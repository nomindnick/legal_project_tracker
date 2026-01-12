"""Report routes for the Legal Project Tracker.

This module provides routes for generating reports and exporting data.
Routes call the service layer; they handle HTTP concerns only.
"""
from datetime import datetime

from flask import Blueprint, Response, render_template, request

from app.models import ProjectStatus
from app.services import report_service

reports_bp = Blueprint('reports', __name__)


def _parse_int(value: str, default: int) -> int:
    """Parse an integer from a string value.

    Args:
        value: String value to parse.
        default: Default value if parsing fails.

    Returns:
        Integer value.
    """
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _parse_bool(value: str, default: bool = False) -> bool:
    """Parse a boolean query parameter.

    Args:
        value: String value to parse.
        default: Default value if parsing fails.

    Returns:
        Boolean value.
    """
    if value is None:
        return default
    return value.lower() in ('true', '1', 'yes')


def _build_filters_from_request() -> dict:
    """Build a filters dict from request query parameters.

    Handles all supported filter parameters for CSV export.

    Returns:
        Dictionary of filter parameters for the service layer.
    """
    filters = {}

    # Status filter - can be comma-separated
    status = request.args.get('status')
    if status:
        status_list = [s.strip() for s in status.split(',') if s.strip()]
        if status_list:
            filters['status'] = status_list

    # include_completed logic: if false (default), exclude Completed status
    # unless status filter is explicitly provided
    include_completed = _parse_bool(request.args.get('include_completed'), False)
    if not include_completed and 'status' not in filters:
        filters['status'] = [
            s for s in ProjectStatus.ALL if s != ProjectStatus.COMPLETED
        ]

    # Other text filters
    if request.args.get('department'):
        filters['department'] = request.args.get('department')
    if request.args.get('assigned_attorney'):
        filters['assigned_attorney'] = request.args.get('assigned_attorney')
    if request.args.get('qcp_attorney'):
        filters['qcp_attorney'] = request.args.get('qcp_attorney')

    # Search term
    if request.args.get('search'):
        filters['search'] = request.args.get('search')

    # Sorting
    if request.args.get('sort_by'):
        filters['sort_by'] = request.args.get('sort_by')
    if request.args.get('sort_dir'):
        filters['sort_dir'] = request.args.get('sort_dir')

    return filters


@reports_bp.route('/reports')
def reports_page():
    """Render the report builder page.

    Provides UI for selecting report type and options.
    """
    # Get available fields for weekly report configuration
    available_fields = report_service.get_available_weekly_fields()

    # Get current date for monthly stats defaults
    now = datetime.now()
    current_year = now.year
    current_month = now.month

    return render_template(
        'reports/report_builder.html',
        available_fields=available_fields,
        current_year=current_year,
        current_month=current_month,
    )


@reports_bp.route('/reports/weekly')
def weekly_report():
    """Generate the weekly status report.

    Query params:
        fields: Comma-separated list of field names to include.
                If not provided, uses default fields.

    Returns:
        HTML page showing weekly status of active projects.
    """
    # Parse requested fields from query params
    fields_param = request.args.get('fields', '')
    if fields_param:
        fields = [f.strip() for f in fields_param.split(',') if f.strip()]
    else:
        fields = None  # Use defaults

    # Get the weekly status data
    projects = report_service.get_weekly_status_data(fields)

    # Get field display names for headers
    available_fields = report_service.get_available_weekly_fields()

    # Determine which fields are being shown
    if fields:
        shown_fields = fields
    else:
        shown_fields = report_service.DEFAULT_WEEKLY_FIELDS

    return render_template(
        'reports/weekly_status.html',
        projects=projects,
        shown_fields=shown_fields,
        field_names=available_fields,
        generated_at=datetime.now(),
    )


@reports_bp.route('/reports/monthly')
def monthly_report():
    """Generate the monthly statistics report.

    Query params:
        year: Year to report on (default: current year)
        month: Month to report on, 1-12 (default: current month)

    Returns:
        HTML page showing monthly statistics.
    """
    now = datetime.now()

    year = _parse_int(request.args.get('year'), now.year)
    month = _parse_int(request.args.get('month'), now.month)

    # Validate month range
    if month < 1:
        month = 1
    elif month > 12:
        month = 12

    # Get monthly statistics
    stats = report_service.get_monthly_stats(year, month)

    # Get month name for display
    from calendar import month_name
    month_display = month_name[month]

    return render_template(
        'reports/monthly_stats.html',
        stats=stats,
        month_name=month_display,
        generated_at=datetime.now(),
    )


@reports_bp.route('/projects/export')
def export_csv():
    """Export projects to CSV file.

    Accepts the same filter query parameters as the projects list.

    Returns:
        CSV file download of projects matching the filters.
    """
    filters = _build_filters_from_request()

    # Generate CSV content
    csv_content = report_service.export_projects_csv(filters)

    # Create response with appropriate headers for CSV download
    response = Response(
        csv_content,
        mimetype='text/csv; charset=utf-8',
    )
    response.headers['Content-Disposition'] = 'attachment; filename=projects_export.csv'

    return response
