"""Tests for project routes.

This module tests all HTTP endpoints in the projects blueprint.
Uses Flask test client to make requests and verify responses.
"""
import json
from datetime import date, timedelta

import pytest

from app import db
from app.models import Project, ProjectStatus


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_project_json():
    """Sample project data as JSON-serializable dict with date strings."""
    return {
        'project_name': 'Test Project',
        'project_group': 'Test Group',
        'department': 'Public Works',
        'date_to_client': '2026-01-01',
        'date_assigned_to_us': '2026-01-05',
        'assigned_attorney': 'John Smith',
        'qcp_attorney': 'Jane Doe',
        'internal_deadline': '2026-01-20',
        'delivery_deadline': '2026-01-25',
        'status': 'In Progress',
        'notes': 'Initial assignment received.',
    }


@pytest.fixture
def create_project(app):
    """Factory fixture to create projects in the database."""
    def _create_project(**kwargs):
        defaults = {
            'project_name': 'Test Project',
            'department': 'Public Works',
            'date_to_client': date(2026, 1, 1),
            'date_assigned_to_us': date(2026, 1, 5),
            'assigned_attorney': 'John Smith',
            'qcp_attorney': 'Jane Doe',
            'status': ProjectStatus.IN_PROGRESS,
        }
        defaults.update(kwargs)
        with app.app_context():
            project = Project(**defaults)
            db.session.add(project)
            db.session.commit()
            return project.id
    return _create_project


# ============================================================================
# GET /projects Tests
# ============================================================================

class TestGetProjects:
    """Tests for GET /projects endpoint."""

    def test_get_projects_empty(self, client):
        """Returns empty list when no projects exist."""
        response = client.get('/projects')
        assert response.status_code == 200
        data = response.get_json()
        assert data['data'] == []
        assert data['count'] == 0

    def test_get_projects_with_data(self, client, create_project):
        """Returns all non-deleted projects."""
        create_project(project_name='Project 1')
        create_project(project_name='Project 2')

        response = client.get('/projects')
        assert response.status_code == 200
        data = response.get_json()
        assert data['count'] == 2
        names = [p['project_name'] for p in data['data']]
        assert 'Project 1' in names
        assert 'Project 2' in names

    def test_get_projects_filter_by_status(self, client, create_project):
        """Filters projects by status."""
        create_project(project_name='In Progress', status=ProjectStatus.IN_PROGRESS)
        create_project(project_name='Under Review', status=ProjectStatus.UNDER_REVIEW)

        response = client.get('/projects?status=Under+Review&include_completed=true')
        assert response.status_code == 200
        data = response.get_json()
        assert data['count'] == 1
        assert data['data'][0]['project_name'] == 'Under Review'

    def test_get_projects_filter_multiple_status(self, client, create_project):
        """Filters by comma-separated statuses."""
        create_project(project_name='In Progress', status=ProjectStatus.IN_PROGRESS)
        create_project(project_name='Under Review', status=ProjectStatus.UNDER_REVIEW)
        create_project(project_name='On Hold', status=ProjectStatus.ON_HOLD)

        response = client.get('/projects?status=In+Progress,Under+Review&include_completed=true')
        assert response.status_code == 200
        data = response.get_json()
        assert data['count'] == 2
        names = [p['project_name'] for p in data['data']]
        assert 'In Progress' in names
        assert 'Under Review' in names
        assert 'On Hold' not in names

    def test_get_projects_exclude_completed_by_default(self, client, create_project):
        """Excludes completed projects by default."""
        create_project(project_name='Active', status=ProjectStatus.IN_PROGRESS)
        create_project(project_name='Completed', status=ProjectStatus.COMPLETED)

        response = client.get('/projects')
        assert response.status_code == 200
        data = response.get_json()
        assert data['count'] == 1
        assert data['data'][0]['project_name'] == 'Active'

    def test_get_projects_include_completed(self, client, create_project):
        """Includes completed projects when requested."""
        create_project(project_name='Active', status=ProjectStatus.IN_PROGRESS)
        create_project(project_name='Completed', status=ProjectStatus.COMPLETED)

        response = client.get('/projects?include_completed=true')
        assert response.status_code == 200
        data = response.get_json()
        assert data['count'] == 2

    def test_get_projects_sorting_asc(self, client, create_project):
        """Sorts projects ascending."""
        create_project(project_name='Z Project', delivery_deadline=date(2026, 3, 1))
        create_project(project_name='A Project', delivery_deadline=date(2026, 1, 1))

        response = client.get('/projects?sort_by=project_name&sort_dir=asc')
        assert response.status_code == 200
        data = response.get_json()
        assert data['data'][0]['project_name'] == 'A Project'
        assert data['data'][1]['project_name'] == 'Z Project'

    def test_get_projects_sorting_desc(self, client, create_project):
        """Sorts projects descending."""
        create_project(project_name='Z Project', delivery_deadline=date(2026, 3, 1))
        create_project(project_name='A Project', delivery_deadline=date(2026, 1, 1))

        response = client.get('/projects?sort_by=project_name&sort_dir=desc')
        assert response.status_code == 200
        data = response.get_json()
        assert data['data'][0]['project_name'] == 'Z Project'
        assert data['data'][1]['project_name'] == 'A Project'

    def test_get_projects_filter_by_department(self, client, create_project):
        """Filters projects by department (case-insensitive)."""
        create_project(project_name='PW Project', department='Public Works')
        create_project(project_name='HR Project', department='Human Resources')

        response = client.get('/projects?department=public+works')
        assert response.status_code == 200
        data = response.get_json()
        assert data['count'] == 1
        assert data['data'][0]['project_name'] == 'PW Project'

    def test_get_projects_filter_by_attorney(self, client, create_project):
        """Filters projects by assigned attorney."""
        create_project(project_name='Smith Project', assigned_attorney='John Smith')
        create_project(project_name='Doe Project', assigned_attorney='Jane Doe')

        response = client.get('/projects?assigned_attorney=John+Smith')
        assert response.status_code == 200
        data = response.get_json()
        assert data['count'] == 1
        assert data['data'][0]['project_name'] == 'Smith Project'

    def test_get_projects_excludes_deleted(self, client, app, create_project):
        """Excludes soft-deleted projects by default."""
        create_project(project_name='Active')
        deleted_id = create_project(project_name='Deleted')

        # Soft delete the project
        with app.app_context():
            project = db.session.get(Project, deleted_id)
            from datetime import datetime, timezone
            project.deleted_at = datetime.now(timezone.utc)
            db.session.commit()

        response = client.get('/projects')
        assert response.status_code == 200
        data = response.get_json()
        assert data['count'] == 1
        assert data['data'][0]['project_name'] == 'Active'

    def test_get_projects_date_range_filter(self, client, create_project):
        """Filters by delivery deadline date range."""
        create_project(project_name='Early', delivery_deadline=date(2026, 1, 10))
        create_project(project_name='Middle', delivery_deadline=date(2026, 1, 20))
        create_project(project_name='Late', delivery_deadline=date(2026, 1, 30))

        response = client.get(
            '/projects?delivery_deadline_from=2026-01-15&delivery_deadline_to=2026-01-25'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['count'] == 1
        assert data['data'][0]['project_name'] == 'Middle'


# ============================================================================
# GET /projects/<id> Tests
# ============================================================================

class TestGetProject:
    """Tests for GET /projects/<id> endpoint."""

    def test_get_project_by_id(self, client, create_project):
        """Returns project when found."""
        project_id = create_project(project_name='Test Project')

        response = client.get(f'/projects/{project_id}')
        assert response.status_code == 200
        data = response.get_json()
        assert data['data']['id'] == project_id
        assert data['data']['project_name'] == 'Test Project'

    def test_get_project_not_found(self, client):
        """Returns 404 when project not found."""
        response = client.get('/projects/99999')
        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data

    def test_get_project_deleted(self, client, app, create_project):
        """Returns 404 for soft-deleted project."""
        project_id = create_project(project_name='Deleted Project')

        # Soft delete
        with app.app_context():
            project = db.session.get(Project, project_id)
            from datetime import datetime, timezone
            project.deleted_at = datetime.now(timezone.utc)
            db.session.commit()

        response = client.get(f'/projects/{project_id}')
        assert response.status_code == 404


# ============================================================================
# POST /projects Tests
# ============================================================================

class TestCreateProject:
    """Tests for POST /projects endpoint."""

    def test_create_project(self, client, sample_project_json):
        """Creates project with valid data."""
        response = client.post(
            '/projects',
            data=json.dumps(sample_project_json),
            content_type='application/json'
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data['data']['project_name'] == 'Test Project'
        assert data['data']['department'] == 'Public Works'
        assert data['data']['id'] is not None

    def test_create_project_missing_fields(self, client):
        """Returns 400 when required fields missing."""
        response = client.post(
            '/projects',
            data=json.dumps({'project_name': 'Incomplete'}),
            content_type='application/json'
        )
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'Missing required fields' in data['error']

    def test_create_project_invalid_status(self, client, sample_project_json):
        """Returns 400 for invalid status."""
        sample_project_json['status'] = 'Invalid Status'
        response = client.post(
            '/projects',
            data=json.dumps(sample_project_json),
            content_type='application/json'
        )
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'Invalid status' in data['error']

    def test_create_project_default_status(self, client, sample_project_json):
        """Uses default status when not provided."""
        del sample_project_json['status']
        response = client.post(
            '/projects',
            data=json.dumps(sample_project_json),
            content_type='application/json'
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data['data']['status'] == 'In Progress'

    def test_create_project_no_json_body(self, client):
        """Returns error when no JSON body provided."""
        response = client.post('/projects')
        # Flask returns 415 when no content-type is set
        assert response.status_code in (400, 415)


# ============================================================================
# PUT /projects/<id> Tests
# ============================================================================

class TestUpdateProject:
    """Tests for PUT /projects/<id> endpoint."""

    def test_update_project(self, client, create_project):
        """Updates project with valid data."""
        project_id = create_project(project_name='Original Name')

        response = client.put(
            f'/projects/{project_id}',
            data=json.dumps({'project_name': 'Updated Name'}),
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['data']['project_name'] == 'Updated Name'

    def test_update_project_not_found(self, client):
        """Returns 404 when project not found."""
        response = client.put(
            '/projects/99999',
            data=json.dumps({'project_name': 'Updated'}),
            content_type='application/json'
        )
        assert response.status_code == 404

    def test_update_project_invalid_status(self, client, create_project):
        """Returns 400 for invalid status."""
        project_id = create_project()

        response = client.put(
            f'/projects/{project_id}',
            data=json.dumps({'status': 'Invalid Status'}),
            content_type='application/json'
        )
        assert response.status_code == 400
        data = response.get_json()
        assert 'Invalid status' in data['error']

    def test_update_project_status(self, client, create_project):
        """Updates project status."""
        project_id = create_project(status=ProjectStatus.IN_PROGRESS)

        response = client.put(
            f'/projects/{project_id}',
            data=json.dumps({'status': 'Under Review'}),
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['data']['status'] == 'Under Review'

    def test_update_project_no_json_body(self, client, create_project):
        """Returns error when no JSON body provided."""
        project_id = create_project()
        response = client.put(f'/projects/{project_id}')
        # Flask returns 415 when no content-type is set
        assert response.status_code in (400, 415)


# ============================================================================
# DELETE /projects/<id> Tests
# ============================================================================

class TestDeleteProject:
    """Tests for DELETE /projects/<id> endpoint."""

    def test_delete_project(self, client, app, create_project):
        """Soft deletes project."""
        project_id = create_project(project_name='To Delete')

        response = client.delete(f'/projects/{project_id}')
        assert response.status_code == 200
        data = response.get_json()
        assert 'message' in data

        # Verify project is soft-deleted
        with app.app_context():
            project = db.session.get(Project, project_id)
            assert project.deleted_at is not None

    def test_delete_project_not_found(self, client):
        """Returns 404 when project not found."""
        response = client.delete('/projects/99999')
        assert response.status_code == 404

    def test_delete_project_already_deleted(self, client, app, create_project):
        """Returns 404 when project already deleted."""
        project_id = create_project()

        # Soft delete
        with app.app_context():
            project = db.session.get(Project, project_id)
            from datetime import datetime, timezone
            project.deleted_at = datetime.now(timezone.utc)
            db.session.commit()

        response = client.delete(f'/projects/{project_id}')
        assert response.status_code == 404


# ============================================================================
# POST /projects/<id>/notes Tests
# ============================================================================

class TestAppendNote:
    """Tests for POST /projects/<id>/notes endpoint."""

    def test_append_note(self, client, create_project):
        """Appends timestamped note to project."""
        project_id = create_project(notes=None)

        response = client.post(
            f'/projects/{project_id}/notes',
            data=json.dumps({'note': 'This is a test note'}),
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert 'This is a test note' in data['data']['notes']
        # Verify timestamp format
        assert '[' in data['data']['notes']
        assert ']:' in data['data']['notes']

    def test_append_note_to_existing(self, client, create_project):
        """Appends note to project with existing notes."""
        project_id = create_project(notes='[2026-01-01 10:00]: Existing note')

        response = client.post(
            f'/projects/{project_id}/notes',
            data=json.dumps({'note': 'New note'}),
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert 'Existing note' in data['data']['notes']
        assert 'New note' in data['data']['notes']

    def test_append_note_not_found(self, client):
        """Returns 404 when project not found."""
        response = client.post(
            '/projects/99999/notes',
            data=json.dumps({'note': 'Test'}),
            content_type='application/json'
        )
        assert response.status_code == 404

    def test_append_empty_note(self, client, create_project):
        """Empty note does not change project notes."""
        project_id = create_project(notes='[2026-01-01 10:00]: Original note')

        response = client.post(
            f'/projects/{project_id}/notes',
            data=json.dumps({'note': '   '}),
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        # Should only have the original note
        assert data['data']['notes'] == '[2026-01-01 10:00]: Original note'


# ============================================================================
# GET /api/autocomplete/<field> Tests
# ============================================================================

class TestAutocomplete:
    """Tests for GET /api/autocomplete/<field> endpoint."""

    def test_autocomplete_department(self, client, create_project):
        """Returns distinct department values."""
        create_project(department='Public Works')
        create_project(department='Human Resources')
        create_project(department='Public Works')  # Duplicate

        response = client.get('/api/autocomplete/department')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['data']) == 2
        assert 'Public Works' in data['data']
        assert 'Human Resources' in data['data']

    def test_autocomplete_assigned_attorney(self, client, create_project):
        """Returns distinct assigned attorney values."""
        create_project(assigned_attorney='John Smith')
        create_project(assigned_attorney='Jane Doe')

        response = client.get('/api/autocomplete/assigned_attorney')
        assert response.status_code == 200
        data = response.get_json()
        assert 'John Smith' in data['data']
        assert 'Jane Doe' in data['data']

    def test_autocomplete_qcp_attorney(self, client, create_project):
        """Returns distinct QCP attorney values."""
        create_project(qcp_attorney='Senior Partner')

        response = client.get('/api/autocomplete/qcp_attorney')
        assert response.status_code == 200
        data = response.get_json()
        assert 'Senior Partner' in data['data']

    def test_autocomplete_status(self, client, create_project):
        """Returns distinct status values."""
        create_project(status=ProjectStatus.IN_PROGRESS)
        create_project(status=ProjectStatus.UNDER_REVIEW)

        response = client.get('/api/autocomplete/status')
        assert response.status_code == 200
        data = response.get_json()
        assert 'In Progress' in data['data']
        assert 'Under Review' in data['data']

    def test_autocomplete_invalid_field(self, client):
        """Returns 400 for invalid field."""
        response = client.get('/api/autocomplete/invalid_field')
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_autocomplete_empty_database(self, client):
        """Returns empty list when no data."""
        response = client.get('/api/autocomplete/department')
        assert response.status_code == 200
        data = response.get_json()
        assert data['data'] == []

    def test_autocomplete_excludes_deleted(self, client, app, create_project):
        """Excludes values from deleted projects."""
        create_project(department='Active Dept')
        deleted_id = create_project(department='Deleted Dept')

        # Soft delete
        with app.app_context():
            project = db.session.get(Project, deleted_id)
            from datetime import datetime, timezone
            project.deleted_at = datetime.now(timezone.utc)
            db.session.commit()

        response = client.get('/api/autocomplete/department')
        assert response.status_code == 200
        data = response.get_json()
        assert 'Active Dept' in data['data']
        assert 'Deleted Dept' not in data['data']


# ============================================================================
# Dashboard Route Tests
# ============================================================================

class TestDashboardRoute:
    """Tests for dashboard route."""

    # HTML Response Tests

    def test_dashboard_returns_200(self, client):
        """Dashboard route returns 200 status."""
        response = client.get('/dashboard')
        assert response.status_code == 200

    def test_dashboard_root_route(self, client):
        """Root route (/) also returns dashboard."""
        response = client.get('/')
        assert response.status_code == 200

    def test_dashboard_returns_html(self, client):
        """Dashboard returns HTML content type."""
        response = client.get('/dashboard')
        assert response.status_code == 200
        assert response.content_type.startswith('text/html')

    def test_dashboard_contains_all_sections(self, client):
        """Dashboard HTML contains all four sections."""
        response = client.get('/dashboard')
        html = response.data.decode('utf-8')

        assert 'Overdue' in html
        assert 'Due This Week' in html
        assert 'Longer Deadline' in html
        assert 'Recently Completed' in html

    def test_dashboard_displays_project(self, client, create_project):
        """Dashboard HTML displays project information."""
        yesterday = date.today() - timedelta(days=1)
        create_project(
            project_name='Test Overdue Project',
            department='Test Department',
            delivery_deadline=yesterday,
            status=ProjectStatus.IN_PROGRESS
        )

        response = client.get('/dashboard')
        html = response.data.decode('utf-8')

        assert 'Test Overdue Project' in html
        assert 'Test Department' in html

    def test_dashboard_empty_state(self, client):
        """Dashboard shows empty state messages when no projects."""
        response = client.get('/dashboard')
        html = response.data.decode('utf-8')

        # Check for empty state messaging
        assert 'No overdue projects' in html or 'Great job!' in html

    # API JSON Response Tests

    def test_dashboard_api_returns_json(self, client):
        """API endpoint returns JSON content type."""
        response = client.get('/api/dashboard')
        assert response.status_code == 200
        assert response.content_type == 'application/json'

    def test_dashboard_api_returns_all_sections(self, client):
        """API endpoint returns all four project sections."""
        response = client.get('/api/dashboard')
        assert response.status_code == 200
        data = response.get_json()

        # Verify all sections exist
        assert 'overdue' in data
        assert 'due_this_week' in data
        assert 'longer_deadline' in data
        assert 'recently_completed' in data

        # Verify structure of each section
        for section in ['overdue', 'due_this_week', 'longer_deadline', 'recently_completed']:
            assert 'data' in data[section]
            assert 'count' in data[section]
            assert isinstance(data[section]['data'], list)
            assert isinstance(data[section]['count'], int)

    def test_dashboard_api_categorizes_overdue(self, client, create_project):
        """API correctly identifies overdue projects."""
        yesterday = date.today() - timedelta(days=1)
        create_project(
            project_name='Overdue Project',
            delivery_deadline=yesterday,
            status=ProjectStatus.IN_PROGRESS
        )

        response = client.get('/api/dashboard')
        data = response.get_json()

        assert data['overdue']['count'] == 1
        assert data['overdue']['data'][0]['project_name'] == 'Overdue Project'
        assert data['due_this_week']['count'] == 0

    def test_dashboard_api_categorizes_due_this_week(self, client, create_project):
        """API correctly identifies projects due this week."""
        in_three_days = date.today() + timedelta(days=3)
        create_project(
            project_name='Due Soon',
            delivery_deadline=in_three_days,
            status=ProjectStatus.IN_PROGRESS
        )

        response = client.get('/api/dashboard')
        data = response.get_json()

        assert data['due_this_week']['count'] == 1
        assert data['due_this_week']['data'][0]['project_name'] == 'Due Soon'
        assert data['overdue']['count'] == 0

    def test_dashboard_api_categorizes_longer_deadline(self, client, create_project):
        """API correctly identifies projects with longer deadlines."""
        in_ten_days = date.today() + timedelta(days=10)
        create_project(
            project_name='Future Project',
            delivery_deadline=in_ten_days,
            status=ProjectStatus.IN_PROGRESS
        )

        response = client.get('/api/dashboard')
        data = response.get_json()

        assert data['longer_deadline']['count'] == 1
        assert data['longer_deadline']['data'][0]['project_name'] == 'Future Project'

    def test_dashboard_api_categorizes_completed(self, client, create_project):
        """API correctly identifies completed projects."""
        create_project(
            project_name='Done Project',
            delivery_deadline=date.today(),
            status=ProjectStatus.COMPLETED
        )

        response = client.get('/api/dashboard')
        data = response.get_json()

        assert data['recently_completed']['count'] == 1
        assert data['recently_completed']['data'][0]['project_name'] == 'Done Project'
        # Completed should not appear in other sections
        assert data['overdue']['count'] == 0
        assert data['due_this_week']['count'] == 0
        assert data['longer_deadline']['count'] == 0

    def test_dashboard_api_with_mixed_projects(self, client, create_project):
        """API correctly categorizes multiple projects."""
        yesterday = date.today() - timedelta(days=1)
        in_three_days = date.today() + timedelta(days=3)
        in_ten_days = date.today() + timedelta(days=10)

        create_project(project_name='Overdue', delivery_deadline=yesterday)
        create_project(project_name='Due Soon 1', delivery_deadline=in_three_days)
        create_project(project_name='Due Soon 2', delivery_deadline=in_three_days)
        create_project(project_name='Future', delivery_deadline=in_ten_days)
        create_project(project_name='Done', delivery_deadline=in_three_days,
                      status=ProjectStatus.COMPLETED)

        response = client.get('/api/dashboard')
        data = response.get_json()

        assert data['overdue']['count'] == 1
        assert data['due_this_week']['count'] == 2
        assert data['longer_deadline']['count'] == 1
        assert data['recently_completed']['count'] == 1


# ============================================================================
# GET /projects Search Tests
# ============================================================================

class TestProjectSearch:
    """Tests for search functionality in GET /projects."""

    def test_search_single_term(self, client, create_project):
        """Search with single term finds matching projects."""
        create_project(project_name='Municipal Code Review')
        create_project(project_name='Budget Analysis')

        response = client.get('/projects?search=Municipal')
        assert response.status_code == 200
        data = response.get_json()
        assert data['count'] == 1
        assert data['data'][0]['project_name'] == 'Municipal Code Review'

    def test_search_multi_term(self, client, create_project):
        """Search with multiple terms uses AND logic."""
        # Note: search only covers project_name, department, notes, project_group
        create_project(
            project_name='HR Policy Review',
            department='Public Works',
            notes='Smith consulted on this'
        )
        create_project(
            project_name='Budget Analysis',
            notes='Smith involved'
        )
        create_project(
            project_name='HR Compliance',
            department='Finance'
        )

        # "hr" in project_name, "smith" in notes
        response = client.get('/projects?search=smith+hr')
        assert response.status_code == 200
        data = response.get_json()
        assert data['count'] == 1
        assert data['data'][0]['project_name'] == 'HR Policy Review'

    def test_search_case_insensitive(self, client, create_project):
        """Search is case-insensitive."""
        create_project(project_name='Public Works Review')

        # Test uppercase
        response = client.get('/projects?search=PUBLIC')
        assert response.status_code == 200
        data = response.get_json()
        assert data['count'] == 1

        # Test lowercase
        response = client.get('/projects?search=public')
        assert response.status_code == 200
        data = response.get_json()
        assert data['count'] == 1

    def test_search_by_department(self, client, create_project):
        """Search finds projects matching department."""
        create_project(department='Finance')
        create_project(department='Public Works')

        response = client.get('/projects?search=Finance')
        assert response.status_code == 200
        data = response.get_json()
        assert data['count'] == 1
        assert data['data'][0]['department'] == 'Finance'

    def test_search_by_notes(self, client, create_project):
        """Search finds projects matching notes."""
        create_project(notes='Meeting with client on Thursday')
        create_project(notes='Reviewed documents')

        response = client.get('/projects?search=Thursday')
        assert response.status_code == 200
        data = response.get_json()
        assert data['count'] == 1
        assert 'Thursday' in data['data'][0]['notes']

    def test_search_by_project_group(self, client, create_project):
        """Search finds projects matching project_group."""
        create_project(project_group='Q4 Public Records')
        create_project(project_group='Municipal Updates')

        response = client.get('/projects?search=Records')
        assert response.status_code == 200
        data = response.get_json()
        assert data['count'] == 1
        assert data['data'][0]['project_group'] == 'Q4 Public Records'

    def test_search_no_match(self, client, create_project):
        """Search with no matches returns empty list."""
        create_project(project_name='Budget Analysis')

        response = client.get('/projects?search=nonexistent')
        assert response.status_code == 200
        data = response.get_json()
        assert data['count'] == 0

    def test_search_combined_with_filters(self, client, create_project):
        """Search can be combined with other filters."""
        create_project(
            project_name='Public Works Contract',
            status=ProjectStatus.IN_PROGRESS
        )
        create_project(
            project_name='Public Health Contract',
            status=ProjectStatus.COMPLETED
        )

        response = client.get('/projects?search=Contract&status=In+Progress&include_completed=true')
        assert response.status_code == 200
        data = response.get_json()
        assert data['count'] == 1
        assert data['data'][0]['project_name'] == 'Public Works Contract'


# ============================================================================
# Projects HTML Page Routes Tests
# ============================================================================

class TestProjectsHtmlRoutes:
    """Tests for HTML page routes for projects."""

    def test_projects_page_returns_200(self, client):
        """Projects page returns 200 status."""
        response = client.get('/projects/page')
        assert response.status_code == 200

    def test_projects_page_returns_html(self, client):
        """Projects page returns HTML content type."""
        response = client.get('/projects/page')
        assert response.status_code == 200
        assert response.content_type.startswith('text/html')

    def test_projects_page_contains_table(self, client):
        """Projects page contains table element."""
        response = client.get('/projects/page')
        html = response.data.decode('utf-8')
        assert '<table' in html
        assert 'projects-table' in html

    def test_projects_page_displays_projects(self, client, create_project):
        """Projects page displays project data."""
        create_project(project_name='Test Project ABC', department='Test Dept')

        response = client.get('/projects/page')
        html = response.data.decode('utf-8')

        assert 'Test Project ABC' in html
        assert 'Test Dept' in html

    def test_projects_page_with_search(self, client, create_project):
        """Projects page filters with search param."""
        create_project(project_name='Municipal Review')
        create_project(project_name='Budget Analysis')

        response = client.get('/projects/page?search=Municipal')
        html = response.data.decode('utf-8')

        assert 'Municipal Review' in html
        # Budget should not appear
        assert 'Budget Analysis' not in html

    def test_projects_page_with_filters(self, client, create_project):
        """Projects page applies filters."""
        create_project(project_name='Finance Project', department='Finance')
        create_project(project_name='HR Project', department='Human Resources')

        response = client.get('/projects/page?department=Finance')
        html = response.data.decode('utf-8')

        assert 'Finance Project' in html
        assert 'HR Project' not in html

    def test_projects_table_rows_returns_200(self, client):
        """Projects table rows partial returns 200."""
        response = client.get('/projects/table_rows')
        assert response.status_code == 200

    def test_projects_table_rows_returns_html(self, client):
        """Projects table rows returns HTML content type."""
        response = client.get('/projects/table_rows')
        assert response.status_code == 200
        assert response.content_type.startswith('text/html')

    def test_projects_table_rows_is_partial(self, client, create_project):
        """Projects table rows returns partial HTML (no full page)."""
        create_project(project_name='Test Project')

        response = client.get('/projects/table_rows')
        html = response.data.decode('utf-8')

        # Should contain table row data
        assert '<tr' in html
        # Should NOT contain full page structure
        assert '<!DOCTYPE' not in html
        assert '<head>' not in html

    def test_projects_table_rows_with_search(self, client, create_project):
        """Projects table rows filters with search."""
        create_project(project_name='Municipal Review')
        create_project(project_name='Budget Analysis')

        response = client.get('/projects/table_rows?search=Municipal')
        html = response.data.decode('utf-8')

        assert 'Municipal Review' in html
        assert 'Budget Analysis' not in html

    def test_projects_table_rows_empty_state(self, client):
        """Projects table rows shows empty state message."""
        response = client.get('/projects/table_rows')
        html = response.data.decode('utf-8')

        assert 'No projects found' in html

    def test_projects_page_excludes_completed_by_default(self, client, create_project):
        """Projects page excludes completed by default."""
        create_project(project_name='Active Project', status=ProjectStatus.IN_PROGRESS)
        create_project(project_name='Done Project', status=ProjectStatus.COMPLETED)

        response = client.get('/projects/page')
        html = response.data.decode('utf-8')

        assert 'Active Project' in html
        assert 'Done Project' not in html

    def test_projects_page_includes_completed_when_requested(self, client, create_project):
        """Projects page includes completed when requested."""
        create_project(project_name='Active Project', status=ProjectStatus.IN_PROGRESS)
        create_project(project_name='Done Project', status=ProjectStatus.COMPLETED)

        response = client.get('/projects/page?include_completed=true')
        html = response.data.decode('utf-8')

        assert 'Active Project' in html
        assert 'Done Project' in html


# ============================================================================
# Project Detail & Edit HTML Routes
# ============================================================================

class TestProjectDetailRoutes:
    """Tests for project detail, edit, and related HTML routes."""

    def test_view_project_returns_200(self, client, create_project):
        """View project page returns 200 for existing project."""
        project_id = create_project(project_name='View Test Project')
        response = client.get(f'/projects/{project_id}/view')
        assert response.status_code == 200

    def test_view_project_returns_html(self, client, create_project):
        """View project page returns HTML content."""
        project_id = create_project(project_name='View Test Project')
        response = client.get(f'/projects/{project_id}/view')
        assert response.content_type.startswith('text/html')

    def test_view_project_displays_project_name(self, client, create_project):
        """View project page displays the project name."""
        project_id = create_project(project_name='Unique Project Name XYZ')
        response = client.get(f'/projects/{project_id}/view')
        html = response.data.decode('utf-8')
        assert 'Unique Project Name XYZ' in html

    def test_view_project_displays_all_fields(self, client, create_project):
        """View project page displays all project fields."""
        project_id = create_project(
            project_name='Full Data Project',
            department='Finance',
            assigned_attorney='Alice Attorney',
            qcp_attorney='Bob QCP',
            status=ProjectStatus.UNDER_REVIEW
        )
        response = client.get(f'/projects/{project_id}/view')
        html = response.data.decode('utf-8')

        assert 'Full Data Project' in html
        assert 'Finance' in html
        assert 'Alice Attorney' in html
        assert 'Bob QCP' in html
        assert 'Under Review' in html

    def test_view_project_not_found_redirects(self, client):
        """View project redirects to projects page if not found."""
        response = client.get('/projects/99999/view')
        assert response.status_code == 302
        assert '/projects/page' in response.location

    def test_edit_project_form_returns_200(self, client, create_project):
        """Edit project form returns 200 for existing project."""
        project_id = create_project(project_name='Edit Test Project')
        response = client.get(f'/projects/{project_id}/edit')
        assert response.status_code == 200

    def test_edit_project_form_displays_current_values(self, client, create_project):
        """Edit project form displays current values in form fields."""
        project_id = create_project(
            project_name='Editable Project',
            department='Human Resources'
        )
        response = client.get(f'/projects/{project_id}/edit')
        html = response.data.decode('utf-8')

        assert 'Editable Project' in html
        assert 'Human Resources' in html
        # Should have form elements
        assert '<form' in html
        assert 'method="POST"' in html

    def test_edit_project_form_not_found_redirects(self, client):
        """Edit project form redirects to projects page if not found."""
        response = client.get('/projects/99999/edit')
        assert response.status_code == 302
        assert '/projects/page' in response.location

    def test_update_project_form_updates_project(self, client, app, create_project):
        """Update project form successfully updates the project."""
        project_id = create_project(
            project_name='Original Name',
            department='Original Dept'
        )

        response = client.post(f'/projects/{project_id}/update', data={
            'project_name': 'Updated Name',
            'department': 'Updated Dept',
            'assigned_attorney': 'John Smith',
            'qcp_attorney': 'Jane Doe',
            'date_to_client': '2026-01-01',
            'date_assigned_to_us': '2026-01-05',
            'status': 'In Progress'
        })

        # Should redirect to view page
        assert response.status_code == 302
        assert f'/projects/{project_id}/view' in response.location

        # Verify update was applied
        with app.app_context():
            from app.services import project_service
            updated = project_service.get_project(project_id)
            assert updated.project_name == 'Updated Name'
            assert updated.department == 'Updated Dept'

    def test_update_project_form_appends_note(self, client, app, create_project):
        """Update project form appends new note with timestamp."""
        project_id = create_project(project_name='Note Test Project')

        response = client.post(f'/projects/{project_id}/update', data={
            'project_name': 'Note Test Project',
            'department': 'Public Works',
            'assigned_attorney': 'John Smith',
            'qcp_attorney': 'Jane Doe',
            'date_to_client': '2026-01-01',
            'date_assigned_to_us': '2026-01-05',
            'status': 'In Progress',
            'new_note': 'This is a test note'
        })

        assert response.status_code == 302

        with app.app_context():
            from app.services import project_service
            updated = project_service.get_project(project_id)
            assert 'This is a test note' in updated.notes
            assert ']: ' in updated.notes  # Timestamp format

    def test_update_project_form_not_found_redirects(self, client):
        """Update project form redirects to projects page if not found."""
        response = client.post('/projects/99999/update', data={
            'project_name': 'Test',
            'department': 'Test',
            'assigned_attorney': 'Test',
            'qcp_attorney': 'Test',
            'date_to_client': '2026-01-01',
            'date_assigned_to_us': '2026-01-05',
            'status': 'In Progress'
        })
        assert response.status_code == 302
        assert '/projects/page' in response.location

    def test_clone_project_redirects_to_new_form(self, client, create_project):
        """Clone project redirects to new project form with pre-filled data."""
        project_id = create_project(
            project_name='Clone Source',
            department='Test Dept',
            assigned_attorney='Test Attorney',
            qcp_attorney='Test QCP',
            project_group='Test Group'
        )
        response = client.get(f'/projects/{project_id}/clone')
        # Should redirect to new project form with params
        assert response.status_code == 302
        assert '/projects/new' in response.location
        assert 'clone_from=' in response.location
        assert 'Copy+of+Clone+Source' in response.location or 'Copy%20of%20Clone%20Source' in response.location

    def test_clone_project_not_found_redirects(self, client):
        """Clone project redirects to projects page if not found."""
        response = client.get('/projects/99999/clone')
        assert response.status_code == 302
        assert '/projects/page' in response.location

    def test_delete_project_form_deletes(self, client, app, create_project):
        """Delete project form soft-deletes the project."""
        project_id = create_project(project_name='Delete Me')

        response = client.post(f'/projects/{project_id}/delete')

        # Should redirect to projects page
        assert response.status_code == 302
        assert '/projects/page' in response.location

        # Verify soft delete was applied
        with app.app_context():
            from app.services import project_service
            deleted = project_service.get_project(project_id)
            assert deleted is None  # Should not be found after soft delete

    def test_delete_project_form_not_found_redirects(self, client):
        """Delete project form redirects to projects page if not found."""
        response = client.post('/projects/99999/delete')
        assert response.status_code == 302
        assert '/projects/page' in response.location

    def test_table_row_links_to_detail_page(self, client, create_project):
        """Table rows link to the detail page."""
        project_id = create_project(project_name='Link Test')
        response = client.get('/projects/table_rows')
        html = response.data.decode('utf-8')

        # Check that row has onclick with correct URL
        assert f'/projects/{project_id}/view' in html


# ============================================================================
# New Project Form Tests (Sprint 5.1)
# ============================================================================

class TestNewProjectForm:
    """Tests for new project form routes."""

    def test_new_project_form_renders(self, client):
        """GET /projects/new renders the new project form."""
        response = client.get('/projects/new')
        assert response.status_code == 200
        html = response.data.decode('utf-8')
        assert 'New Project' in html
        assert 'Create Project' in html
        assert 'project_name' in html

    def test_new_project_form_has_default_date(self, client):
        """New project form defaults date_assigned_to_us to today."""
        response = client.get('/projects/new')
        assert response.status_code == 200
        html = response.data.decode('utf-8')
        # The today variable is passed to the template
        today_str = date.today().strftime('%Y-%m-%d')
        assert today_str in html

    def test_new_project_form_clone_prefill(self, client, create_project):
        """New project form shows prefilled data when cloning."""
        project_id = create_project(
            project_name='Original Project',
            department='Test Dept',
            assigned_attorney='Test Attorney',
            qcp_attorney='Test QCP'
        )
        response = client.get(f'/projects/new?clone_from={project_id}&project_name=Copy&department=Test+Dept&assigned_attorney=Test+Attorney&qcp_attorney=Test+QCP')
        assert response.status_code == 200
        html = response.data.decode('utf-8')
        assert 'Cloning' in html or 'Clone' in html
        assert 'Test Dept' in html
        assert 'Test Attorney' in html
        assert 'Test QCP' in html

    def test_create_project_form_success(self, client, app):
        """POST /projects/create creates a project and redirects."""
        response = client.post('/projects/create', data={
            'project_name': 'New Test Project',
            'department': 'New Dept',
            'assigned_attorney': 'New Attorney',
            'qcp_attorney': 'New QCP',
            'date_to_client': '2026-01-01',
            'date_assigned_to_us': '2026-01-05',
            'status': 'In Progress'
        })

        # Should redirect to projects page
        assert response.status_code == 302
        assert '/projects/page' in response.location

        # Verify project was created
        with app.app_context():
            from app.services import project_service
            projects = project_service.get_all_projects({'include_completed': True})
            names = [p.project_name for p in projects]
            assert 'New Test Project' in names

    def test_create_project_form_with_notes(self, client, app):
        """POST /projects/create creates a project with initial notes."""
        response = client.post('/projects/create', data={
            'project_name': 'Project With Notes',
            'department': 'Test Dept',
            'assigned_attorney': 'Test Attorney',
            'qcp_attorney': 'Test QCP',
            'date_to_client': '2026-01-01',
            'date_assigned_to_us': '2026-01-05',
            'status': 'In Progress',
            'notes': 'Initial project notes'
        })

        assert response.status_code == 302

        # Verify notes were saved
        with app.app_context():
            from app.services import project_service
            projects = project_service.get_all_projects({'include_completed': True})
            project = next((p for p in projects if p.project_name == 'Project With Notes'), None)
            assert project is not None
            assert 'Initial project notes' in project.notes

    def test_create_project_form_missing_required_fields(self, client):
        """POST /projects/create re-renders form on missing required fields."""
        response = client.post('/projects/create', data={
            'project_name': 'Incomplete Project',
            # Missing department, attorneys, dates
            'status': 'In Progress'
        })

        # Should re-render form with error (not redirect)
        assert response.status_code == 200
        html = response.data.decode('utf-8')
        assert 'Missing required fields' in html or 'error' in html.lower()
        # Form data should be preserved
        assert 'Incomplete Project' in html

    def test_create_project_form_invalid_date(self, client):
        """POST /projects/create re-renders form on invalid date format."""
        response = client.post('/projects/create', data={
            'project_name': 'Bad Date Project',
            'department': 'Test Dept',
            'assigned_attorney': 'Test Attorney',
            'qcp_attorney': 'Test QCP',
            'date_to_client': 'not-a-date',  # Invalid date
            'date_assigned_to_us': '2026-01-05',
            'status': 'In Progress'
        })

        # Should re-render form with error
        assert response.status_code == 200
        html = response.data.decode('utf-8')
        assert 'Invalid date' in html or 'error' in html.lower()

    def test_create_project_form_with_optional_dates(self, client, app):
        """POST /projects/create handles optional deadline dates."""
        response = client.post('/projects/create', data={
            'project_name': 'Optional Dates Project',
            'department': 'Test Dept',
            'assigned_attorney': 'Test Attorney',
            'qcp_attorney': 'Test QCP',
            'date_to_client': '2026-01-01',
            'date_assigned_to_us': '2026-01-05',
            'internal_deadline': '2026-01-15',
            'delivery_deadline': '2026-01-20',
            'status': 'In Progress'
        })

        assert response.status_code == 302

        # Verify dates were saved
        with app.app_context():
            from app.services import project_service
            projects = project_service.get_all_projects({'include_completed': True})
            project = next((p for p in projects if p.project_name == 'Optional Dates Project'), None)
            assert project is not None
            assert project.internal_deadline == date(2026, 1, 15)
            assert project.delivery_deadline == date(2026, 1, 20)
