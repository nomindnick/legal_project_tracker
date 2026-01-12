"""Project routes for the Legal Project Tracker API.

This module provides RESTful API endpoints for project CRUD operations.
Routes call the service layer; they handle HTTP concerns only.
"""
from datetime import datetime

from flask import Blueprint, jsonify, render_template, request

from app.models import ProjectStatus
from app.services import project_service

projects_bp = Blueprint('projects', __name__)


def _parse_date(date_str: str):
    """Parse a date string in YYYY-MM-DD format.

    Args:
        date_str: Date string to parse.

    Returns:
        date object if valid, None otherwise.
    """
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return None


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

    Handles all supported filter and sort parameters.

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
        # Exclude Completed status by default
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

    # Search term (multi-field, multi-term search)
    if request.args.get('search'):
        filters['search'] = request.args.get('search')

    # Date range filters
    delivery_from = _parse_date(request.args.get('delivery_deadline_from'))
    if delivery_from:
        filters['delivery_deadline_from'] = delivery_from
    delivery_to = _parse_date(request.args.get('delivery_deadline_to'))
    if delivery_to:
        filters['delivery_deadline_to'] = delivery_to

    date_assigned_from = _parse_date(request.args.get('date_assigned_from'))
    if date_assigned_from:
        filters['date_assigned_from'] = date_assigned_from
    date_assigned_to = _parse_date(request.args.get('date_assigned_to'))
    if date_assigned_to:
        filters['date_assigned_to'] = date_assigned_to

    # Include deleted
    filters['include_deleted'] = _parse_bool(
        request.args.get('include_deleted'), False
    )

    # Sorting
    if request.args.get('sort_by'):
        filters['sort_by'] = request.args.get('sort_by')
    if request.args.get('sort_dir'):
        filters['sort_dir'] = request.args.get('sort_dir')

    return filters


def _parse_project_data(data: dict) -> dict:
    """Parse and prepare project data from request JSON.

    Converts date strings to date objects.

    Args:
        data: Raw request JSON data.

    Returns:
        Prepared data dict for service layer.
    """
    result = {}

    # Text fields
    text_fields = [
        'project_name', 'project_group', 'department',
        'assigned_attorney', 'qcp_attorney', 'status', 'notes'
    ]
    for field in text_fields:
        if field in data:
            result[field] = data[field]

    # Date fields
    date_fields = [
        'date_to_client', 'date_assigned_to_us',
        'internal_deadline', 'delivery_deadline'
    ]
    for field in date_fields:
        if field in data:
            if data[field]:
                parsed = _parse_date(data[field])
                if parsed:
                    result[field] = parsed
                else:
                    result[field] = data[field]  # Let service handle invalid
            else:
                result[field] = None

    return result


# ============================================================================
# Project CRUD Routes
# ============================================================================

@projects_bp.route('/projects', methods=['GET'])
def get_projects():
    """Get all projects with optional filtering and sorting.

    Query Parameters:
        status: Filter by status (comma-separated for multiple)
        department: Filter by department
        assigned_attorney: Filter by assigned attorney
        qcp_attorney: Filter by QCP attorney
        search: Multi-term search across project_name, department,
                notes, project_group (case-insensitive)
        include_completed: Include completed projects (default: false)
        include_deleted: Include soft-deleted projects (default: false)
        delivery_deadline_from: Minimum delivery deadline (YYYY-MM-DD)
        delivery_deadline_to: Maximum delivery deadline (YYYY-MM-DD)
        date_assigned_from: Minimum assignment date (YYYY-MM-DD)
        date_assigned_to: Maximum assignment date (YYYY-MM-DD)
        sort_by: Field to sort by (default: delivery_deadline)
        sort_dir: Sort direction, 'asc' or 'desc' (default: asc)

    Returns:
        JSON array of projects with count.
    """
    filters = _build_filters_from_request()
    projects = project_service.get_all_projects(filters)
    return jsonify({
        'data': [p.to_dict() for p in projects],
        'count': len(projects)
    })


@projects_bp.route('/projects/<int:id>', methods=['GET'])
def get_project(id: int):
    """Get a single project by ID.

    Args:
        id: Project ID.

    Returns:
        JSON object with project data, or 404 if not found.
    """
    project = project_service.get_project(id)
    if not project:
        return jsonify({'error': 'Project not found'}), 404
    return jsonify({'data': project.to_dict()})


@projects_bp.route('/projects', methods=['POST'])
def create_project():
    """Create a new project.

    Request Body (JSON):
        Required: project_name, department, date_to_client,
                  date_assigned_to_us, assigned_attorney, qcp_attorney
        Optional: project_group, internal_deadline, delivery_deadline,
                  status (defaults to In Progress), notes

    Returns:
        201 with created project data, or 400 on validation error.
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body must be JSON'}), 400

    parsed_data = _parse_project_data(data)

    try:
        project = project_service.create_project(parsed_data)
        return jsonify({'data': project.to_dict()}), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@projects_bp.route('/projects/<int:id>', methods=['PUT'])
def update_project(id: int):
    """Update an existing project.

    Args:
        id: Project ID.

    Request Body (JSON):
        Any project fields to update.

    Returns:
        200 with updated project data, 404 if not found, or 400 on error.
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body must be JSON'}), 400

    parsed_data = _parse_project_data(data)

    try:
        project = project_service.update_project(id, parsed_data)
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        return jsonify({'data': project.to_dict()})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@projects_bp.route('/projects/<int:id>', methods=['DELETE'])
def delete_project(id: int):
    """Soft delete a project.

    Sets deleted_at timestamp but keeps project in database.
    Critical for legal context where you may need to prove a project existed.

    Args:
        id: Project ID.

    Returns:
        200 with success message, or 404 if not found.
    """
    success = project_service.delete_project(id)
    if not success:
        return jsonify({'error': 'Project not found'}), 404
    return jsonify({'message': 'Project deleted successfully'})


# ============================================================================
# Notes Route
# ============================================================================

@projects_bp.route('/projects/<int:id>/notes', methods=['POST'])
def append_note(id: int):
    """Append a timestamped note to a project.

    Notes are append-only with format: [YYYY-MM-DD HH:MM]: note content

    Args:
        id: Project ID.

    Request Body (JSON):
        note: The note content to append.

    Returns:
        200 with updated project data, or 404 if not found.
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body must be JSON'}), 400

    note = data.get('note', '')
    project = project_service.append_note(id, note)

    if not project:
        return jsonify({'error': 'Project not found'}), 404

    return jsonify({'data': project.to_dict()})


# ============================================================================
# Autocomplete Route
# ============================================================================

@projects_bp.route('/api/autocomplete/<field>', methods=['GET'])
def autocomplete(field: str):
    """Get distinct values for a field for autocomplete functionality.

    Args:
        field: Field name (department, assigned_attorney, qcp_attorney,
               status, project_group).

    Returns:
        JSON array of distinct values, or 400 if field is invalid.
    """
    try:
        values = project_service.get_distinct_values(field)
        return jsonify({'data': values})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


# ============================================================================
# HTML Page Routes (for HTMX)
# ============================================================================

@projects_bp.route('/projects/page')
def projects_page():
    """Render the full projects HTML page.

    Supports all query parameters from GET /projects.
    Provides data for filter dropdowns from autocomplete values.

    Returns:
        HTML page with projects table and filter controls.
    """
    filters = _build_filters_from_request()
    projects = project_service.get_all_projects(filters)

    # Get distinct values for filter dropdowns
    statuses = [s for s in ProjectStatus.ALL]
    departments = project_service.get_distinct_values('department')
    attorneys = project_service.get_distinct_values('assigned_attorney')

    return render_template(
        'projects.html',
        projects=projects,
        statuses=statuses,
        departments=departments,
        attorneys=attorneys,
        filters=request.args
    )


@projects_bp.route('/projects/table_rows')
def projects_table_rows():
    """Return just the table body HTML for HTMX updates.

    Supports all query parameters from GET /projects.
    Returns a partial HTML fragment for HTMX to swap into the table body.

    Returns:
        HTML fragment containing table rows.
    """
    filters = _build_filters_from_request()
    projects = project_service.get_all_projects(filters)

    return render_template(
        'partials/project_table_rows.html',
        projects=projects
    )
