"""Dashboard routes for the Legal Project Tracker.

Provides the main dashboard view with projects organized by deadline urgency.
"""
from flask import Blueprint, jsonify, render_template

from app.services import project_service

dashboard_bp = Blueprint('dashboard', __name__)


def _get_dashboard_data() -> dict:
    """Fetch and structure dashboard data.

    Retrieves projects organized by deadline urgency from the service layer.

    Returns:
        Dictionary with four project sections, each containing 'data' and 'count'.
    """
    overdue = project_service.get_overdue_projects()
    due_this_week = project_service.get_due_this_week()
    longer_deadline = project_service.get_longer_deadline()
    recently_completed = project_service.get_recently_completed()

    return {
        'overdue': {
            'data': [p.to_dict() for p in overdue],
            'count': len(overdue)
        },
        'due_this_week': {
            'data': [p.to_dict() for p in due_this_week],
            'count': len(due_this_week)
        },
        'longer_deadline': {
            'data': [p.to_dict() for p in longer_deadline],
            'count': len(longer_deadline)
        },
        'recently_completed': {
            'data': [p.to_dict() for p in recently_completed],
            'count': len(recently_completed)
        }
    }


@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
def dashboard():
    """Render dashboard page with projects organized by deadline urgency.

    Displays four sections:
    - Overdue: Past delivery deadline (red/danger styling)
    - Due This Week: Delivery deadline within 7 days (amber/warning styling)
    - Longer Deadline: Delivery deadline beyond 7 days (neutral styling)
    - Recently Completed: Last 10 completed projects (green/success styling)

    Returns:
        Rendered HTML template with project data.
    """
    data = _get_dashboard_data()
    return render_template('dashboard.html', **data)


@dashboard_bp.route('/api/dashboard')
def dashboard_api():
    """API endpoint for dashboard data (JSON).

    Provides dashboard data as JSON for API consumers and testing.
    This endpoint will remain as JSON even after Sprint 3.2 converts
    the main dashboard routes to return HTML templates.

    Returns:
        JSON object with project lists and counts.
    """
    return jsonify(_get_dashboard_data())
