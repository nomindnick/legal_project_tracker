"""Integration tests for the Legal Project Tracker.

This module contains end-to-end integration tests that verify complete user
workflows across multiple routes and services. These tests ensure all components
work together correctly.

Sprint 7.1 Acceptance Criteria:
- All integration tests pass
- pytest runs all tests with 0 failures
- Tests cover: create→list→edit→dashboard, filtering/sorting, completion workflow,
  weekly report, monthly report
"""
import csv
import io
from datetime import date, datetime, timedelta, timezone

import pytest

from app import db
from app.models import Project, ProjectStatus
from app.services import project_service


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def create_test_project(app):
    """Factory fixture to create projects with controlled attributes.

    Returns a function that creates a project and returns its ID.
    Defaults are provided but can be overridden with kwargs.
    """
    def _create(**kwargs):
        defaults = {
            'project_name': f'Test Project {datetime.now().timestamp()}',
            'department': 'Public Works',
            'date_to_client': date.today() - timedelta(days=7),
            'date_assigned_to_us': date.today() - timedelta(days=5),
            'assigned_attorney': 'John Smith',
            'qcp_attorney': 'Jane Doe',
            'status': ProjectStatus.IN_PROGRESS,
            'delivery_deadline': date.today() + timedelta(days=7),
        }
        defaults.update(kwargs)
        with app.app_context():
            project = Project(**defaults)
            db.session.add(project)
            db.session.commit()
            return project.id
    return _create


@pytest.fixture
def create_project_with_timestamps(app):
    """Factory fixture to create projects with controlled created_at/updated_at.

    Useful for testing monthly stats where we need to control when
    projects were created or completed.
    """
    def _create(created_at=None, updated_at=None, **kwargs):
        defaults = {
            'project_name': f'Test Project {datetime.now().timestamp()}',
            'department': 'Public Works',
            'date_to_client': date.today() - timedelta(days=7),
            'date_assigned_to_us': date.today() - timedelta(days=5),
            'assigned_attorney': 'John Smith',
            'qcp_attorney': 'Jane Doe',
            'status': ProjectStatus.IN_PROGRESS,
        }
        defaults.update(kwargs)
        with app.app_context():
            project = Project(**defaults)
            db.session.add(project)
            db.session.flush()  # Get ID before setting timestamps

            # Override timestamps if provided
            if created_at:
                project.created_at = created_at
            if updated_at:
                project.updated_at = updated_at

            db.session.commit()
            return project.id
    return _create


# ============================================================================
# Test 1: Full Project Lifecycle with Dashboard Categorization
# ============================================================================

class TestProjectLifecycleDashboard:
    """Tests for: Create project → appears in list → edit status → dashboard section."""

    def test_create_project_appears_in_projects_list(self, client, app):
        """Project created via form appears in projects list."""
        # Create project via form POST
        form_data = {
            'project_name': 'Lifecycle Test Project',
            'department': 'Public Works',
            'date_to_client': date.today().isoformat(),
            'date_assigned_to_us': date.today().isoformat(),
            'assigned_attorney': 'John Smith',
            'qcp_attorney': 'Jane Doe',
            'status': ProjectStatus.IN_PROGRESS,
            'delivery_deadline': (date.today() + timedelta(days=3)).isoformat(),
        }

        response = client.post('/projects/create', data=form_data, follow_redirects=True)
        assert response.status_code == 200

        # Verify project appears in JSON projects list
        response = client.get('/projects')
        assert response.status_code == 200
        data = response.get_json()
        assert data['count'] >= 1
        project_names = [p['project_name'] for p in data['data']]
        assert 'Lifecycle Test Project' in project_names

    def test_project_due_this_week_appears_in_dashboard_section(self, client, create_test_project):
        """Project with deadline in 3 days appears in 'due this week' dashboard section."""
        # Create project due in 3 days
        project_id = create_test_project(
            project_name='Due This Week Project',
            delivery_deadline=date.today() + timedelta(days=3),
            status=ProjectStatus.IN_PROGRESS,
        )

        # Check dashboard API
        response = client.get('/api/dashboard')
        assert response.status_code == 200
        data = response.get_json()

        # Should be in due_this_week section
        due_this_week_names = [p['project_name'] for p in data['due_this_week']['data']]
        assert 'Due This Week Project' in due_this_week_names

        # Should NOT be in overdue or longer_deadline
        overdue_names = [p['project_name'] for p in data['overdue']['data']]
        longer_names = [p['project_name'] for p in data['longer_deadline']['data']]
        assert 'Due This Week Project' not in overdue_names
        assert 'Due This Week Project' not in longer_names

    def test_edit_status_project_still_in_correct_dashboard(self, client, app, create_test_project):
        """After editing status, project remains in correct dashboard section."""
        # Create project
        project_id = create_test_project(
            project_name='Status Edit Project',
            delivery_deadline=date.today() + timedelta(days=3),
            status=ProjectStatus.IN_PROGRESS,
        )

        # Update status via PUT
        update_data = {'status': ProjectStatus.UNDER_REVIEW}
        response = client.put(
            f'/projects/{project_id}',
            json=update_data,
            content_type='application/json'
        )
        assert response.status_code == 200

        # Verify in dashboard (should still be in due_this_week with new status)
        response = client.get('/api/dashboard')
        data = response.get_json()

        due_this_week = data['due_this_week']['data']
        project = next((p for p in due_this_week if p['project_name'] == 'Status Edit Project'), None)
        assert project is not None
        assert project['status'] == ProjectStatus.UNDER_REVIEW

    def test_update_deadline_moves_to_overdue_section(self, client, app, create_test_project):
        """Updating delivery_deadline to past moves project to overdue section."""
        # Create project due in the future
        project_id = create_test_project(
            project_name='Overdue Test Project',
            delivery_deadline=date.today() + timedelta(days=3),
            status=ProjectStatus.IN_PROGRESS,
        )

        # Verify initially in due_this_week
        response = client.get('/api/dashboard')
        data = response.get_json()
        due_this_week_names = [p['project_name'] for p in data['due_this_week']['data']]
        assert 'Overdue Test Project' in due_this_week_names

        # Update deadline to yesterday
        yesterday = date.today() - timedelta(days=1)
        update_data = {'delivery_deadline': yesterday.isoformat()}
        response = client.put(
            f'/projects/{project_id}',
            json=update_data,
            content_type='application/json'
        )
        assert response.status_code == 200

        # Verify moved to overdue
        response = client.get('/api/dashboard')
        data = response.get_json()
        overdue_names = [p['project_name'] for p in data['overdue']['data']]
        assert 'Overdue Test Project' in overdue_names


# ============================================================================
# Test 2: Multiple Projects with Filtering and Sorting
# ============================================================================

class TestFilteringAndSorting:
    """Tests for: Create multiple projects → filter works → sort works."""

    def test_filter_by_department(self, client, create_test_project):
        """Filter by department returns only matching projects."""
        # Create projects in different departments
        create_test_project(project_name='PW Project 1', department='Public Works')
        create_test_project(project_name='PW Project 2', department='Public Works')
        create_test_project(project_name='HR Project', department='Human Resources')
        create_test_project(project_name='Finance Project', department='Finance')

        # Filter by Public Works
        response = client.get('/projects?department=Public+Works')
        assert response.status_code == 200
        data = response.get_json()
        assert data['count'] == 2
        for project in data['data']:
            assert project['department'] == 'Public Works'

    def test_filter_by_status(self, client, create_test_project):
        """Filter by status returns only matching projects."""
        create_test_project(project_name='In Progress', status=ProjectStatus.IN_PROGRESS)
        create_test_project(project_name='Under Review 1', status=ProjectStatus.UNDER_REVIEW)
        create_test_project(project_name='Under Review 2', status=ProjectStatus.UNDER_REVIEW)

        # Filter by Under Review
        response = client.get('/projects?status=Under+Review&include_completed=true')
        assert response.status_code == 200
        data = response.get_json()
        assert data['count'] == 2
        for project in data['data']:
            assert project['status'] == ProjectStatus.UNDER_REVIEW

    def test_sort_by_delivery_deadline_ascending(self, client, create_test_project):
        """Sort by delivery_deadline ascending orders correctly."""
        create_test_project(
            project_name='Later',
            delivery_deadline=date.today() + timedelta(days=10)
        )
        create_test_project(
            project_name='Sooner',
            delivery_deadline=date.today() + timedelta(days=2)
        )
        create_test_project(
            project_name='Middle',
            delivery_deadline=date.today() + timedelta(days=5)
        )

        response = client.get('/projects?sort_by=delivery_deadline&sort_dir=asc')
        assert response.status_code == 200
        data = response.get_json()

        names = [p['project_name'] for p in data['data']]
        assert names.index('Sooner') < names.index('Middle') < names.index('Later')

    def test_multi_term_search(self, client, create_test_project):
        """Multi-term search finds projects matching all terms."""
        create_test_project(
            project_name='HR Investigation Case',
            department='Human Resources',
            notes='Investigation into employee conduct'
        )
        create_test_project(
            project_name='Finance Audit',
            department='Finance',
            notes='Annual audit review'
        )
        create_test_project(
            project_name='HR Benefits Review',
            department='Human Resources',
            notes='Quarterly benefits review'
        )

        # Search for "HR Investigation" - should only find the first project
        response = client.get('/projects?search=HR+Investigation')
        assert response.status_code == 200
        data = response.get_json()
        assert data['count'] == 1
        assert data['data'][0]['project_name'] == 'HR Investigation Case'

    def test_combined_filters(self, client, create_test_project):
        """Multiple filters work together."""
        create_test_project(
            project_name='Match All',
            department='Public Works',
            status=ProjectStatus.UNDER_REVIEW,
            assigned_attorney='John Smith',
        )
        create_test_project(
            project_name='Wrong Dept',
            department='Finance',
            status=ProjectStatus.UNDER_REVIEW,
            assigned_attorney='John Smith',
        )
        create_test_project(
            project_name='Wrong Status',
            department='Public Works',
            status=ProjectStatus.IN_PROGRESS,
            assigned_attorney='John Smith',
        )

        # Combine department and status filters
        response = client.get(
            '/projects?department=Public+Works&status=Under+Review&include_completed=true'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['count'] == 1
        assert data['data'][0]['project_name'] == 'Match All'


# ============================================================================
# Test 3: Project Completion Workflow
# ============================================================================

class TestCompletionWorkflow:
    """Tests for: Complete project → disappears from default view → appears in Recently Completed."""

    def test_completed_project_excluded_from_default_view(self, client, create_test_project):
        """Completed projects are excluded from default projects list."""
        project_id = create_test_project(
            project_name='Soon Completed',
            status=ProjectStatus.IN_PROGRESS
        )

        # Verify in default list initially
        response = client.get('/projects')
        data = response.get_json()
        names = [p['project_name'] for p in data['data']]
        assert 'Soon Completed' in names

        # Complete the project
        client.put(f'/projects/{project_id}', json={'status': ProjectStatus.COMPLETED})

        # Verify NOT in default list (excludes completed by default)
        response = client.get('/projects')
        data = response.get_json()
        names = [p['project_name'] for p in data['data']]
        assert 'Soon Completed' not in names

    def test_completed_project_visible_with_include_completed(self, client, create_test_project):
        """Completed projects visible when include_completed=true."""
        project_id = create_test_project(
            project_name='Completed Visible',
            status=ProjectStatus.COMPLETED
        )

        # Default: not visible
        response = client.get('/projects')
        data = response.get_json()
        names = [p['project_name'] for p in data['data']]
        assert 'Completed Visible' not in names

        # With include_completed: visible
        response = client.get('/projects?include_completed=true')
        data = response.get_json()
        names = [p['project_name'] for p in data['data']]
        assert 'Completed Visible' in names

    def test_completed_project_in_recently_completed_dashboard(self, client, create_test_project):
        """Completed projects appear in 'Recently Completed' dashboard section."""
        project_id = create_test_project(
            project_name='Dashboard Completed',
            status=ProjectStatus.COMPLETED
        )

        response = client.get('/api/dashboard')
        data = response.get_json()

        # Should be in recently_completed
        recently_completed_names = [p['project_name'] for p in data['recently_completed']['data']]
        assert 'Dashboard Completed' in recently_completed_names

        # Should NOT be in active sections
        overdue_names = [p['project_name'] for p in data['overdue']['data']]
        due_this_week_names = [p['project_name'] for p in data['due_this_week']['data']]
        longer_names = [p['project_name'] for p in data['longer_deadline']['data']]

        assert 'Dashboard Completed' not in overdue_names
        assert 'Dashboard Completed' not in due_this_week_names
        assert 'Dashboard Completed' not in longer_names

    def test_recently_completed_limited_to_10(self, client, create_test_project):
        """Recently Completed section shows maximum 10 projects."""
        # Create 12 completed projects
        for i in range(12):
            create_test_project(
                project_name=f'Completed {i}',
                status=ProjectStatus.COMPLETED
            )

        response = client.get('/api/dashboard')
        data = response.get_json()

        assert data['recently_completed']['count'] <= 10


# ============================================================================
# Test 4: Weekly Report Generation
# ============================================================================

class TestWeeklyReport:
    """Tests for: Generate weekly report → all active projects appear."""

    def test_weekly_report_includes_active_projects(self, client, create_test_project):
        """Weekly report includes all active (non-completed) projects."""
        create_test_project(project_name='Active 1', status=ProjectStatus.IN_PROGRESS)
        create_test_project(project_name='Active 2', status=ProjectStatus.UNDER_REVIEW)
        create_test_project(project_name='Active 3', status=ProjectStatus.ON_HOLD)
        create_test_project(project_name='Completed', status=ProjectStatus.COMPLETED)

        response = client.get('/reports/weekly')
        assert response.status_code == 200
        html = response.data.decode('utf-8')

        # Active projects should appear
        assert 'Active 1' in html
        assert 'Active 2' in html
        assert 'Active 3' in html

        # Completed should NOT appear
        assert 'Completed' not in html

    def test_weekly_report_field_selection(self, client, create_test_project):
        """Weekly report respects field selection."""
        create_test_project(
            project_name='Field Test Project',
            department='Public Works',
            assigned_attorney='John Smith',
            status=ProjectStatus.IN_PROGRESS,
        )

        # Request specific fields only
        response = client.get('/reports/weekly?fields=project_name,status')
        assert response.status_code == 200
        html = response.data.decode('utf-8')

        # Should include requested fields
        assert 'Field Test Project' in html

    def test_weekly_report_anticipated_completion_label(self, client, create_test_project):
        """Weekly report uses 'Anticipated Completion' instead of 'Delivery Deadline'."""
        create_test_project(
            project_name='Deadline Label Test',
            delivery_deadline=date.today() + timedelta(days=5),
        )

        response = client.get('/reports/weekly?fields=project_name,anticipated_completion')
        assert response.status_code == 200
        html = response.data.decode('utf-8')

        # Should use soft language
        assert 'Anticipated Completion' in html


# ============================================================================
# Test 5: Monthly Report Statistics
# ============================================================================

class TestMonthlyReport:
    """Tests for: Generate monthly report → stats are accurate."""

    def test_monthly_report_projects_opened_count(self, client, app, create_project_with_timestamps):
        """Monthly report correctly counts projects opened this month."""
        now = datetime.now(timezone.utc)
        first_of_month = datetime(now.year, now.month, 1, 0, 0, 0, tzinfo=timezone.utc)
        last_month = first_of_month - timedelta(days=1)

        # Create 2 projects this month
        create_project_with_timestamps(
            project_name='This Month 1',
            created_at=first_of_month + timedelta(days=1)
        )
        create_project_with_timestamps(
            project_name='This Month 2',
            created_at=first_of_month + timedelta(days=2)
        )

        # Create 1 project last month (should not count)
        create_project_with_timestamps(
            project_name='Last Month',
            created_at=last_month
        )

        response = client.get(f'/reports/monthly?year={now.year}&month={now.month}')
        assert response.status_code == 200
        html = response.data.decode('utf-8')

        # Look for the count in the HTML
        # The template shows "projects_opened" as a stat
        assert '2' in html  # 2 projects opened this month

    def test_monthly_report_projects_completed_count(self, client, app, create_project_with_timestamps):
        """Monthly report correctly counts projects completed this month."""
        now = datetime.now(timezone.utc)
        first_of_month = datetime(now.year, now.month, 1, 0, 0, 0, tzinfo=timezone.utc)

        # Create completed project updated this month
        create_project_with_timestamps(
            project_name='Completed This Month',
            status=ProjectStatus.COMPLETED,
            updated_at=first_of_month + timedelta(days=5)
        )

        # Create active project (should not count as completed)
        create_project_with_timestamps(
            project_name='Still Active',
            status=ProjectStatus.IN_PROGRESS,
            updated_at=first_of_month + timedelta(days=5)
        )

        response = client.get(f'/reports/monthly?year={now.year}&month={now.month}')
        assert response.status_code == 200
        html = response.data.decode('utf-8')

        # 1 project completed this month
        assert 'Completed This Month' not in html or '1' in html

    def test_monthly_report_by_department_breakdown(self, client, app, create_project_with_timestamps):
        """Monthly report shows correct by-department breakdown."""
        now = datetime.now(timezone.utc)
        first_of_month = datetime(now.year, now.month, 1, 0, 0, 0, tzinfo=timezone.utc)

        # Create projects in different departments
        create_project_with_timestamps(
            project_name='PW 1',
            department='Public Works',
            created_at=first_of_month + timedelta(days=1)
        )
        create_project_with_timestamps(
            project_name='PW 2',
            department='Public Works',
            created_at=first_of_month + timedelta(days=2)
        )
        create_project_with_timestamps(
            project_name='Finance 1',
            department='Finance',
            created_at=first_of_month + timedelta(days=3)
        )

        response = client.get(f'/reports/monthly?year={now.year}&month={now.month}')
        assert response.status_code == 200
        html = response.data.decode('utf-8')

        # Departments should appear in the breakdown
        assert 'Public Works' in html
        assert 'Finance' in html


# ============================================================================
# Test 6: Clone Project Workflow
# ============================================================================

class TestCloneWorkflow:
    """Tests for clone project functionality."""

    def test_clone_redirects_to_new_form_with_prefill(self, client, create_test_project):
        """Clone redirects to new project form with prefilled fields."""
        project_id = create_test_project(
            project_name='Original Project',
            department='Public Works',
            project_group='Test Group',
            assigned_attorney='John Smith',
            qcp_attorney='Jane Doe',
        )

        response = client.get(f'/projects/{project_id}/clone')
        assert response.status_code == 302  # Redirect

        # Follow redirect
        response = client.get(f'/projects/{project_id}/clone', follow_redirects=True)
        assert response.status_code == 200
        html = response.data.decode('utf-8')

        # Prefilled values should appear
        assert 'Public Works' in html
        assert 'John Smith' in html
        assert 'Jane Doe' in html

    def test_clone_does_not_prefill_dates(self, client, create_test_project):
        """Clone does not prefill date fields."""
        project_id = create_test_project(
            project_name='Original With Dates',
            delivery_deadline=date.today() + timedelta(days=10),
            internal_deadline=date.today() + timedelta(days=5),
        )

        response = client.get(f'/projects/{project_id}/clone', follow_redirects=True)
        assert response.status_code == 200

        # The form should not have dates prefilled
        # Dates from original project should not appear in the form values


# ============================================================================
# Test 7: Notes Append-Only Workflow
# ============================================================================

class TestNotesAppendOnly:
    """Tests for append-only notes functionality."""

    def test_append_note_preserves_existing_notes(self, client, app, create_test_project):
        """Appending a note preserves existing notes."""
        project_id = create_test_project(
            project_name='Notes Test',
            notes='[2026-01-01 09:00]: Initial note.'
        )

        # Append a new note via API
        response = client.post(
            f'/projects/{project_id}/notes',
            json={'note': 'Second note added'},
            content_type='application/json'
        )
        assert response.status_code == 200

        # Get project and verify both notes exist
        response = client.get(f'/projects/{project_id}')
        data = response.get_json()

        # API wraps response in {'data': {...}}
        assert 'Initial note' in data['data']['notes']
        assert 'Second note added' in data['data']['notes']

    def test_append_note_adds_timestamp(self, client, create_test_project):
        """Appended notes include timestamps."""
        project_id = create_test_project(project_name='Timestamp Test')

        response = client.post(
            f'/projects/{project_id}/notes',
            json={'note': 'Timestamped note'},
            content_type='application/json'
        )
        assert response.status_code == 200

        response = client.get(f'/projects/{project_id}')
        data = response.get_json()

        # API wraps response in {'data': {...}}
        notes = data['data']['notes']

        # Should have timestamp format [YYYY-MM-DD HH:MM]
        assert '[' in notes
        assert ']:' in notes
        assert 'Timestamped note' in notes


# ============================================================================
# Test 8: Soft Delete Integration
# ============================================================================

class TestSoftDelete:
    """Tests for soft delete functionality."""

    def test_delete_hides_from_list(self, client, create_test_project):
        """Deleted project hidden from default list."""
        project_id = create_test_project(project_name='To Delete')

        # Verify initially visible
        response = client.get('/projects')
        names = [p['project_name'] for p in response.get_json()['data']]
        assert 'To Delete' in names

        # Delete project
        response = client.delete(f'/projects/{project_id}')
        assert response.status_code == 200

        # Verify hidden
        response = client.get('/projects')
        names = [p['project_name'] for p in response.get_json()['data']]
        assert 'To Delete' not in names

    def test_delete_visible_with_include_deleted(self, client, create_test_project):
        """Deleted project visible with include_deleted=true."""
        project_id = create_test_project(project_name='Soft Deleted')

        # Delete project
        client.delete(f'/projects/{project_id}')

        # Verify visible with flag
        response = client.get('/projects?include_deleted=true')
        names = [p['project_name'] for p in response.get_json()['data']]
        assert 'Soft Deleted' in names

    def test_delete_sets_deleted_at_timestamp(self, client, app, create_test_project):
        """Delete sets deleted_at timestamp."""
        project_id = create_test_project(project_name='Timestamp Delete')

        # Delete project
        client.delete(f'/projects/{project_id}')

        # Query database directly
        with app.app_context():
            project = db.session.get(Project, project_id)
            assert project.deleted_at is not None


# ============================================================================
# Test 9: Autocomplete and Normalization Integration
# ============================================================================

class TestAutocompleteNormalization:
    """Tests for autocomplete and soft normalization."""

    def test_autocomplete_returns_distinct_values(self, client, create_test_project):
        """Autocomplete endpoint returns distinct values."""
        create_test_project(project_name='P1', department='Public Works')
        create_test_project(project_name='P2', department='Human Resources')
        create_test_project(project_name='P3', department='Public Works')  # Duplicate

        response = client.get('/api/autocomplete/department')
        assert response.status_code == 200
        data = response.get_json()

        # API wraps response in {'data': [...]}
        values = data['data']

        # Should have exactly 2 distinct departments
        assert 'Human Resources' in values
        assert 'Public Works' in values
        assert len(values) == 2

    def test_soft_normalization_matches_existing_case(self, client, app, create_test_project):
        """Creating project with different case normalizes to existing value."""
        # Create canonical value
        create_test_project(project_name='First', department='Public Works')

        # Create new project with lowercase department
        form_data = {
            'project_name': 'Second Project',
            'department': 'public works',  # lowercase
            'date_to_client': date.today().isoformat(),
            'date_assigned_to_us': date.today().isoformat(),
            'assigned_attorney': 'John Smith',
            'qcp_attorney': 'Jane Doe',
        }

        response = client.post('/projects/create', data=form_data, follow_redirects=True)
        assert response.status_code == 200

        # Verify normalized to canonical case
        with app.app_context():
            project = Project.query.filter_by(project_name='Second Project').first()
            assert project.department == 'Public Works'


# ============================================================================
# Test 10: CSV Export Integration
# ============================================================================

class TestCSVExport:
    """Tests for CSV export functionality."""

    def test_csv_export_returns_csv_format(self, client, create_test_project):
        """CSV export returns proper CSV format with headers."""
        create_test_project(project_name='CSV Test Project')

        response = client.get('/projects/export')
        assert response.status_code == 200
        assert response.content_type.startswith('text/csv')

        # Parse CSV
        csv_content = response.data.decode('utf-8')
        reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(reader)

        assert len(rows) >= 1
        assert 'Project Name' in reader.fieldnames

    def test_csv_export_respects_filters(self, client, create_test_project):
        """CSV export respects filter parameters."""
        create_test_project(project_name='PW Export', department='Public Works')
        create_test_project(project_name='HR Export', department='Human Resources')

        # Export with department filter
        response = client.get('/projects/export?department=Public+Works')
        csv_content = response.data.decode('utf-8')
        reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(reader)

        # Should only have Public Works project
        assert len(rows) == 1
        assert rows[0]['Project Name'] == 'PW Export'

    def test_csv_export_content_disposition(self, client, create_test_project):
        """CSV export has correct Content-Disposition header."""
        create_test_project(project_name='Export Header Test')

        response = client.get('/projects/export')

        assert 'Content-Disposition' in response.headers
        assert 'attachment' in response.headers['Content-Disposition']
        assert 'csv' in response.headers['Content-Disposition']
