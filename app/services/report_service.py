"""Report service for generating reports and CSV exports.

This module provides the service layer for report generation including
weekly status data, monthly statistics, and CSV export functionality.
Routes call these functions; they interact with models and database.
"""
import csv
import io
from calendar import monthrange
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import func

from app import db
from app.models import Project, ProjectStatus
from app.services.project_service import get_all_projects


# Default fields for weekly status report if none specified
DEFAULT_WEEKLY_FIELDS = [
    'project_name',
    'department',
    'assigned_attorney',
    'status',
    'anticipated_completion',
]

# All available fields for weekly report (internal -> display name mapping)
WEEKLY_FIELD_OPTIONS = {
    'id': 'ID',
    'project_name': 'Project Name',
    'project_group': 'Project Group',
    'department': 'Department',
    'date_to_client': 'Date to Client',
    'date_assigned_to_us': 'Date Assigned',
    'assigned_attorney': 'Assigned Attorney',
    'qcp_attorney': 'QCP Attorney',
    'internal_deadline': 'Internal Deadline',
    'anticipated_completion': 'Anticipated Completion',
    'status': 'Status',
}

# CSV export column headers (order matters)
CSV_FIELDNAMES = [
    'ID',
    'Project Name',
    'Project Group',
    'Department',
    'Date to Client',
    'Date Assigned',
    'Assigned Attorney',
    'QCP Attorney',
    'Internal Deadline',
    'Delivery Deadline',
    'Status',
    'Notes',
]


def get_weekly_status_data(fields: list[str] = None) -> list[dict]:
    """Get active projects with only requested fields for weekly report.

    Returns non-completed, non-deleted projects sorted by delivery deadline.
    The field 'delivery_deadline' is renamed to 'anticipated_completion'
    in the output for client-facing reports (softer language).

    Args:
        fields: List of field names to include in output.
                If None, uses DEFAULT_WEEKLY_FIELDS.
                Use 'anticipated_completion' to get delivery_deadline values.

    Returns:
        List of dictionaries, each containing only the requested fields.
        Dates are formatted as ISO strings. Projects sorted by delivery
        deadline (nulls last).
    """
    if not fields:
        fields = DEFAULT_WEEKLY_FIELDS.copy()

    # Query active projects (not completed, not deleted)
    projects = (
        db.session.query(Project)
        .filter(Project.deleted_at.is_(None))
        .filter(Project.status != ProjectStatus.COMPLETED)
        .order_by(Project.delivery_deadline.asc().nulls_last())
        .all()
    )

    result = []
    for project in projects:
        row = {}
        for field in fields:
            if field == 'anticipated_completion':
                # Map to delivery_deadline
                value = project.delivery_deadline
                if value and hasattr(value, 'isoformat'):
                    value = value.isoformat()
                row['anticipated_completion'] = value
            elif hasattr(project, field):
                value = getattr(project, field)
                # Convert dates to ISO format strings
                if value and hasattr(value, 'isoformat'):
                    value = value.isoformat()
                row[field] = value
        result.append(row)

    return result


def get_monthly_stats(year: int, month: int) -> dict:
    """Get statistics for a specific month.

    Calculates various metrics for projects created or completed
    during the specified month.

    Args:
        year: The year (e.g., 2024).
        month: The month number (1-12).

    Returns:
        Dictionary with:
            - projects_opened: Count of projects created this month
            - projects_completed: Count of projects completed this month
              (status = Completed and updated_at within the month)
            - by_department: Dict of department name -> count (opened)
            - by_attorney: Dict of assigned attorney name -> count (opened)
            - avg_days_to_completion: Average days from date_assigned_to_us
              to updated_at for projects completed this month (float or None)

    Raises:
        ValueError: If month is not 1-12 or year is invalid.
    """
    if not 1 <= month <= 12:
        raise ValueError(f"Invalid month: {month}. Must be 1-12.")
    if year < 1900 or year > 2100:
        raise ValueError(f"Invalid year: {year}. Must be 1900-2100.")

    # Calculate date range for the month
    start_date = datetime(year, month, 1, 0, 0, 0, tzinfo=timezone.utc)
    _, last_day = monthrange(year, month)
    end_date = datetime(year, month, last_day, 23, 59, 59, tzinfo=timezone.utc)

    # Projects opened this month (by created_at)
    opened_query = (
        db.session.query(Project)
        .filter(Project.created_at >= start_date)
        .filter(Project.created_at <= end_date)
        .filter(Project.deleted_at.is_(None))
    )
    opened_projects = opened_query.all()
    projects_opened = len(opened_projects)

    # Projects completed this month (status = Completed AND updated_at in month)
    completed_query = (
        db.session.query(Project)
        .filter(Project.status == ProjectStatus.COMPLETED)
        .filter(Project.updated_at >= start_date)
        .filter(Project.updated_at <= end_date)
        .filter(Project.deleted_at.is_(None))
    )
    completed_projects = completed_query.all()
    projects_completed = len(completed_projects)

    # Breakdown by department (for opened projects)
    by_department = {}
    for project in opened_projects:
        dept = project.department
        by_department[dept] = by_department.get(dept, 0) + 1

    # Breakdown by assigned attorney (for opened projects)
    by_attorney = {}
    for project in opened_projects:
        attorney = project.assigned_attorney
        by_attorney[attorney] = by_attorney.get(attorney, 0) + 1

    # Average days to completion (for completed projects)
    avg_days_to_completion = None
    if completed_projects:
        total_days = 0
        valid_count = 0
        for project in completed_projects:
            if project.date_assigned_to_us and project.updated_at:
                # Convert date to datetime for calculation (timezone-naive)
                assigned_datetime = datetime.combine(
                    project.date_assigned_to_us,
                    datetime.min.time()
                )
                # updated_at may be timezone-aware or naive depending on DB
                # Make both naive for comparison
                updated_at = project.updated_at
                if updated_at.tzinfo is not None:
                    updated_at = updated_at.replace(tzinfo=None)
                days = (updated_at - assigned_datetime).days
                total_days += days
                valid_count += 1
        if valid_count > 0:
            avg_days_to_completion = round(total_days / valid_count, 1)

    return {
        'projects_opened': projects_opened,
        'projects_completed': projects_completed,
        'by_department': by_department,
        'by_attorney': by_attorney,
        'avg_days_to_completion': avg_days_to_completion,
        'year': year,
        'month': month,
    }


def export_projects_csv(filters: dict = None) -> str:
    """Export projects to CSV format.

    Uses the same filtering logic as get_all_projects.
    Notes are truncated to 200 characters.

    Args:
        filters: Optional dictionary with filter parameters.
                 Same filters as get_all_projects (status, department,
                 assigned_attorney, qcp_attorney, search, etc.)

    Returns:
        CSV-formatted string suitable for file download.
        Includes header row and all matching projects.
    """
    # Get projects using existing filtering logic
    projects = get_all_projects(filters)

    # Build CSV using StringIO
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=CSV_FIELDNAMES)
    writer.writeheader()

    for project in projects:
        # Truncate notes to 200 chars
        notes = project.notes or ''
        if len(notes) > 200:
            notes = notes[:197] + '...'

        row = {
            'ID': project.id,
            'Project Name': project.project_name,
            'Project Group': project.project_group or '',
            'Department': project.department,
            'Date to Client': _format_date(project.date_to_client),
            'Date Assigned': _format_date(project.date_assigned_to_us),
            'Assigned Attorney': project.assigned_attorney,
            'QCP Attorney': project.qcp_attorney,
            'Internal Deadline': _format_date(project.internal_deadline),
            'Delivery Deadline': _format_date(project.delivery_deadline),
            'Status': project.status,
            'Notes': notes,
        }
        writer.writerow(row)

    return output.getvalue()


def _format_date(d: Optional[date]) -> str:
    """Format a date for CSV output.

    Args:
        d: Date object or None.

    Returns:
        ISO format string or empty string if None.
    """
    if d is None:
        return ''
    return d.isoformat()


def get_available_weekly_fields() -> dict:
    """Get available fields for weekly status report configuration.

    Returns:
        Dictionary mapping internal field names to display names.
        Used to populate checkboxes in report builder UI.
    """
    return WEEKLY_FIELD_OPTIONS.copy()
