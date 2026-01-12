"""Project routes for the Legal Project Tracker API.

This module provides RESTful API endpoints for project CRUD operations,
as well as HTML page routes for the web interface.
Routes call the service layer; they handle HTTP concerns only.
"""
from datetime import date, datetime

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for

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
    qcp_attorneys = project_service.get_distinct_values('qcp_attorney')

    return render_template(
        'projects.html',
        projects=projects,
        statuses=statuses,
        departments=departments,
        attorneys=attorneys,
        qcp_attorneys=qcp_attorneys,
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


# ============================================================================
# New Project Form Routes
# ============================================================================

@projects_bp.route('/projects/new')
def new_project_form():
    """Render the new project form HTML page.

    Query Parameters:
        clone_from: Optional project ID to pre-fill metadata from
        project_name: Optional pre-filled project name
        department: Optional pre-filled department
        assigned_attorney: Optional pre-filled assigned attorney
        qcp_attorney: Optional pre-filled QCP attorney
        project_group: Optional pre-filled project group

    Returns:
        HTML page with new project form.
    """
    # Check for clone parameters
    clone_from = request.args.get('clone_from')
    is_clone = clone_from is not None

    # Build prefill data from query params
    prefill = {
        'project_name': request.args.get('project_name', ''),
        'department': request.args.get('department', ''),
        'assigned_attorney': request.args.get('assigned_attorney', ''),
        'qcp_attorney': request.args.get('qcp_attorney', ''),
        'project_group': request.args.get('project_group', ''),
        'date_to_client': request.args.get('date_to_client', ''),
        'date_assigned_to_us': request.args.get('date_assigned_to_us', ''),
        'internal_deadline': request.args.get('internal_deadline', ''),
        'delivery_deadline': request.args.get('delivery_deadline', ''),
        'notes': request.args.get('notes', ''),
    }

    # Get distinct values for autocomplete
    departments = project_service.get_distinct_values('department')
    attorneys = project_service.get_distinct_values('assigned_attorney')
    qcp_attorneys = project_service.get_distinct_values('qcp_attorney')

    return render_template(
        'project_form.html',
        prefill=prefill,
        is_clone=is_clone,
        departments=departments,
        attorneys=attorneys,
        qcp_attorneys=qcp_attorneys,
        today=date.today().strftime('%Y-%m-%d')
    )


@projects_bp.route('/projects/create', methods=['POST'])
def create_project_form():
    """Handle new project form submission.

    Processes form data, creates the project, and redirects on success.
    On validation error, re-renders the form with error message and preserved data.

    Returns:
        Redirect to projects page on success, or re-render form with errors.
    """
    # Parse form data
    form_data = {
        'project_name': request.form.get('project_name', '').strip(),
        'project_group': request.form.get('project_group', '').strip() or None,
        'department': request.form.get('department', '').strip(),
        'assigned_attorney': request.form.get('assigned_attorney', '').strip(),
        'qcp_attorney': request.form.get('qcp_attorney', '').strip(),
        'status': request.form.get('status', 'In Progress').strip(),
    }

    # Parse date fields
    date_fields = ['date_to_client', 'date_assigned_to_us', 'internal_deadline', 'delivery_deadline']
    date_error = None
    for field in date_fields:
        date_str = request.form.get(field, '').strip()
        if date_str:
            parsed = _parse_date(date_str)
            if parsed:
                form_data[field] = parsed
            else:
                date_error = f'Invalid date format for {field.replace("_", " ").title()}'
                break
        else:
            form_data[field] = None

    # Handle initial notes
    notes = request.form.get('notes', '').strip()
    if notes:
        form_data['notes'] = notes

    # If date parse error, re-render form
    if date_error:
        prefill = {
            'project_name': request.form.get('project_name', ''),
            'project_group': request.form.get('project_group', ''),
            'department': request.form.get('department', ''),
            'assigned_attorney': request.form.get('assigned_attorney', ''),
            'qcp_attorney': request.form.get('qcp_attorney', ''),
            'date_to_client': request.form.get('date_to_client', ''),
            'date_assigned_to_us': request.form.get('date_assigned_to_us', ''),
            'internal_deadline': request.form.get('internal_deadline', ''),
            'delivery_deadline': request.form.get('delivery_deadline', ''),
            'notes': request.form.get('notes', ''),
        }
        departments = project_service.get_distinct_values('department')
        attorneys = project_service.get_distinct_values('assigned_attorney')
        qcp_attorneys = project_service.get_distinct_values('qcp_attorney')

        return render_template(
            'project_form.html',
            prefill=prefill,
            is_clone=False,
            departments=departments,
            attorneys=attorneys,
            qcp_attorneys=qcp_attorneys,
            today=date.today().strftime('%Y-%m-%d'),
            error=date_error
        )

    try:
        # Create the project
        project = project_service.create_project(form_data)
        flash(f'Project "{project.project_name}" created successfully', 'success')
        return redirect(url_for('projects.projects_page'))

    except ValueError as e:
        # Validation error - re-render form with error
        prefill = {
            'project_name': request.form.get('project_name', ''),
            'project_group': request.form.get('project_group', ''),
            'department': request.form.get('department', ''),
            'assigned_attorney': request.form.get('assigned_attorney', ''),
            'qcp_attorney': request.form.get('qcp_attorney', ''),
            'date_to_client': request.form.get('date_to_client', ''),
            'date_assigned_to_us': request.form.get('date_assigned_to_us', ''),
            'internal_deadline': request.form.get('internal_deadline', ''),
            'delivery_deadline': request.form.get('delivery_deadline', ''),
            'notes': request.form.get('notes', ''),
        }
        departments = project_service.get_distinct_values('department')
        attorneys = project_service.get_distinct_values('assigned_attorney')
        qcp_attorneys = project_service.get_distinct_values('qcp_attorney')

        return render_template(
            'project_form.html',
            prefill=prefill,
            is_clone=False,
            departments=departments,
            attorneys=attorneys,
            qcp_attorneys=qcp_attorneys,
            today=date.today().strftime('%Y-%m-%d'),
            error=str(e)
        )


# ============================================================================
# Project Detail & Edit HTML Routes
# ============================================================================

@projects_bp.route('/projects/<int:id>/view')
def view_project(id: int):
    """Render the project detail HTML page.

    Args:
        id: Project ID.

    Returns:
        HTML page with project details, or redirect to projects page if not found.
    """
    project = project_service.get_project(id)
    if not project:
        flash('Project not found', 'danger')
        return redirect(url_for('projects.projects_page'))

    return render_template(
        'project_detail.html',
        project=project,
        today=date.today()
    )


@projects_bp.route('/projects/<int:id>/edit')
def edit_project_form(id: int):
    """Render the project edit form HTML page.

    Args:
        id: Project ID.

    Returns:
        HTML page with edit form, or redirect to projects page if not found.
    """
    project = project_service.get_project(id)
    if not project:
        flash('Project not found', 'danger')
        return redirect(url_for('projects.projects_page'))

    # Get autocomplete values for dropdowns
    statuses = ProjectStatus.ALL
    departments = project_service.get_distinct_values('department')
    attorneys = project_service.get_distinct_values('assigned_attorney')
    qcp_attorneys = project_service.get_distinct_values('qcp_attorney')

    return render_template(
        'project_edit.html',
        project=project,
        statuses=statuses,
        departments=departments,
        attorneys=attorneys,
        qcp_attorneys=qcp_attorneys
    )


@projects_bp.route('/projects/<int:id>/update', methods=['POST'])
def update_project_form(id: int):
    """Handle project edit form submission.

    Processes form data, updates the project, and handles new notes.
    Redirects back to detail page on success.

    Args:
        id: Project ID.

    Returns:
        Redirect to detail page on success, or re-render form with errors.
    """
    project = project_service.get_project(id)
    if not project:
        flash('Project not found', 'danger')
        return redirect(url_for('projects.projects_page'))

    # Parse form data
    form_data = {
        'project_name': request.form.get('project_name', '').strip(),
        'project_group': request.form.get('project_group', '').strip() or None,
        'department': request.form.get('department', '').strip(),
        'assigned_attorney': request.form.get('assigned_attorney', '').strip(),
        'qcp_attorney': request.form.get('qcp_attorney', '').strip(),
        'status': request.form.get('status', '').strip(),
    }

    # Parse date fields
    date_fields = ['date_to_client', 'date_assigned_to_us', 'internal_deadline', 'delivery_deadline']
    for field in date_fields:
        date_str = request.form.get(field, '').strip()
        if date_str:
            parsed = _parse_date(date_str)
            if parsed:
                form_data[field] = parsed
            else:
                flash(f'Invalid date format for {field.replace("_", " ")}', 'danger')
                return redirect(url_for('projects.edit_project_form', id=id))
        else:
            form_data[field] = None

    try:
        # Update the project
        updated_project = project_service.update_project(id, form_data)
        if not updated_project:
            flash('Project not found', 'danger')
            return redirect(url_for('projects.projects_page'))

        # Handle new note if provided
        new_note = request.form.get('new_note', '').strip()
        if new_note:
            project_service.append_note(id, new_note)

        flash('Project updated successfully', 'success')
        return redirect(url_for('projects.view_project', id=id))

    except ValueError as e:
        flash(str(e), 'danger')
        return redirect(url_for('projects.edit_project_form', id=id))


@projects_bp.route('/projects/<int:id>/clone')
def clone_project(id: int):
    """Clone a project by redirecting to new project form with pre-filled data.

    Pre-fills metadata (attorneys, department, project group) but leaves dates empty.

    Args:
        id: Project ID to clone from.

    Returns:
        Redirect to new project form with query params, or projects page if not found.
    """
    project = project_service.get_project(id)
    if not project:
        flash('Project not found', 'danger')
        return redirect(url_for('projects.projects_page'))

    # Redirect to new project form with pre-filled data
    return redirect(url_for(
        'projects.new_project_form',
        clone_from=id,
        project_name=f'Copy of {project.project_name}',
        department=project.department,
        assigned_attorney=project.assigned_attorney,
        qcp_attorney=project.qcp_attorney,
        project_group=project.project_group or ''
    ))


@projects_bp.route('/projects/<int:id>/delete', methods=['POST'])
def delete_project_form(id: int):
    """Handle project delete form submission.

    Soft-deletes the project and redirects to the projects list.

    Args:
        id: Project ID.

    Returns:
        Redirect to projects page with success/error message.
    """
    success = project_service.delete_project(id)
    if not success:
        flash('Project not found', 'danger')
    else:
        flash('Project deleted successfully', 'success')

    return redirect(url_for('projects.projects_page'))
