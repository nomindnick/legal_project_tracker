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
)

__all__ = [
    'create_project',
    'get_project',
    'get_all_projects',
    'update_project',
    'delete_project',
    'append_note',
    'get_distinct_values',
]
