"""Dashboard routes for the Legal Project Tracker.

Provides the main dashboard view with projects organized by deadline urgency.
"""
from flask import Blueprint, jsonify

from app.services import project_service

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
def dashboard():
    """Get dashboard data with projects organized by deadline urgency.

    Returns JSON with four project lists:
    - overdue: Past delivery deadline
    - due_this_week: Delivery deadline within 7 days
    - longer_deadline: Delivery deadline beyond 7 days
    - recently_completed: Last 10 completed projects

    Returns:
        JSON object with project lists and counts.
    """
    overdue = project_service.get_overdue_projects()
    due_this_week = project_service.get_due_this_week()
    longer_deadline = project_service.get_longer_deadline()
    recently_completed = project_service.get_recently_completed()

    return jsonify({
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
    })
