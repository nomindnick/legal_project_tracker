"""Project model for the Legal Project Tracker.

This module defines the Project model which represents a legal project
being tracked in the system.
"""
from datetime import datetime, timezone
from typing import Optional


def _utcnow():
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)

from app import db


class ProjectStatus:
    """Enumeration of valid project status values.

    Status values are stored as strings in the database to keep
    the schema simple and allow easy inspection via SQL.
    """
    IN_PROGRESS = "In Progress"
    UNDER_REVIEW = "Under Review"
    WAITING_ON_CLIENT = "Waiting on Client"
    ON_HOLD = "On-Hold"
    COMPLETED = "Completed"

    ALL = [IN_PROGRESS, UNDER_REVIEW, WAITING_ON_CLIENT, ON_HOLD, COMPLETED]


class Project(db.Model):
    """SQLAlchemy model for legal projects.

    Represents a legal project with all associated metadata including
    deadlines, assignments, status, and notes. Supports soft deletion
    via the deleted_at timestamp.

    Attributes:
        id: Primary key, auto-incrementing integer.
        project_name: Name/title of the project (required).
        project_group: Optional grouping for related projects.
        department: Client department this project belongs to (required).
        date_to_client: When the client received the original request.
        date_assigned_to_us: When outside counsel received the project.
        assigned_attorney: Primary attorney working on the project.
        qcp_attorney: Quality Control Partner reviewing the work.
        internal_deadline: When work should reach QCP for review.
        delivery_deadline: When deliverable goes to client.
        status: Current project status (defaults to In Progress).
        notes: Append-only notes with timestamps.
        created_at: Timestamp when project was created.
        updated_at: Timestamp when project was last modified.
        deleted_at: Soft delete timestamp (null if not deleted).
    """
    __tablename__ = 'projects'

    # Primary key
    id: int = db.Column(db.Integer, primary_key=True)

    # Project identification
    project_name: str = db.Column(db.String(500), nullable=False)
    project_group: Optional[str] = db.Column(db.String(200), nullable=True)

    # Client/department info
    department: str = db.Column(db.String(200), nullable=False)

    # Important dates
    date_to_client: datetime = db.Column(db.Date, nullable=False)
    date_assigned_to_us: datetime = db.Column(db.Date, nullable=False)
    internal_deadline: Optional[datetime] = db.Column(db.Date, nullable=True)
    delivery_deadline: Optional[datetime] = db.Column(db.Date, nullable=True)

    # Assignments
    assigned_attorney: str = db.Column(db.String(200), nullable=False)
    qcp_attorney: str = db.Column(db.String(200), nullable=False)

    # Status and notes
    status: str = db.Column(
        db.String(50),
        nullable=False,
        default=ProjectStatus.IN_PROGRESS
    )
    notes: Optional[str] = db.Column(db.Text, nullable=True)

    # Timestamps
    created_at: datetime = db.Column(
        db.DateTime,
        nullable=False,
        default=_utcnow
    )
    updated_at: datetime = db.Column(
        db.DateTime,
        nullable=False,
        default=_utcnow,
        onupdate=_utcnow
    )

    # Soft delete
    deleted_at: Optional[datetime] = db.Column(db.DateTime, nullable=True)

    def __repr__(self) -> str:
        """Return string representation of the project."""
        return f'<Project {self.id}: {self.project_name}>'

    @property
    def is_deleted(self) -> bool:
        """Check if the project has been soft-deleted."""
        return self.deleted_at is not None

    def to_dict(self) -> dict:
        """Convert project to dictionary representation.

        Useful for JSON serialization and testing.

        Returns:
            Dictionary with all project fields.
        """
        return {
            'id': self.id,
            'project_name': self.project_name,
            'project_group': self.project_group,
            'department': self.department,
            'date_to_client': self.date_to_client.isoformat() if self.date_to_client else None,
            'date_assigned_to_us': self.date_assigned_to_us.isoformat() if self.date_assigned_to_us else None,
            'internal_deadline': self.internal_deadline.isoformat() if self.internal_deadline else None,
            'delivery_deadline': self.delivery_deadline.isoformat() if self.delivery_deadline else None,
            'assigned_attorney': self.assigned_attorney,
            'qcp_attorney': self.qcp_attorney,
            'status': self.status,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None,
        }
