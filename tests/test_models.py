"""Tests for the Project model.

This module contains unit tests for the Project model, verifying
that all fields work correctly and the model behaves as expected.
"""
from datetime import date, datetime, timedelta

import pytest

from app import db
from app.models import Project, ProjectStatus


class TestProjectStatus:
    """Tests for the ProjectStatus enumeration."""

    def test_all_statuses_defined(self):
        """Verify all expected status values are defined."""
        assert ProjectStatus.IN_PROGRESS == "In Progress"
        assert ProjectStatus.UNDER_REVIEW == "Under Review"
        assert ProjectStatus.WAITING_ON_CLIENT == "Waiting on Client"
        assert ProjectStatus.ON_HOLD == "On-Hold"
        assert ProjectStatus.COMPLETED == "Completed"

    def test_all_list_contains_all_statuses(self):
        """Verify ALL list contains all status values."""
        assert len(ProjectStatus.ALL) == 5
        assert ProjectStatus.IN_PROGRESS in ProjectStatus.ALL
        assert ProjectStatus.UNDER_REVIEW in ProjectStatus.ALL
        assert ProjectStatus.WAITING_ON_CLIENT in ProjectStatus.ALL
        assert ProjectStatus.ON_HOLD in ProjectStatus.ALL
        assert ProjectStatus.COMPLETED in ProjectStatus.ALL


class TestProjectModel:
    """Tests for the Project model."""

    def test_create_project_with_required_fields(self, app):
        """Test creating a project with all required fields."""
        with app.app_context():
            project = Project(
                project_name='Test Project',
                department='Public Works',
                date_to_client=date(2026, 1, 1),
                date_assigned_to_us=date(2026, 1, 5),
                assigned_attorney='John Smith',
                qcp_attorney='Jane Doe',
                status=ProjectStatus.IN_PROGRESS,
            )
            db.session.add(project)
            db.session.commit()

            assert project.id is not None
            assert project.project_name == 'Test Project'
            assert project.department == 'Public Works'
            assert project.assigned_attorney == 'John Smith'
            assert project.qcp_attorney == 'Jane Doe'
            assert project.status == ProjectStatus.IN_PROGRESS

    def test_create_project_with_all_fields(self, app, sample_project_data):
        """Test creating a project with all fields including optional ones."""
        with app.app_context():
            project = Project(**sample_project_data)
            db.session.add(project)
            db.session.commit()

            assert project.id is not None
            assert project.project_name == sample_project_data['project_name']
            assert project.project_group == sample_project_data['project_group']
            assert project.department == sample_project_data['department']
            assert project.date_to_client == sample_project_data['date_to_client']
            assert project.date_assigned_to_us == sample_project_data['date_assigned_to_us']
            assert project.internal_deadline == sample_project_data['internal_deadline']
            assert project.delivery_deadline == sample_project_data['delivery_deadline']
            assert project.assigned_attorney == sample_project_data['assigned_attorney']
            assert project.qcp_attorney == sample_project_data['qcp_attorney']
            assert project.status == sample_project_data['status']
            assert project.notes == sample_project_data['notes']

    def test_created_at_auto_set(self, app):
        """Test that created_at is automatically set on creation."""
        with app.app_context():
            before = datetime.utcnow()
            project = Project(
                project_name='Test Project',
                department='Finance',
                date_to_client=date(2026, 1, 1),
                date_assigned_to_us=date(2026, 1, 5),
                assigned_attorney='John Smith',
                qcp_attorney='Jane Doe',
            )
            db.session.add(project)
            db.session.commit()
            after = datetime.utcnow()

            assert project.created_at is not None
            assert before <= project.created_at <= after

    def test_updated_at_auto_set(self, app):
        """Test that updated_at is automatically set on creation."""
        with app.app_context():
            before = datetime.utcnow()
            project = Project(
                project_name='Test Project',
                department='Finance',
                date_to_client=date(2026, 1, 1),
                date_assigned_to_us=date(2026, 1, 5),
                assigned_attorney='John Smith',
                qcp_attorney='Jane Doe',
            )
            db.session.add(project)
            db.session.commit()
            after = datetime.utcnow()

            assert project.updated_at is not None
            assert before <= project.updated_at <= after

    def test_default_status_is_in_progress(self, app):
        """Test that default status is 'In Progress'."""
        with app.app_context():
            project = Project(
                project_name='Test Project',
                department='Finance',
                date_to_client=date(2026, 1, 1),
                date_assigned_to_us=date(2026, 1, 5),
                assigned_attorney='John Smith',
                qcp_attorney='Jane Doe',
            )
            db.session.add(project)
            db.session.commit()

            assert project.status == ProjectStatus.IN_PROGRESS

    def test_optional_fields_can_be_null(self, app):
        """Test that optional fields can be left as None."""
        with app.app_context():
            project = Project(
                project_name='Minimal Project',
                department='HR',
                date_to_client=date(2026, 1, 1),
                date_assigned_to_us=date(2026, 1, 5),
                assigned_attorney='John Smith',
                qcp_attorney='Jane Doe',
            )
            db.session.add(project)
            db.session.commit()

            assert project.project_group is None
            assert project.internal_deadline is None
            assert project.delivery_deadline is None
            assert project.notes is None
            assert project.deleted_at is None

    def test_soft_delete_sets_deleted_at(self, app):
        """Test that soft delete sets deleted_at timestamp."""
        with app.app_context():
            project = Project(
                project_name='Project to Delete',
                department='IT',
                date_to_client=date(2026, 1, 1),
                date_assigned_to_us=date(2026, 1, 5),
                assigned_attorney='John Smith',
                qcp_attorney='Jane Doe',
            )
            db.session.add(project)
            db.session.commit()

            assert project.deleted_at is None
            assert project.is_deleted is False

            # Soft delete by setting deleted_at
            project.deleted_at = datetime.utcnow()
            db.session.commit()

            assert project.deleted_at is not None
            assert project.is_deleted is True

    def test_project_repr(self, app):
        """Test the string representation of a project."""
        with app.app_context():
            project = Project(
                project_name='Repr Test Project',
                department='Finance',
                date_to_client=date(2026, 1, 1),
                date_assigned_to_us=date(2026, 1, 5),
                assigned_attorney='John Smith',
                qcp_attorney='Jane Doe',
            )
            db.session.add(project)
            db.session.commit()

            assert 'Repr Test Project' in repr(project)
            assert str(project.id) in repr(project)

    def test_to_dict(self, app, sample_project_data):
        """Test converting project to dictionary."""
        with app.app_context():
            project = Project(**sample_project_data)
            db.session.add(project)
            db.session.commit()

            result = project.to_dict()

            assert result['id'] == project.id
            assert result['project_name'] == sample_project_data['project_name']
            assert result['project_group'] == sample_project_data['project_group']
            assert result['department'] == sample_project_data['department']
            assert result['date_to_client'] == sample_project_data['date_to_client'].isoformat()
            assert result['date_assigned_to_us'] == sample_project_data['date_assigned_to_us'].isoformat()
            assert result['internal_deadline'] == sample_project_data['internal_deadline'].isoformat()
            assert result['delivery_deadline'] == sample_project_data['delivery_deadline'].isoformat()
            assert result['assigned_attorney'] == sample_project_data['assigned_attorney']
            assert result['qcp_attorney'] == sample_project_data['qcp_attorney']
            assert result['status'] == sample_project_data['status']
            assert result['notes'] == sample_project_data['notes']
            assert result['created_at'] is not None
            assert result['updated_at'] is not None
            assert result['deleted_at'] is None

    def test_to_dict_with_none_dates(self, app):
        """Test to_dict handles None date fields correctly."""
        with app.app_context():
            project = Project(
                project_name='Minimal Project',
                department='HR',
                date_to_client=date(2026, 1, 1),
                date_assigned_to_us=date(2026, 1, 5),
                assigned_attorney='John Smith',
                qcp_attorney='Jane Doe',
            )
            db.session.add(project)
            db.session.commit()

            result = project.to_dict()

            assert result['internal_deadline'] is None
            assert result['delivery_deadline'] is None
            assert result['deleted_at'] is None

    def test_all_status_values_can_be_set(self, app):
        """Test that all status values from the enum can be saved."""
        with app.app_context():
            for status in ProjectStatus.ALL:
                project = Project(
                    project_name=f'Project with status {status}',
                    department='Test',
                    date_to_client=date(2026, 1, 1),
                    date_assigned_to_us=date(2026, 1, 5),
                    assigned_attorney='John Smith',
                    qcp_attorney='Jane Doe',
                    status=status,
                )
                db.session.add(project)
                db.session.commit()

                # Fetch fresh from DB to verify
                fetched = db.session.get(Project, project.id)
                assert fetched.status == status


class TestProjectTableStructure:
    """Tests to verify the database table structure matches SPEC requirements."""

    def test_all_required_columns_exist(self, app):
        """Verify all columns from SPEC.md exist in the projects table."""
        with app.app_context():
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            columns = {col['name'] for col in inspector.get_columns('projects')}

            required_columns = {
                'id',
                'project_name',
                'project_group',
                'department',
                'date_to_client',
                'date_assigned_to_us',
                'assigned_attorney',
                'qcp_attorney',
                'internal_deadline',
                'delivery_deadline',
                'status',
                'notes',
                'created_at',
                'updated_at',
                'deleted_at',
            }

            assert required_columns.issubset(columns), \
                f"Missing columns: {required_columns - columns}"
