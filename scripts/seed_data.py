#!/usr/bin/env python3
"""Seed data script for Legal Project Tracker.

Generates 27 realistic fake legal projects for development and testing.
Designed to populate all dashboard sections (overdue, due this week,
longer deadline, recently completed).

Usage:
    python scripts/seed_data.py

The script is idempotent - it checks for existing projects and skips
seeding if data already exists. Use reset_db.py to clear and reseed.
"""
import random
import sys
from datetime import date, timedelta
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app, db
from app.models import Project, ProjectStatus


# Sample data constants
DEPARTMENTS = [
    "Public Works",
    "Human Resources",
    "Finance",
    "Information Technology",
    "Parks & Recreation",
    "Sheriff's Office",
    "County Counsel",
    "Planning",
    "Health Services",
    "Building & Safety",
]

ATTORNEYS = [
    "Smith, J.",
    "Johnson, M.",
    "Williams, R.",
    "Brown, S.",
    "Davis, K.",
    "Miller, A.",
    "Wilson, T.",
    "Garcia, L.",
]

# Project name templates by category
PROJECT_TEMPLATES = {
    "investigation": [
        "Employment Investigation - {dept}-{year}-{num:02d}",
        "Workplace Complaint Investigation - {dept}",
        "Internal Affairs Review - {dept}",
    ],
    "agreement": [
        "Easement Agreement - {dept}",
        "Service Contract Review - {dept}",
        "Interagency Agreement - {dept}",
        "Vendor Agreement Review - {dept}",
    ],
    "review": [
        "Review of {policy} Policy",
        "Policy Update - {policy}",
        "Ordinance Review - {topic}",
        "Code Compliance Review - {dept}",
    ],
    "prr": [
        "Public Records Request #{year}-{num:03d}",
        "PRR Response - {dept} #{num:03d}",
        "FOIA Request #{year}-{num:03d}",
    ],
    "litigation": [
        "Litigation Hold - {dept}",
        "Claim Review - {dept}-{year}-{num:02d}",
        "Settlement Analysis - {topic}",
    ],
}

POLICIES = [
    "Procurement",
    "Travel & Expense",
    "Remote Work",
    "Vehicle Use",
    "Social Media",
    "Retention",
    "Privacy",
    "Safety",
]

TOPICS = [
    "Zoning Variance",
    "Environmental Compliance",
    "ADA Accessibility",
    "Construction Permits",
    "Labor Relations",
    "Public Comment",
]


def generate_project_name(category: str, dept: str, counter: int) -> str:
    """Generate a realistic project name based on category."""
    year = date.today().year
    template = random.choice(PROJECT_TEMPLATES[category])

    return template.format(
        dept=dept.split()[0],  # First word of department
        year=year,
        num=counter,
        policy=random.choice(POLICIES),
        topic=random.choice(TOPICS),
    )


def generate_notes(num_entries: int = 0) -> str | None:
    """Generate sample timestamped notes."""
    if num_entries == 0:
        return None

    note_templates = [
        "Initial review started",
        "Research completed, drafting response",
        "Sent to QCP for review",
        "QCP comments received, revising",
        "Client follow-up call scheduled",
        "Awaiting additional documents from client",
        "Draft delivered for internal review",
        "Final review in progress",
        "Ready for delivery",
    ]

    today = date.today()
    notes = []
    for i in range(num_entries):
        days_ago = (num_entries - i) * 3 + random.randint(0, 2)
        note_date = today - timedelta(days=days_ago)
        hour = random.randint(8, 17)
        minute = random.choice([0, 15, 30, 45])
        timestamp = f"{note_date.isoformat()} {hour:02d}:{minute:02d}"
        note_text = note_templates[min(i, len(note_templates) - 1)]
        notes.append(f"[{timestamp}]: {note_text}")

    return "\n".join(notes)


def create_seed_projects() -> list[dict]:
    """Generate list of seed project data dictionaries."""
    today = date.today()
    projects = []
    counter = 1

    # Helper to pick attorneys (assigned and QCP should be different)
    def pick_attorneys():
        assigned = random.choice(ATTORNEYS)
        qcp = random.choice([a for a in ATTORNEYS if a != assigned])
        return assigned, qcp

    # === OVERDUE PROJECTS (4) ===
    # delivery_deadline in past, status != Completed
    for i in range(4):
        dept = random.choice(DEPARTMENTS)
        assigned, qcp = pick_attorneys()
        days_overdue = random.randint(3, 21)
        days_assigned = days_overdue + random.randint(14, 30)

        projects.append({
            "project_name": generate_project_name("review", dept, counter),
            "department": dept,
            "date_to_client": today - timedelta(days=days_assigned + 5),
            "date_assigned_to_us": today - timedelta(days=days_assigned),
            "assigned_attorney": assigned,
            "qcp_attorney": qcp,
            "internal_deadline": today - timedelta(days=days_overdue + 3),
            "delivery_deadline": today - timedelta(days=days_overdue),
            "status": random.choice([ProjectStatus.IN_PROGRESS, ProjectStatus.UNDER_REVIEW]),
            "notes": generate_notes(random.randint(1, 3)),
        })
        counter += 1

    # === DUE THIS WEEK (6) ===
    # delivery_deadline within 0-6 days from today
    for i in range(6):
        dept = random.choice(DEPARTMENTS)
        assigned, qcp = pick_attorneys()
        days_until_due = random.randint(0, 6)
        days_assigned = random.randint(14, 30)

        projects.append({
            "project_name": generate_project_name(
                random.choice(["prr", "agreement", "review"]), dept, counter
            ),
            "department": dept,
            "date_to_client": today - timedelta(days=days_assigned + 5),
            "date_assigned_to_us": today - timedelta(days=days_assigned),
            "assigned_attorney": assigned,
            "qcp_attorney": qcp,
            "internal_deadline": today + timedelta(days=days_until_due - 2),
            "delivery_deadline": today + timedelta(days=days_until_due),
            "status": random.choice([
                ProjectStatus.IN_PROGRESS,
                ProjectStatus.UNDER_REVIEW,
                ProjectStatus.WAITING_ON_CLIENT,
            ]),
            "notes": generate_notes(random.randint(2, 4)),
        })
        counter += 1

    # === LONGER DEADLINE (8) ===
    # delivery_deadline > 7 days out
    for i in range(8):
        dept = random.choice(DEPARTMENTS)
        assigned, qcp = pick_attorneys()
        days_until_due = random.randint(8, 45)
        days_assigned = random.randint(7, 21)

        projects.append({
            "project_name": generate_project_name(
                random.choice(["investigation", "litigation", "agreement"]), dept, counter
            ),
            "department": dept,
            "date_to_client": today - timedelta(days=days_assigned + 5),
            "date_assigned_to_us": today - timedelta(days=days_assigned),
            "assigned_attorney": assigned,
            "qcp_attorney": qcp,
            "internal_deadline": today + timedelta(days=days_until_due - 5),
            "delivery_deadline": today + timedelta(days=days_until_due),
            "status": random.choice([
                ProjectStatus.IN_PROGRESS,
                ProjectStatus.ON_HOLD,
                ProjectStatus.WAITING_ON_CLIENT,
            ]),
            "notes": generate_notes(random.randint(0, 2)),
        })
        counter += 1

    # === NO DEADLINE (4) ===
    # delivery_deadline is None
    for i in range(4):
        dept = random.choice(DEPARTMENTS)
        assigned, qcp = pick_attorneys()
        days_assigned = random.randint(7, 30)

        projects.append({
            "project_name": generate_project_name("review", dept, counter),
            "department": dept,
            "date_to_client": today - timedelta(days=days_assigned + 5),
            "date_assigned_to_us": today - timedelta(days=days_assigned),
            "assigned_attorney": assigned,
            "qcp_attorney": qcp,
            "internal_deadline": None,
            "delivery_deadline": None,
            "status": random.choice([ProjectStatus.IN_PROGRESS, ProjectStatus.ON_HOLD]),
            "notes": generate_notes(random.randint(0, 1)),
        })
        counter += 1

    # === COMPLETED (5) ===
    # status = Completed, for "Recently Completed" section
    for i in range(5):
        dept = random.choice(DEPARTMENTS)
        assigned, qcp = pick_attorneys()
        days_completed = random.randint(1, 14)
        days_assigned = days_completed + random.randint(14, 30)

        projects.append({
            "project_name": generate_project_name(
                random.choice(["prr", "agreement", "review"]), dept, counter
            ),
            "department": dept,
            "date_to_client": today - timedelta(days=days_assigned + 5),
            "date_assigned_to_us": today - timedelta(days=days_assigned),
            "assigned_attorney": assigned,
            "qcp_attorney": qcp,
            "internal_deadline": today - timedelta(days=days_completed + 3),
            "delivery_deadline": today - timedelta(days=days_completed),
            "status": ProjectStatus.COMPLETED,
            "notes": generate_notes(random.randint(3, 5)),
        })
        counter += 1

    return projects


def create_project_group_projects() -> list[dict]:
    """Generate projects belonging to project groups (related deliverables)."""
    today = date.today()
    projects = []

    # === Municipal Code Updates group (3 projects) ===
    assigned, qcp = "Smith, J.", "Johnson, M."
    base_date = today - timedelta(days=21)

    group_1_projects = [
        {
            "project_name": "Municipal Code Updates - Chapter 5 Zoning",
            "project_group": "Municipal Code Updates",
            "department": "Planning",
            "date_to_client": base_date - timedelta(days=5),
            "date_assigned_to_us": base_date,
            "assigned_attorney": assigned,
            "qcp_attorney": qcp,
            "internal_deadline": today + timedelta(days=5),
            "delivery_deadline": today + timedelta(days=10),
            "status": ProjectStatus.IN_PROGRESS,
            "notes": generate_notes(2),
        },
        {
            "project_name": "Municipal Code Updates - Chapter 8 Building",
            "project_group": "Municipal Code Updates",
            "department": "Building & Safety",
            "date_to_client": base_date - timedelta(days=5),
            "date_assigned_to_us": base_date,
            "assigned_attorney": assigned,
            "qcp_attorney": qcp,
            "internal_deadline": today + timedelta(days=8),
            "delivery_deadline": today + timedelta(days=14),
            "status": ProjectStatus.IN_PROGRESS,
            "notes": generate_notes(1),
        },
        {
            "project_name": "Municipal Code Updates - Chapter 12 Environment",
            "project_group": "Municipal Code Updates",
            "department": "Public Works",
            "date_to_client": base_date - timedelta(days=5),
            "date_assigned_to_us": base_date,
            "assigned_attorney": assigned,
            "qcp_attorney": qcp,
            "internal_deadline": today + timedelta(days=12),
            "delivery_deadline": today + timedelta(days=18),
            "status": ProjectStatus.IN_PROGRESS,
            "notes": None,
        },
    ]
    projects.extend(group_1_projects)

    # === Q4 Public Records Requests group (3 projects) ===
    assigned, qcp = "Davis, K.", "Miller, A."
    base_date = today - timedelta(days=14)
    year = today.year

    group_2_projects = [
        {
            "project_name": f"PRR #{year}-401 - Sheriff Body Cam Footage",
            "project_group": "Q4 Public Records Requests",
            "department": "Sheriff's Office",
            "date_to_client": base_date - timedelta(days=3),
            "date_assigned_to_us": base_date,
            "assigned_attorney": assigned,
            "qcp_attorney": qcp,
            "internal_deadline": today + timedelta(days=1),
            "delivery_deadline": today + timedelta(days=3),
            "status": ProjectStatus.UNDER_REVIEW,
            "notes": generate_notes(3),
        },
        {
            "project_name": f"PRR #{year}-402 - Finance Budget Documents",
            "project_group": "Q4 Public Records Requests",
            "department": "Finance",
            "date_to_client": base_date - timedelta(days=3),
            "date_assigned_to_us": base_date,
            "assigned_attorney": assigned,
            "qcp_attorney": qcp,
            "internal_deadline": today - timedelta(days=1),
            "delivery_deadline": today + timedelta(days=2),
            "status": ProjectStatus.IN_PROGRESS,
            "notes": generate_notes(2),
        },
        {
            "project_name": f"PRR #{year}-403 - HR Personnel Records",
            "project_group": "Q4 Public Records Requests",
            "department": "Human Resources",
            "date_to_client": base_date - timedelta(days=3),
            "date_assigned_to_us": base_date,
            "assigned_attorney": assigned,
            "qcp_attorney": qcp,
            "internal_deadline": today + timedelta(days=4),
            "delivery_deadline": today + timedelta(days=7),
            "status": ProjectStatus.WAITING_ON_CLIENT,
            "notes": generate_notes(2),
        },
    ]
    projects.extend(group_2_projects)

    return projects


def seed_database() -> int:
    """Seed the database with fake projects.

    Returns:
        Number of projects created.
    """
    # Combine regular and project group projects
    all_projects = create_seed_projects() + create_project_group_projects()

    # Create projects using direct model instantiation
    # (bypassing service to avoid normalization affecting our controlled data)
    created_count = 0
    for data in all_projects:
        project = Project(**data)
        db.session.add(project)
        created_count += 1

    db.session.commit()
    return created_count


def main():
    """Main entry point for seed script."""
    app = create_app()

    with app.app_context():
        # Check if projects already exist
        existing_count = db.session.query(Project).count()
        if existing_count > 0:
            print(f"Database already contains {existing_count} projects.")
            print("To reseed, run: python scripts/reset_db.py")
            return

        print("Seeding database with fake projects...")
        count = seed_database()
        print(f"Created {count} projects.")

        # Print summary
        statuses = {}
        for status in ProjectStatus.ALL:
            status_count = db.session.query(Project).filter_by(status=status).count()
            statuses[status] = status_count
            print(f"  - {status}: {status_count}")

        # Count overdue
        today = date.today()
        overdue = (
            db.session.query(Project)
            .filter(Project.delivery_deadline < today)
            .filter(Project.status != ProjectStatus.COMPLETED)
            .filter(Project.deleted_at.is_(None))
            .count()
        )
        print(f"  - Overdue: {overdue}")

        # Count due this week
        week_end = today + timedelta(days=6)
        due_this_week = (
            db.session.query(Project)
            .filter(Project.delivery_deadline >= today)
            .filter(Project.delivery_deadline <= week_end)
            .filter(Project.status != ProjectStatus.COMPLETED)
            .filter(Project.deleted_at.is_(None))
            .count()
        )
        print(f"  - Due this week: {due_this_week}")

        # Count project groups
        groups = (
            db.session.query(Project.project_group)
            .filter(Project.project_group.isnot(None))
            .distinct()
            .count()
        )
        print(f"  - Project groups: {groups}")

        print("\nSeed complete!")


if __name__ == "__main__":
    main()
