"""Business logic services package.

This package contains service modules that implement business logic.
Routes call services; services interact with models.
This separation keeps routes thin and logic testable.
"""
from app.services.project_service import (
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
from app.services.report_service import (
    get_weekly_status_data,
    get_monthly_stats,
    export_projects_csv,
    get_available_weekly_fields,
)

__all__ = [
    # Project service
    'create_project',
    'get_project',
    'get_all_projects',
    'update_project',
    'delete_project',
    'append_note',
    'get_distinct_values',
    'get_overdue_projects',
    'get_due_this_week',
    'get_longer_deadline',
    'get_recently_completed',
    # Report service
    'get_weekly_status_data',
    'get_monthly_stats',
    'export_projects_csv',
    'get_available_weekly_fields',
]
