"""Tests for the project service layer.

Comprehensive tests covering CRUD operations, soft delete,
soft normalization, filtering, sorting, and append-only notes.
"""
import pytest
from datetime import date, datetime, timedelta

from app import db
from app.models import Project, ProjectStatus
from app.services import (
    create_project,
    get_project,
    get_all_projects,
    update_project,
    delete_project,
    append_note,
    get_distinct_values,
    get_overdue_projects,
    get_due_this_week,
    get_longer_deadline,
    get_recently_completed,
)


class TestCreateProject:
    """Tests for create_project function."""

    def test_create_project_with_required_fields(self, app):
        """Create project with only required fields."""
        with app.app_context():
            data = {
                'project_name': 'Test Project',
                'department': 'Public Works',
                'date_to_client': date(2026, 1, 1),
                'date_assigned_to_us': date(2026, 1, 5),
                'assigned_attorney': 'John Smith',
                'qcp_attorney': 'Jane Doe',
            }
            project = create_project(data)

            assert project.id is not None
            assert project.project_name == 'Test Project'
            assert project.department == 'Public Works'
            assert project.status == ProjectStatus.IN_PROGRESS
            assert project.notes is None

    def test_create_project_with_all_fields(self, app, sample_project_data):
        """Create project with all fields populated."""
        with app.app_context():
            project = create_project(sample_project_data)

            assert project.id is not None
            assert project.project_name == sample_project_data['project_name']
            assert project.project_group == sample_project_data['project_group']
            assert project.internal_deadline == sample_project_data['internal_deadline']
            assert project.delivery_deadline == sample_project_data['delivery_deadline']
            assert project.notes == sample_project_data['notes']

    def test_create_project_missing_required_field(self, app):
        """Create project with missing required field raises error."""
        with app.app_context():
            data = {
                'project_name': 'Test Project',
                # Missing department and other required fields
            }
            with pytest.raises(ValueError) as excinfo:
                create_project(data)
            assert 'Missing required fields' in str(excinfo.value)

    def test_create_project_applies_soft_normalization(self, app):
        """Create project normalizes department to existing canonical value."""
        with app.app_context():
            # Create first project with canonical department name
            data1 = {
                'project_name': 'First Project',
                'department': 'Public Works',
                'date_to_client': date(2026, 1, 1),
                'date_assigned_to_us': date(2026, 1, 5),
                'assigned_attorney': 'John Smith',
                'qcp_attorney': 'Jane Doe',
            }
            create_project(data1)

            # Create second project with different case
            data2 = {
                'project_name': 'Second Project',
                'department': 'public works',  # lowercase
                'date_to_client': date(2026, 1, 1),
                'date_assigned_to_us': date(2026, 1, 5),
                'assigned_attorney': 'john smith',  # lowercase
                'qcp_attorney': 'JANE DOE',  # uppercase
            }
            project2 = create_project(data2)

            # Should be normalized to match existing values
            assert project2.department == 'Public Works'
            assert project2.assigned_attorney == 'John Smith'
            assert project2.qcp_attorney == 'Jane Doe'


class TestGetProject:
    """Tests for get_project function."""

    def test_get_project_by_id(self, app, sample_project_data):
        """Get existing project by ID."""
        with app.app_context():
            created = create_project(sample_project_data)
            project = get_project(created.id)

            assert project is not None
            assert project.id == created.id
            assert project.project_name == sample_project_data['project_name']

    def test_get_project_not_found(self, app):
        """Get non-existent project returns None."""
        with app.app_context():
            project = get_project(99999)
            assert project is None

    def test_get_project_excludes_deleted(self, app, sample_project_data):
        """Get soft-deleted project returns None."""
        with app.app_context():
            created = create_project(sample_project_data)
            delete_project(created.id)
            project = get_project(created.id)

            assert project is None


class TestGetAllProjects:
    """Tests for get_all_projects function."""

    def test_get_all_projects_empty(self, app):
        """Get all projects when none exist."""
        with app.app_context():
            projects = get_all_projects()
            assert projects == []

    def test_get_all_projects_returns_all(self, app):
        """Get all projects returns all non-deleted projects."""
        with app.app_context():
            # Create 3 projects
            for i in range(3):
                create_project({
                    'project_name': f'Project {i}',
                    'department': 'Public Works',
                    'date_to_client': date(2026, 1, 1),
                    'date_assigned_to_us': date(2026, 1, 5),
                    'assigned_attorney': 'John Smith',
                    'qcp_attorney': 'Jane Doe',
                })

            projects = get_all_projects()
            assert len(projects) == 3

    def test_get_all_projects_excludes_deleted(self, app):
        """Get all projects excludes soft-deleted by default."""
        with app.app_context():
            # Create 3 projects
            project_ids = []
            for i in range(3):
                p = create_project({
                    'project_name': f'Project {i}',
                    'department': 'Public Works',
                    'date_to_client': date(2026, 1, 1),
                    'date_assigned_to_us': date(2026, 1, 5),
                    'assigned_attorney': 'John Smith',
                    'qcp_attorney': 'Jane Doe',
                })
                project_ids.append(p.id)

            # Delete one
            delete_project(project_ids[0])

            projects = get_all_projects()
            assert len(projects) == 2

    def test_get_all_projects_include_deleted(self, app):
        """Get all projects can include soft-deleted when requested."""
        with app.app_context():
            # Create 3 projects
            project_ids = []
            for i in range(3):
                p = create_project({
                    'project_name': f'Project {i}',
                    'department': 'Public Works',
                    'date_to_client': date(2026, 1, 1),
                    'date_assigned_to_us': date(2026, 1, 5),
                    'assigned_attorney': 'John Smith',
                    'qcp_attorney': 'Jane Doe',
                })
                project_ids.append(p.id)

            # Delete one
            delete_project(project_ids[0])

            projects = get_all_projects({'include_deleted': True})
            assert len(projects) == 3


class TestGetAllProjectsFiltering:
    """Tests for filtering in get_all_projects."""

    def test_filter_by_single_status(self, app):
        """Filter by single status value."""
        with app.app_context():
            # Create projects with different statuses
            for status in [ProjectStatus.IN_PROGRESS, ProjectStatus.COMPLETED,
                          ProjectStatus.IN_PROGRESS]:
                create_project({
                    'project_name': f'Project {status}',
                    'department': 'Public Works',
                    'date_to_client': date(2026, 1, 1),
                    'date_assigned_to_us': date(2026, 1, 5),
                    'assigned_attorney': 'John Smith',
                    'qcp_attorney': 'Jane Doe',
                    'status': status,
                })

            projects = get_all_projects({'status': ProjectStatus.IN_PROGRESS})
            assert len(projects) == 2
            assert all(p.status == ProjectStatus.IN_PROGRESS for p in projects)

    def test_filter_by_multiple_statuses(self, app):
        """Filter by multiple status values."""
        with app.app_context():
            # Create projects with different statuses
            statuses = [ProjectStatus.IN_PROGRESS, ProjectStatus.COMPLETED,
                       ProjectStatus.UNDER_REVIEW, ProjectStatus.ON_HOLD]
            for i, status in enumerate(statuses):
                create_project({
                    'project_name': f'Project {i}',
                    'department': 'Public Works',
                    'date_to_client': date(2026, 1, 1),
                    'date_assigned_to_us': date(2026, 1, 5),
                    'assigned_attorney': 'John Smith',
                    'qcp_attorney': 'Jane Doe',
                    'status': status,
                })

            projects = get_all_projects({
                'status': [ProjectStatus.IN_PROGRESS, ProjectStatus.UNDER_REVIEW]
            })
            assert len(projects) == 2

    def test_filter_by_department_case_insensitive(self, app):
        """Filter by department is case-insensitive."""
        with app.app_context():
            create_project({
                'project_name': 'Project 1',
                'department': 'Public Works',
                'date_to_client': date(2026, 1, 1),
                'date_assigned_to_us': date(2026, 1, 5),
                'assigned_attorney': 'John Smith',
                'qcp_attorney': 'Jane Doe',
            })
            create_project({
                'project_name': 'Project 2',
                'department': 'Finance',
                'date_to_client': date(2026, 1, 1),
                'date_assigned_to_us': date(2026, 1, 5),
                'assigned_attorney': 'John Smith',
                'qcp_attorney': 'Jane Doe',
            })

            # Search with different case
            projects = get_all_projects({'department': 'PUBLIC WORKS'})
            assert len(projects) == 1
            assert projects[0].department == 'Public Works'

    def test_filter_by_assigned_attorney_case_insensitive(self, app):
        """Filter by assigned attorney is case-insensitive."""
        with app.app_context():
            create_project({
                'project_name': 'Project 1',
                'department': 'Public Works',
                'date_to_client': date(2026, 1, 1),
                'date_assigned_to_us': date(2026, 1, 5),
                'assigned_attorney': 'John Smith',
                'qcp_attorney': 'Jane Doe',
            })
            create_project({
                'project_name': 'Project 2',
                'department': 'Public Works',
                'date_to_client': date(2026, 1, 1),
                'date_assigned_to_us': date(2026, 1, 5),
                'assigned_attorney': 'Bob Jones',
                'qcp_attorney': 'Jane Doe',
            })

            projects = get_all_projects({'assigned_attorney': 'john smith'})
            assert len(projects) == 1
            assert projects[0].assigned_attorney == 'John Smith'

    def test_filter_by_qcp_attorney(self, app):
        """Filter by QCP attorney."""
        with app.app_context():
            create_project({
                'project_name': 'Project 1',
                'department': 'Public Works',
                'date_to_client': date(2026, 1, 1),
                'date_assigned_to_us': date(2026, 1, 5),
                'assigned_attorney': 'John Smith',
                'qcp_attorney': 'Jane Doe',
            })
            create_project({
                'project_name': 'Project 2',
                'department': 'Public Works',
                'date_to_client': date(2026, 1, 1),
                'date_assigned_to_us': date(2026, 1, 5),
                'assigned_attorney': 'John Smith',
                'qcp_attorney': 'Bob Wilson',
            })

            projects = get_all_projects({'qcp_attorney': 'Jane Doe'})
            assert len(projects) == 1

    def test_filter_by_delivery_deadline_range(self, app):
        """Filter by delivery deadline date range."""
        with app.app_context():
            # Create projects with different deadlines
            create_project({
                'project_name': 'Early Project',
                'department': 'Public Works',
                'date_to_client': date(2026, 1, 1),
                'date_assigned_to_us': date(2026, 1, 5),
                'assigned_attorney': 'John Smith',
                'qcp_attorney': 'Jane Doe',
                'delivery_deadline': date(2026, 1, 10),
            })
            create_project({
                'project_name': 'Mid Project',
                'department': 'Public Works',
                'date_to_client': date(2026, 1, 1),
                'date_assigned_to_us': date(2026, 1, 5),
                'assigned_attorney': 'John Smith',
                'qcp_attorney': 'Jane Doe',
                'delivery_deadline': date(2026, 1, 20),
            })
            create_project({
                'project_name': 'Late Project',
                'department': 'Public Works',
                'date_to_client': date(2026, 1, 1),
                'date_assigned_to_us': date(2026, 1, 5),
                'assigned_attorney': 'John Smith',
                'qcp_attorney': 'Jane Doe',
                'delivery_deadline': date(2026, 1, 30),
            })

            projects = get_all_projects({
                'delivery_deadline_from': date(2026, 1, 15),
                'delivery_deadline_to': date(2026, 1, 25),
            })
            assert len(projects) == 1
            assert projects[0].project_name == 'Mid Project'

    def test_filter_by_date_assigned_range(self, app):
        """Filter by date assigned to us range."""
        with app.app_context():
            create_project({
                'project_name': 'Early Assignment',
                'department': 'Public Works',
                'date_to_client': date(2026, 1, 1),
                'date_assigned_to_us': date(2026, 1, 5),
                'assigned_attorney': 'John Smith',
                'qcp_attorney': 'Jane Doe',
            })
            create_project({
                'project_name': 'Late Assignment',
                'department': 'Public Works',
                'date_to_client': date(2026, 1, 1),
                'date_assigned_to_us': date(2026, 1, 15),
                'assigned_attorney': 'John Smith',
                'qcp_attorney': 'Jane Doe',
            })

            projects = get_all_projects({
                'date_assigned_from': date(2026, 1, 10),
            })
            assert len(projects) == 1
            assert projects[0].project_name == 'Late Assignment'

    def test_combine_multiple_filters(self, app):
        """Combine multiple filter criteria."""
        with app.app_context():
            create_project({
                'project_name': 'Match All',
                'department': 'Public Works',
                'date_to_client': date(2026, 1, 1),
                'date_assigned_to_us': date(2026, 1, 5),
                'assigned_attorney': 'John Smith',
                'qcp_attorney': 'Jane Doe',
                'status': ProjectStatus.IN_PROGRESS,
            })
            create_project({
                'project_name': 'Wrong Department',
                'department': 'Finance',
                'date_to_client': date(2026, 1, 1),
                'date_assigned_to_us': date(2026, 1, 5),
                'assigned_attorney': 'John Smith',
                'qcp_attorney': 'Jane Doe',
                'status': ProjectStatus.IN_PROGRESS,
            })
            create_project({
                'project_name': 'Wrong Status',
                'department': 'Public Works',
                'date_to_client': date(2026, 1, 1),
                'date_assigned_to_us': date(2026, 1, 5),
                'assigned_attorney': 'John Smith',
                'qcp_attorney': 'Jane Doe',
                'status': ProjectStatus.COMPLETED,
            })

            projects = get_all_projects({
                'department': 'Public Works',
                'status': ProjectStatus.IN_PROGRESS,
            })
            assert len(projects) == 1
            assert projects[0].project_name == 'Match All'


class TestGetAllProjectsSorting:
    """Tests for sorting in get_all_projects."""

    def test_sort_by_delivery_deadline_asc(self, app):
        """Sort by delivery deadline ascending (default)."""
        with app.app_context():
            create_project({
                'project_name': 'Late',
                'department': 'Public Works',
                'date_to_client': date(2026, 1, 1),
                'date_assigned_to_us': date(2026, 1, 5),
                'assigned_attorney': 'John Smith',
                'qcp_attorney': 'Jane Doe',
                'delivery_deadline': date(2026, 1, 30),
            })
            create_project({
                'project_name': 'Early',
                'department': 'Public Works',
                'date_to_client': date(2026, 1, 1),
                'date_assigned_to_us': date(2026, 1, 5),
                'assigned_attorney': 'John Smith',
                'qcp_attorney': 'Jane Doe',
                'delivery_deadline': date(2026, 1, 10),
            })

            projects = get_all_projects({'sort_by': 'delivery_deadline', 'sort_dir': 'asc'})
            assert projects[0].project_name == 'Early'
            assert projects[1].project_name == 'Late'

    def test_sort_by_delivery_deadline_desc(self, app):
        """Sort by delivery deadline descending."""
        with app.app_context():
            create_project({
                'project_name': 'Late',
                'department': 'Public Works',
                'date_to_client': date(2026, 1, 1),
                'date_assigned_to_us': date(2026, 1, 5),
                'assigned_attorney': 'John Smith',
                'qcp_attorney': 'Jane Doe',
                'delivery_deadline': date(2026, 1, 30),
            })
            create_project({
                'project_name': 'Early',
                'department': 'Public Works',
                'date_to_client': date(2026, 1, 1),
                'date_assigned_to_us': date(2026, 1, 5),
                'assigned_attorney': 'John Smith',
                'qcp_attorney': 'Jane Doe',
                'delivery_deadline': date(2026, 1, 10),
            })

            projects = get_all_projects({'sort_by': 'delivery_deadline', 'sort_dir': 'desc'})
            assert projects[0].project_name == 'Late'
            assert projects[1].project_name == 'Early'

    def test_sort_by_project_name(self, app):
        """Sort by project name."""
        with app.app_context():
            create_project({
                'project_name': 'Zebra Project',
                'department': 'Public Works',
                'date_to_client': date(2026, 1, 1),
                'date_assigned_to_us': date(2026, 1, 5),
                'assigned_attorney': 'John Smith',
                'qcp_attorney': 'Jane Doe',
            })
            create_project({
                'project_name': 'Alpha Project',
                'department': 'Public Works',
                'date_to_client': date(2026, 1, 1),
                'date_assigned_to_us': date(2026, 1, 5),
                'assigned_attorney': 'John Smith',
                'qcp_attorney': 'Jane Doe',
            })

            projects = get_all_projects({'sort_by': 'project_name', 'sort_dir': 'asc'})
            assert projects[0].project_name == 'Alpha Project'
            assert projects[1].project_name == 'Zebra Project'

    def test_sort_handles_null_values(self, app):
        """Sort handles null values correctly (nulls last)."""
        with app.app_context():
            create_project({
                'project_name': 'No Deadline',
                'department': 'Public Works',
                'date_to_client': date(2026, 1, 1),
                'date_assigned_to_us': date(2026, 1, 5),
                'assigned_attorney': 'John Smith',
                'qcp_attorney': 'Jane Doe',
                'delivery_deadline': None,
            })
            create_project({
                'project_name': 'Has Deadline',
                'department': 'Public Works',
                'date_to_client': date(2026, 1, 1),
                'date_assigned_to_us': date(2026, 1, 5),
                'assigned_attorney': 'John Smith',
                'qcp_attorney': 'Jane Doe',
                'delivery_deadline': date(2026, 1, 15),
            })

            projects = get_all_projects({'sort_by': 'delivery_deadline', 'sort_dir': 'asc'})
            assert projects[0].project_name == 'Has Deadline'
            assert projects[1].project_name == 'No Deadline'


class TestUpdateProject:
    """Tests for update_project function."""

    def test_update_project_fields(self, app, sample_project_data):
        """Update project updates fields correctly."""
        with app.app_context():
            created = create_project(sample_project_data)
            updated = update_project(created.id, {
                'project_name': 'Updated Name',
                'status': ProjectStatus.COMPLETED,
            })

            assert updated.project_name == 'Updated Name'
            assert updated.status == ProjectStatus.COMPLETED
            # Other fields unchanged
            assert updated.department == sample_project_data['department']

    def test_update_project_applies_soft_normalization(self, app, sample_project_data):
        """Update project applies soft normalization."""
        with app.app_context():
            created = create_project(sample_project_data)

            # Update with different case
            updated = update_project(created.id, {
                'department': 'public works',  # lowercase
            })

            # Should normalize to existing canonical value
            assert updated.department == 'Public Works'

    def test_update_project_not_found(self, app):
        """Update non-existent project returns None."""
        with app.app_context():
            result = update_project(99999, {'project_name': 'New Name'})
            assert result is None

    def test_update_project_cannot_update_deleted(self, app, sample_project_data):
        """Cannot update soft-deleted project."""
        with app.app_context():
            created = create_project(sample_project_data)
            delete_project(created.id)

            result = update_project(created.id, {'project_name': 'New Name'})
            assert result is None


class TestDeleteProject:
    """Tests for delete_project function."""

    def test_delete_project_sets_deleted_at(self, app, sample_project_data):
        """Delete project sets deleted_at timestamp."""
        with app.app_context():
            created = create_project(sample_project_data)
            result = delete_project(created.id)

            assert result is True

            # Verify the project still exists but is marked deleted
            project = db.session.get(Project, created.id)
            assert project is not None
            assert project.deleted_at is not None

    def test_delete_project_not_found(self, app):
        """Delete non-existent project returns False."""
        with app.app_context():
            result = delete_project(99999)
            assert result is False

    def test_delete_project_already_deleted(self, app, sample_project_data):
        """Delete already-deleted project returns False."""
        with app.app_context():
            created = create_project(sample_project_data)
            delete_project(created.id)

            # Try to delete again
            result = delete_project(created.id)
            assert result is False


class TestAppendNote:
    """Tests for append_note function."""

    def test_append_note_to_empty(self, app, sample_project_data):
        """Append note to project with no existing notes."""
        with app.app_context():
            sample_project_data['notes'] = None
            created = create_project(sample_project_data)
            result = append_note(created.id, 'First note')

            assert result is not None
            assert 'First note' in result.notes
            # Should have timestamp format
            assert result.notes.startswith('[')
            assert ']: First note' in result.notes

    def test_append_note_to_existing(self, app, sample_project_data):
        """Append note preserves existing notes."""
        with app.app_context():
            sample_project_data['notes'] = '[2026-01-01 09:00]: Original note'
            created = create_project(sample_project_data)
            result = append_note(created.id, 'New note')

            assert 'Original note' in result.notes
            assert 'New note' in result.notes
            # New note should be after original
            original_pos = result.notes.find('Original note')
            new_pos = result.notes.find('New note')
            assert new_pos > original_pos

    def test_append_note_format(self, app, sample_project_data):
        """Append note uses correct timestamp format."""
        with app.app_context():
            sample_project_data['notes'] = None
            created = create_project(sample_project_data)
            result = append_note(created.id, 'Test note')

            # Note should be in format [YYYY-MM-DD HH:MM]: content
            import re
            pattern = r'\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}\]: Test note'
            assert re.match(pattern, result.notes)

    def test_append_note_empty_note(self, app, sample_project_data):
        """Append empty note does nothing."""
        with app.app_context():
            original_notes = sample_project_data['notes']
            created = create_project(sample_project_data)
            result = append_note(created.id, '')

            assert result.notes == original_notes

    def test_append_note_not_found(self, app):
        """Append note to non-existent project returns None."""
        with app.app_context():
            result = append_note(99999, 'Note')
            assert result is None


class TestGetDistinctValues:
    """Tests for get_distinct_values function."""

    def test_get_distinct_departments(self, app):
        """Get distinct department values."""
        with app.app_context():
            for dept in ['Public Works', 'Finance', 'Public Works', 'IT']:
                create_project({
                    'project_name': f'Project {dept}',
                    'department': dept,
                    'date_to_client': date(2026, 1, 1),
                    'date_assigned_to_us': date(2026, 1, 5),
                    'assigned_attorney': 'John Smith',
                    'qcp_attorney': 'Jane Doe',
                })

            departments = get_distinct_values('department')
            assert len(departments) == 3
            assert 'Public Works' in departments
            assert 'Finance' in departments
            assert 'IT' in departments

    def test_get_distinct_attorneys(self, app):
        """Get distinct assigned attorney values."""
        with app.app_context():
            for attorney in ['John Smith', 'Jane Doe', 'John Smith']:
                create_project({
                    'project_name': f'Project {attorney}',
                    'department': 'Public Works',
                    'date_to_client': date(2026, 1, 1),
                    'date_assigned_to_us': date(2026, 1, 5),
                    'assigned_attorney': attorney,
                    'qcp_attorney': 'QCP Attorney',
                })

            attorneys = get_distinct_values('assigned_attorney')
            assert len(attorneys) == 2
            assert 'John Smith' in attorneys
            assert 'Jane Doe' in attorneys

    def test_get_distinct_excludes_deleted(self, app):
        """Get distinct values excludes soft-deleted projects."""
        with app.app_context():
            p1 = create_project({
                'project_name': 'Project 1',
                'department': 'Public Works',
                'date_to_client': date(2026, 1, 1),
                'date_assigned_to_us': date(2026, 1, 5),
                'assigned_attorney': 'John Smith',
                'qcp_attorney': 'Jane Doe',
            })
            create_project({
                'project_name': 'Project 2',
                'department': 'Finance',
                'date_to_client': date(2026, 1, 1),
                'date_assigned_to_us': date(2026, 1, 5),
                'assigned_attorney': 'John Smith',
                'qcp_attorney': 'Jane Doe',
            })

            # Delete first project
            delete_project(p1.id)

            departments = get_distinct_values('department')
            assert len(departments) == 1
            assert 'Finance' in departments
            assert 'Public Works' not in departments

    def test_get_distinct_invalid_field(self, app):
        """Get distinct values for invalid field raises error."""
        with app.app_context():
            with pytest.raises(ValueError) as excinfo:
                get_distinct_values('invalid_field')
            assert 'Invalid field' in str(excinfo.value)

    def test_get_distinct_values_sorted(self, app):
        """Get distinct values returns sorted list."""
        with app.app_context():
            for dept in ['Zebra', 'Apple', 'Middle']:
                create_project({
                    'project_name': f'Project {dept}',
                    'department': dept,
                    'date_to_client': date(2026, 1, 1),
                    'date_assigned_to_us': date(2026, 1, 5),
                    'assigned_attorney': 'John Smith',
                    'qcp_attorney': 'Jane Doe',
                })

            departments = get_distinct_values('department')
            assert departments == ['Apple', 'Middle', 'Zebra']


class TestSoftNormalization:
    """Tests for soft normalization behavior."""

    def test_department_normalization(self, app):
        """Department field is normalized to existing canonical value."""
        with app.app_context():
            # Create first with canonical
            create_project({
                'project_name': 'First',
                'department': 'Public Works',
                'date_to_client': date(2026, 1, 1),
                'date_assigned_to_us': date(2026, 1, 5),
                'assigned_attorney': 'John Smith',
                'qcp_attorney': 'Jane Doe',
            })

            # Create second with different case
            second = create_project({
                'project_name': 'Second',
                'department': 'PUBLIC WORKS',
                'date_to_client': date(2026, 1, 1),
                'date_assigned_to_us': date(2026, 1, 5),
                'assigned_attorney': 'John Smith',
                'qcp_attorney': 'Jane Doe',
            })

            assert second.department == 'Public Works'

    def test_new_value_becomes_canonical(self, app):
        """New value that doesn't match existing stays as entered."""
        with app.app_context():
            project = create_project({
                'project_name': 'First',
                'department': 'Brand New Department',
                'date_to_client': date(2026, 1, 1),
                'date_assigned_to_us': date(2026, 1, 5),
                'assigned_attorney': 'New Attorney',
                'qcp_attorney': 'Another Attorney',
            })

            assert project.department == 'Brand New Department'
            assert project.assigned_attorney == 'New Attorney'

    def test_all_normalized_fields(self, app):
        """All three normalized fields work correctly."""
        with app.app_context():
            # Create canonical values
            create_project({
                'project_name': 'First',
                'department': 'Public Works',
                'date_to_client': date(2026, 1, 1),
                'date_assigned_to_us': date(2026, 1, 5),
                'assigned_attorney': 'John Smith',
                'qcp_attorney': 'Jane Doe',
            })

            # Create with all different cases
            second = create_project({
                'project_name': 'Second',
                'department': 'public works',
                'date_to_client': date(2026, 1, 1),
                'date_assigned_to_us': date(2026, 1, 5),
                'assigned_attorney': 'JOHN SMITH',
                'qcp_attorney': 'jane doe',
            })

            assert second.department == 'Public Works'
            assert second.assigned_attorney == 'John Smith'
            assert second.qcp_attorney == 'Jane Doe'


class TestEdgeCases:
    """Tests for edge cases and missing coverage."""

    def test_sort_invalid_field_falls_back_to_default(self, app):
        """Invalid sort_by field falls back to delivery_deadline."""
        with app.app_context():
            create_project({
                'project_name': 'Late Deadline',
                'department': 'Public Works',
                'date_to_client': date(2026, 1, 1),
                'date_assigned_to_us': date(2026, 1, 5),
                'assigned_attorney': 'John Smith',
                'qcp_attorney': 'Jane Doe',
                'delivery_deadline': date(2026, 1, 30),
            })
            create_project({
                'project_name': 'Early Deadline',
                'department': 'Public Works',
                'date_to_client': date(2026, 1, 1),
                'date_assigned_to_us': date(2026, 1, 5),
                'assigned_attorney': 'John Smith',
                'qcp_attorney': 'Jane Doe',
                'delivery_deadline': date(2026, 1, 10),
            })

            # Invalid sort field should fall back to delivery_deadline
            projects = get_all_projects({
                'sort_by': 'nonexistent_field',
                'sort_dir': 'asc'
            })
            assert projects[0].project_name == 'Early Deadline'
            assert projects[1].project_name == 'Late Deadline'

    def test_sort_invalid_field_falls_back_desc(self, app):
        """Invalid sort_by with desc falls back to delivery_deadline desc."""
        with app.app_context():
            create_project({
                'project_name': 'Late Deadline',
                'department': 'Public Works',
                'date_to_client': date(2026, 1, 1),
                'date_assigned_to_us': date(2026, 1, 5),
                'assigned_attorney': 'John Smith',
                'qcp_attorney': 'Jane Doe',
                'delivery_deadline': date(2026, 1, 30),
            })
            create_project({
                'project_name': 'Early Deadline',
                'department': 'Public Works',
                'date_to_client': date(2026, 1, 1),
                'date_assigned_to_us': date(2026, 1, 5),
                'assigned_attorney': 'John Smith',
                'qcp_attorney': 'Jane Doe',
                'delivery_deadline': date(2026, 1, 10),
            })

            projects = get_all_projects({
                'sort_by': 'invalid_column',
                'sort_dir': 'desc'
            })
            assert projects[0].project_name == 'Late Deadline'
            assert projects[1].project_name == 'Early Deadline'

    def test_get_distinct_status_values(self, app):
        """Get distinct status values."""
        with app.app_context():
            create_project({
                'project_name': 'Project 1',
                'department': 'Public Works',
                'date_to_client': date(2026, 1, 1),
                'date_assigned_to_us': date(2026, 1, 5),
                'assigned_attorney': 'John Smith',
                'qcp_attorney': 'Jane Doe',
                'status': ProjectStatus.IN_PROGRESS,
            })
            create_project({
                'project_name': 'Project 2',
                'department': 'Public Works',
                'date_to_client': date(2026, 1, 1),
                'date_assigned_to_us': date(2026, 1, 5),
                'assigned_attorney': 'John Smith',
                'qcp_attorney': 'Jane Doe',
                'status': ProjectStatus.COMPLETED,
            })

            statuses = get_distinct_values('status')
            assert len(statuses) == 2
            assert ProjectStatus.IN_PROGRESS in statuses
            assert ProjectStatus.COMPLETED in statuses

    def test_get_distinct_project_groups(self, app):
        """Get distinct project group values."""
        with app.app_context():
            create_project({
                'project_name': 'Project 1',
                'department': 'Public Works',
                'date_to_client': date(2026, 1, 1),
                'date_assigned_to_us': date(2026, 1, 5),
                'assigned_attorney': 'John Smith',
                'qcp_attorney': 'Jane Doe',
                'project_group': 'Group A',
            })
            create_project({
                'project_name': 'Project 2',
                'department': 'Public Works',
                'date_to_client': date(2026, 1, 1),
                'date_assigned_to_us': date(2026, 1, 5),
                'assigned_attorney': 'John Smith',
                'qcp_attorney': 'Jane Doe',
                'project_group': 'Group B',
            })
            create_project({
                'project_name': 'Project 3',
                'department': 'Public Works',
                'date_to_client': date(2026, 1, 1),
                'date_assigned_to_us': date(2026, 1, 5),
                'assigned_attorney': 'John Smith',
                'qcp_attorney': 'Jane Doe',
                'project_group': None,  # No group
            })

            groups = get_distinct_values('project_group')
            assert len(groups) == 2
            assert 'Group A' in groups
            assert 'Group B' in groups

    def test_filter_with_empty_date_assigned_to(self, app):
        """Filter with empty date_assigned_to value is ignored."""
        with app.app_context():
            create_project({
                'project_name': 'Project 1',
                'department': 'Public Works',
                'date_to_client': date(2026, 1, 1),
                'date_assigned_to_us': date(2026, 1, 5),
                'assigned_attorney': 'John Smith',
                'qcp_attorney': 'Jane Doe',
            })

            # Empty filter values should be ignored
            projects = get_all_projects({
                'date_assigned_to': None,
                'date_assigned_from': None,
            })
            assert len(projects) == 1

    def test_filter_status_as_string(self, app):
        """Filter by status as single string (not list)."""
        with app.app_context():
            create_project({
                'project_name': 'In Progress Project',
                'department': 'Public Works',
                'date_to_client': date(2026, 1, 1),
                'date_assigned_to_us': date(2026, 1, 5),
                'assigned_attorney': 'John Smith',
                'qcp_attorney': 'Jane Doe',
                'status': ProjectStatus.IN_PROGRESS,
            })
            create_project({
                'project_name': 'Completed Project',
                'department': 'Public Works',
                'date_to_client': date(2026, 1, 1),
                'date_assigned_to_us': date(2026, 1, 5),
                'assigned_attorney': 'John Smith',
                'qcp_attorney': 'Jane Doe',
                'status': ProjectStatus.COMPLETED,
            })

            # Pass status as string, not list
            projects = get_all_projects({'status': ProjectStatus.IN_PROGRESS})
            assert len(projects) == 1
            assert projects[0].status == ProjectStatus.IN_PROGRESS

    def test_create_project_invalid_status_raises_error(self, app):
        """Create project with invalid status raises ValueError."""
        with app.app_context():
            data = {
                'project_name': 'Test Project',
                'department': 'Public Works',
                'date_to_client': date(2026, 1, 1),
                'date_assigned_to_us': date(2026, 1, 5),
                'assigned_attorney': 'John Smith',
                'qcp_attorney': 'Jane Doe',
                'status': 'InvalidStatus',
            }
            with pytest.raises(ValueError) as excinfo:
                create_project(data)
            assert 'Invalid status' in str(excinfo.value)

    def test_update_project_invalid_status_raises_error(self, app, sample_project_data):
        """Update project with invalid status raises ValueError."""
        with app.app_context():
            created = create_project(sample_project_data)
            with pytest.raises(ValueError) as excinfo:
                update_project(created.id, {'status': 'BadStatus'})
            assert 'Invalid status' in str(excinfo.value)


class TestDashboardFunctions:
    """Tests for dashboard service functions."""

    def _create_project_with_deadline(self, deadline, status=ProjectStatus.IN_PROGRESS):
        """Helper to create a project with specific deadline and status."""
        return create_project({
            'project_name': f'Project {deadline}',
            'department': 'Public Works',
            'date_to_client': date(2026, 1, 1),
            'date_assigned_to_us': date(2026, 1, 5),
            'assigned_attorney': 'John Smith',
            'qcp_attorney': 'Jane Doe',
            'delivery_deadline': deadline,
            'status': status,
        })

    def test_get_overdue_projects_finds_past_deadline(self, app):
        """Projects with delivery_deadline in the past are overdue."""
        with app.app_context():
            yesterday = date.today() - timedelta(days=1)
            self._create_project_with_deadline(yesterday)

            overdue = get_overdue_projects()
            assert len(overdue) == 1
            assert overdue[0].delivery_deadline == yesterday

    def test_get_overdue_projects_excludes_future_deadline(self, app):
        """Projects with future deadline are not overdue."""
        with app.app_context():
            tomorrow = date.today() + timedelta(days=1)
            self._create_project_with_deadline(tomorrow)

            overdue = get_overdue_projects()
            assert len(overdue) == 0

    def test_get_overdue_projects_excludes_completed(self, app):
        """Completed projects are not shown as overdue."""
        with app.app_context():
            yesterday = date.today() - timedelta(days=1)
            self._create_project_with_deadline(yesterday, ProjectStatus.COMPLETED)

            overdue = get_overdue_projects()
            assert len(overdue) == 0

    def test_get_overdue_projects_excludes_deleted(self, app):
        """Soft-deleted projects are not shown as overdue."""
        with app.app_context():
            yesterday = date.today() - timedelta(days=1)
            project = self._create_project_with_deadline(yesterday)
            delete_project(project.id)

            overdue = get_overdue_projects()
            assert len(overdue) == 0

    def test_get_overdue_projects_excludes_null_deadline(self, app):
        """Projects without delivery_deadline are not overdue."""
        with app.app_context():
            self._create_project_with_deadline(None)

            overdue = get_overdue_projects()
            assert len(overdue) == 0

    def test_get_overdue_projects_orders_by_deadline_asc(self, app):
        """Overdue projects are ordered by deadline ascending (most overdue first)."""
        with app.app_context():
            three_days_ago = date.today() - timedelta(days=3)
            one_day_ago = date.today() - timedelta(days=1)
            self._create_project_with_deadline(one_day_ago)
            self._create_project_with_deadline(three_days_ago)

            overdue = get_overdue_projects()
            assert len(overdue) == 2
            assert overdue[0].delivery_deadline == three_days_ago
            assert overdue[1].delivery_deadline == one_day_ago

    def test_get_due_this_week_finds_upcoming(self, app):
        """Projects due within 7 days are found."""
        with app.app_context():
            in_three_days = date.today() + timedelta(days=3)
            self._create_project_with_deadline(in_three_days)

            due_this_week = get_due_this_week()
            assert len(due_this_week) == 1
            assert due_this_week[0].delivery_deadline == in_three_days

    def test_get_due_this_week_includes_today(self, app):
        """Projects due today are included in due this week."""
        with app.app_context():
            today = date.today()
            self._create_project_with_deadline(today)

            due_this_week = get_due_this_week()
            assert len(due_this_week) == 1

    def test_get_due_this_week_includes_day_seven(self, app):
        """Projects due exactly 7 days from now are included."""
        with app.app_context():
            in_seven_days = date.today() + timedelta(days=7)
            self._create_project_with_deadline(in_seven_days)

            due_this_week = get_due_this_week()
            assert len(due_this_week) == 1

    def test_get_due_this_week_excludes_overdue(self, app):
        """Overdue projects are not included in due this week."""
        with app.app_context():
            yesterday = date.today() - timedelta(days=1)
            self._create_project_with_deadline(yesterday)

            due_this_week = get_due_this_week()
            assert len(due_this_week) == 0

    def test_get_due_this_week_excludes_beyond_seven_days(self, app):
        """Projects due beyond 7 days are not in due this week."""
        with app.app_context():
            in_eight_days = date.today() + timedelta(days=8)
            self._create_project_with_deadline(in_eight_days)

            due_this_week = get_due_this_week()
            assert len(due_this_week) == 0

    def test_get_due_this_week_excludes_completed(self, app):
        """Completed projects are not included in due this week."""
        with app.app_context():
            in_three_days = date.today() + timedelta(days=3)
            self._create_project_with_deadline(in_three_days, ProjectStatus.COMPLETED)

            due_this_week = get_due_this_week()
            assert len(due_this_week) == 0

    def test_get_longer_deadline_finds_future(self, app):
        """Projects due beyond 7 days are found."""
        with app.app_context():
            in_ten_days = date.today() + timedelta(days=10)
            self._create_project_with_deadline(in_ten_days)

            longer = get_longer_deadline()
            assert len(longer) == 1
            assert longer[0].delivery_deadline == in_ten_days

    def test_get_longer_deadline_excludes_this_week(self, app):
        """Projects due within 7 days are not in longer deadline."""
        with app.app_context():
            in_five_days = date.today() + timedelta(days=5)
            self._create_project_with_deadline(in_five_days)

            longer = get_longer_deadline()
            assert len(longer) == 0

    def test_get_longer_deadline_excludes_day_seven(self, app):
        """Projects due exactly 7 days from now are NOT in longer deadline."""
        with app.app_context():
            in_seven_days = date.today() + timedelta(days=7)
            self._create_project_with_deadline(in_seven_days)

            longer = get_longer_deadline()
            assert len(longer) == 0

    def test_get_longer_deadline_excludes_completed(self, app):
        """Completed projects are not in longer deadline."""
        with app.app_context():
            in_ten_days = date.today() + timedelta(days=10)
            self._create_project_with_deadline(in_ten_days, ProjectStatus.COMPLETED)

            longer = get_longer_deadline()
            assert len(longer) == 0

    def test_get_recently_completed_finds_completed(self, app):
        """Recently completed finds completed projects."""
        with app.app_context():
            today = date.today()
            self._create_project_with_deadline(today, ProjectStatus.COMPLETED)

            completed = get_recently_completed()
            assert len(completed) == 1
            assert completed[0].status == ProjectStatus.COMPLETED

    def test_get_recently_completed_excludes_in_progress(self, app):
        """In progress projects are not in recently completed."""
        with app.app_context():
            today = date.today()
            self._create_project_with_deadline(today, ProjectStatus.IN_PROGRESS)

            completed = get_recently_completed()
            assert len(completed) == 0

    def test_get_recently_completed_orders_by_updated_at(self, app):
        """Recently completed returns projects ordered by updated_at desc."""
        with app.app_context():
            today = date.today()
            # Create two completed projects
            project1 = self._create_project_with_deadline(today, ProjectStatus.COMPLETED)
            project2 = self._create_project_with_deadline(today, ProjectStatus.COMPLETED)

            # Update project1 to make it more recent
            from app.services import update_project
            update_project(project1.id, {'project_name': 'Updated Project'})

            completed = get_recently_completed()
            assert len(completed) == 2
            # project1 was updated more recently, so it should be first
            assert completed[0].id == project1.id

    def test_get_recently_completed_respects_limit(self, app):
        """Recently completed respects the limit parameter."""
        with app.app_context():
            today = date.today()
            # Create 15 completed projects
            for i in range(15):
                create_project({
                    'project_name': f'Completed Project {i}',
                    'department': 'Public Works',
                    'date_to_client': date(2026, 1, 1),
                    'date_assigned_to_us': date(2026, 1, 5),
                    'assigned_attorney': 'John Smith',
                    'qcp_attorney': 'Jane Doe',
                    'delivery_deadline': today,
                    'status': ProjectStatus.COMPLETED,
                })

            # Default limit is 10
            completed = get_recently_completed()
            assert len(completed) == 10

            # Custom limit
            completed_5 = get_recently_completed(limit=5)
            assert len(completed_5) == 5

    def test_get_recently_completed_excludes_deleted(self, app):
        """Soft-deleted completed projects are excluded."""
        with app.app_context():
            today = date.today()
            project = self._create_project_with_deadline(today, ProjectStatus.COMPLETED)
            delete_project(project.id)

            completed = get_recently_completed()
            assert len(completed) == 0
