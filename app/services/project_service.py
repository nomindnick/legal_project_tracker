"""Project service for business logic operations.

This module provides the service layer for project CRUD operations,
implementing soft delete, soft normalization, filtering, and sorting.
Routes call these functions; they interact with models and database.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func

from app import db
from app.models import Project, ProjectStatus


# Fields that should be soft-normalized (case-matched to existing values)
NORMALIZED_FIELDS = ['department', 'assigned_attorney', 'qcp_attorney']


def get_distinct_values(field: str) -> list[str]:
    """Get distinct values for a field from non-deleted projects.

    Used for autocomplete functionality and soft normalization.

    Args:
        field: Field name to get distinct values for.
               Valid fields: department, assigned_attorney, qcp_attorney, status

    Returns:
        List of unique values for the field, sorted alphabetically.

    Raises:
        ValueError: If field is not a valid column name.
    """
    valid_fields = ['department', 'assigned_attorney', 'qcp_attorney', 'status', 'project_group']
    if field not in valid_fields:
        raise ValueError(f"Invalid field: {field}. Must be one of: {valid_fields}")

    column = getattr(Project, field)
    results = (
        db.session.query(column)
        .filter(Project.deleted_at.is_(None))
        .filter(column.isnot(None))
        .filter(column != '')
        .distinct()
        .order_by(column)
        .all()
    )
    return [r[0] for r in results]


def _normalize_field(field_name: str, value: Optional[str]) -> Optional[str]:
    """Normalize a field value to match existing canonical values.

    Performs case-insensitive matching against existing values.
    If a match is found, returns the canonical (existing) version.
    Otherwise returns the value as-is (it becomes the new canonical).

    Args:
        field_name: The field being normalized.
        value: The value to normalize.

    Returns:
        The normalized value.
    """
    if not value:
        return value

    try:
        existing = get_distinct_values(field_name)
    except ValueError:
        return value

    for canonical in existing:
        if canonical.lower() == value.lower():
            return canonical
    return value


def _apply_normalization(data: dict) -> dict:
    """Apply soft normalization to applicable fields in data dict.

    Args:
        data: Dictionary of project field values.

    Returns:
        New dictionary with normalized values for applicable fields.
    """
    result = data.copy()
    for field in NORMALIZED_FIELDS:
        if field in result and result[field]:
            result[field] = _normalize_field(field, result[field])
    return result


def create_project(data: dict) -> Project:
    """Create a new project.

    Applies soft normalization to department and attorney fields.

    Args:
        data: Dictionary containing project field values.
              Required: project_name, department, date_to_client,
                       date_assigned_to_us, assigned_attorney, qcp_attorney
              Optional: project_group, internal_deadline, delivery_deadline,
                       status (defaults to In Progress), notes

    Returns:
        The created Project instance with ID populated.

    Raises:
        ValueError: If required fields are missing.
    """
    required_fields = [
        'project_name', 'department', 'date_to_client',
        'date_assigned_to_us', 'assigned_attorney', 'qcp_attorney'
    ]
    missing = [f for f in required_fields if f not in data or not data[f]]
    if missing:
        raise ValueError(f"Missing required fields: {missing}")

    # Apply soft normalization
    normalized_data = _apply_normalization(data)

    # Set default status if not provided
    if 'status' not in normalized_data or not normalized_data['status']:
        normalized_data['status'] = ProjectStatus.IN_PROGRESS
    elif normalized_data['status'] not in ProjectStatus.ALL:
        raise ValueError(
            f"Invalid status: {normalized_data['status']}. "
            f"Must be one of: {ProjectStatus.ALL}"
        )

    project = Project(**normalized_data)
    db.session.add(project)
    db.session.commit()
    return project


def get_project(id: int) -> Optional[Project]:
    """Get a project by ID, excluding soft-deleted projects.

    Args:
        id: The project ID to retrieve.

    Returns:
        The Project instance if found and not deleted, None otherwise.
    """
    project = db.session.get(Project, id)
    if project and project.deleted_at is None:
        return project
    return None


def get_all_projects(filters: dict = None) -> list[Project]:
    """Get all projects with optional filtering and sorting.

    By default excludes soft-deleted projects and includes all statuses.

    Args:
        filters: Optional dictionary with filter/sort parameters:
            - status: Single status string or list of statuses
            - department: Department name (case-insensitive)
            - assigned_attorney: Attorney name (case-insensitive)
            - qcp_attorney: QCP attorney name (case-insensitive)
            - include_deleted: If True, includes soft-deleted projects
            - delivery_deadline_from: Minimum delivery deadline (date)
            - delivery_deadline_to: Maximum delivery deadline (date)
            - date_assigned_from: Minimum date assigned (date)
            - date_assigned_to: Maximum date assigned (date)
            - sort_by: Field name to sort by (default: delivery_deadline)
            - sort_dir: 'asc' or 'desc' (default: asc)

    Returns:
        List of Project instances matching the filters.
    """
    filters = filters or {}

    query = db.session.query(Project)

    # Soft delete filter (default: exclude deleted)
    if not filters.get('include_deleted', False):
        query = query.filter(Project.deleted_at.is_(None))

    # Status filter
    if 'status' in filters and filters['status']:
        status_values = filters['status']
        if isinstance(status_values, str):
            status_values = [status_values]
        query = query.filter(Project.status.in_(status_values))

    # Department filter (case-insensitive)
    if 'department' in filters and filters['department']:
        query = query.filter(
            func.lower(Project.department) == func.lower(filters['department'])
        )

    # Assigned attorney filter (case-insensitive)
    if 'assigned_attorney' in filters and filters['assigned_attorney']:
        query = query.filter(
            func.lower(Project.assigned_attorney) == func.lower(filters['assigned_attorney'])
        )

    # QCP attorney filter (case-insensitive)
    if 'qcp_attorney' in filters and filters['qcp_attorney']:
        query = query.filter(
            func.lower(Project.qcp_attorney) == func.lower(filters['qcp_attorney'])
        )

    # Delivery deadline range
    if 'delivery_deadline_from' in filters and filters['delivery_deadline_from']:
        query = query.filter(
            Project.delivery_deadline >= filters['delivery_deadline_from']
        )
    if 'delivery_deadline_to' in filters and filters['delivery_deadline_to']:
        query = query.filter(
            Project.delivery_deadline <= filters['delivery_deadline_to']
        )

    # Date assigned range
    if 'date_assigned_from' in filters and filters['date_assigned_from']:
        query = query.filter(
            Project.date_assigned_to_us >= filters['date_assigned_from']
        )
    if 'date_assigned_to' in filters and filters['date_assigned_to']:
        query = query.filter(
            Project.date_assigned_to_us <= filters['date_assigned_to']
        )

    # Sorting
    sort_by = filters.get('sort_by', 'delivery_deadline')
    sort_dir = filters.get('sort_dir', 'asc')

    # Validate sort_by is a valid column
    if hasattr(Project, sort_by):
        sort_column = getattr(Project, sort_by)
        if sort_dir.lower() == 'desc':
            query = query.order_by(sort_column.desc().nulls_last())
        else:
            query = query.order_by(sort_column.asc().nulls_last())
    else:
        # Default to delivery_deadline if invalid sort_by
        if sort_dir.lower() == 'desc':
            query = query.order_by(Project.delivery_deadline.desc().nulls_last())
        else:
            query = query.order_by(Project.delivery_deadline.asc().nulls_last())

    return query.all()


def update_project(id: int, data: dict) -> Optional[Project]:
    """Update an existing project.

    Applies soft normalization to department and attorney fields.
    Cannot update soft-deleted projects.

    Args:
        id: The project ID to update.
        data: Dictionary of fields to update.

    Returns:
        The updated Project instance, or None if not found/deleted.
    """
    project = get_project(id)
    if not project:
        return None

    # Validate status if provided
    if 'status' in data and data['status'] and data['status'] not in ProjectStatus.ALL:
        raise ValueError(
            f"Invalid status: {data['status']}. "
            f"Must be one of: {ProjectStatus.ALL}"
        )

    # Apply soft normalization to the update data
    normalized_data = _apply_normalization(data)

    # Update only provided fields
    for key, value in normalized_data.items():
        if hasattr(project, key) and key not in ['id', 'created_at', 'deleted_at']:
            setattr(project, key, value)

    db.session.commit()
    return project


def delete_project(id: int) -> bool:
    """Soft delete a project by setting deleted_at timestamp.

    Does not actually remove the project from the database.
    Critical for legal context where you may need to prove a project existed.

    Args:
        id: The project ID to delete.

    Returns:
        True if project was deleted, False if not found or already deleted.
    """
    # Get the project directly without the soft-delete filter
    project = db.session.get(Project, id)
    if not project or project.deleted_at is not None:
        return False

    project.deleted_at = datetime.now(timezone.utc)
    db.session.commit()
    return True


def append_note(id: int, note: str) -> Optional[Project]:
    """Append a timestamped note to a project.

    Notes are append-only with format: [YYYY-MM-DD HH:MM]: note content

    Args:
        id: The project ID to add note to.
        note: The note content to append.

    Returns:
        The updated Project instance, or None if not found/deleted.
    """
    project = get_project(id)
    if not project:
        return None

    if not note or not note.strip():
        return project

    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')
    formatted_note = f"[{timestamp}]: {note.strip()}"

    if project.notes:
        project.notes = f"{project.notes}\n{formatted_note}"
    else:
        project.notes = formatted_note

    db.session.commit()
    return project


# ============================================================================
# Dashboard Functions
# ============================================================================

def get_overdue_projects() -> list[Project]:
    """Get projects past their delivery deadline.

    Returns projects where:
    - delivery_deadline < today
    - status != Completed
    - Not soft-deleted

    Projects are ordered by delivery_deadline ascending (most overdue first).

    Returns:
        List of overdue Project instances.
    """
    today = datetime.now(timezone.utc).date()

    return (
        db.session.query(Project)
        .filter(Project.deleted_at.is_(None))
        .filter(Project.delivery_deadline.isnot(None))
        .filter(Project.delivery_deadline < today)
        .filter(Project.status != ProjectStatus.COMPLETED)
        .order_by(Project.delivery_deadline.asc())
        .all()
    )


def get_due_this_week() -> list[Project]:
    """Get projects due within the next 7 days.

    Returns projects where:
    - today <= delivery_deadline <= today + 7 days
    - status != Completed
    - Not soft-deleted

    Projects are ordered by delivery_deadline ascending.

    Returns:
        List of Project instances due this week.
    """
    today = datetime.now(timezone.utc).date()
    week_from_now = today + timedelta(days=7)

    return (
        db.session.query(Project)
        .filter(Project.deleted_at.is_(None))
        .filter(Project.delivery_deadline.isnot(None))
        .filter(Project.delivery_deadline >= today)
        .filter(Project.delivery_deadline <= week_from_now)
        .filter(Project.status != ProjectStatus.COMPLETED)
        .order_by(Project.delivery_deadline.asc())
        .all()
    )


def get_longer_deadline() -> list[Project]:
    """Get projects with deadlines beyond 7 days.

    Returns projects where:
    - delivery_deadline > today + 7 days
    - status != Completed
    - Not soft-deleted

    Projects are ordered by delivery_deadline ascending.

    Returns:
        List of Project instances with longer deadlines.
    """
    today = datetime.now(timezone.utc).date()
    week_from_now = today + timedelta(days=7)

    return (
        db.session.query(Project)
        .filter(Project.deleted_at.is_(None))
        .filter(Project.delivery_deadline.isnot(None))
        .filter(Project.delivery_deadline > week_from_now)
        .filter(Project.status != ProjectStatus.COMPLETED)
        .order_by(Project.delivery_deadline.asc())
        .all()
    )


def get_recently_completed(limit: int = 10) -> list[Project]:
    """Get recently completed projects.

    Returns projects where:
    - status == Completed
    - Not soft-deleted

    Projects are ordered by updated_at descending (most recently completed first).

    Args:
        limit: Maximum number of projects to return (default: 10).

    Returns:
        List of recently completed Project instances.
    """
    return (
        db.session.query(Project)
        .filter(Project.deleted_at.is_(None))
        .filter(Project.status == ProjectStatus.COMPLETED)
        .order_by(Project.updated_at.desc())
        .limit(limit)
        .all()
    )
