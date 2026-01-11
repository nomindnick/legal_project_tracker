"""Pytest fixtures for the Legal Project Tracker tests.

This module provides fixtures for setting up test database and application
context. Uses an in-memory SQLite database to ensure test isolation and
avoid affecting development data.
"""
import pytest
from datetime import date, datetime

from app import create_app, db
from app.config import Config
from app.models import Project, ProjectStatus


class TestConfig(Config):
    """Test configuration using in-memory SQLite database.

    This ensures tests are isolated from development data and run quickly.
    """
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    SECRET_KEY = 'test-secret-key'


@pytest.fixture(scope='function')
def app():
    """Create and configure a test application instance.

    Uses an in-memory SQLite database to ensure each test starts with
    a clean database. Tables are created fresh for each test function.

    Yields:
        Flask application configured for testing.
    """
    app = create_app(TestConfig)

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope='function')
def client(app):
    """Create a test client for the application.

    Args:
        app: Flask application fixture.

    Returns:
        Flask test client for making HTTP requests.
    """
    return app.test_client()


@pytest.fixture(scope='function')
def db_session(app):
    """Provide a database session for tests.

    Args:
        app: Flask application fixture.

    Yields:
        SQLAlchemy database session.
    """
    with app.app_context():
        yield db.session


@pytest.fixture
def sample_project_data():
    """Provide sample data for creating a project.

    Returns:
        Dictionary with valid project data.
    """
    return {
        'project_name': 'Test Project',
        'project_group': 'Test Group',
        'department': 'Public Works',
        'date_to_client': date(2026, 1, 1),
        'date_assigned_to_us': date(2026, 1, 5),
        'assigned_attorney': 'John Smith',
        'qcp_attorney': 'Jane Doe',
        'internal_deadline': date(2026, 1, 20),
        'delivery_deadline': date(2026, 1, 25),
        'status': ProjectStatus.IN_PROGRESS,
        'notes': '[2026-01-05 09:00]: Initial assignment received.',
    }


@pytest.fixture
def sample_project(app, sample_project_data):
    """Create and return a sample project in the database.

    Args:
        app: Flask application fixture.
        sample_project_data: Sample project data fixture.

    Returns:
        Project instance saved to the database.
    """
    with app.app_context():
        project = Project(**sample_project_data)
        db.session.add(project)
        db.session.commit()
        # Refresh to get the ID and return a detached object
        project_id = project.id
        db.session.expunge(project)
        return project
