# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Legal Project Tracker is a web-based project management system for law firms tracking legal work on large client engagements. It replaces spreadsheet-based tracking with deadline visibility, project management, and automated reporting.

**Status:** Planning phase complete. Implementation pending.

## Technology Stack

- **Backend:** Python 3.11+, Flask, SQLAlchemy ORM, Alembic migrations
- **Database:** PostgreSQL (Railway), SQLite for local dev
- **Frontend:** Jinja2 templates, Bootstrap 5 (CDN), HTMX for interactivity
- **Testing:** pytest
- **Deployment:** Railway with gunicorn

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run development server
flask run

# Run all tests
pytest

# Run database migrations
flask db upgrade

# Seed database with test data
python scripts/seed_data.py

# Reset database and re-seed
python scripts/reset_db.py
```

## Architecture

**Layered architecture:** Routes → Services → Models → Database

```
app/
├── __init__.py          # Flask app factory
├── config.py            # Environment-based configuration
├── models/              # SQLAlchemy ORM models
├── routes/              # Flask blueprints (dashboard, projects, reports)
├── services/            # Business logic layer
├── templates/           # Jinja2 templates
└── static/              # CSS/JS assets
```

Routes handle HTTP only. Services contain all business logic. This separation makes code testable and maintainable.

## Key Design Patterns

1. **Soft delete:** Projects set `deleted_at` timestamp but remain in database. Critical for legal context where you may need to prove a project existed.

2. **Append-only notes:** Notes never overwritten, always appended with timestamp format: `[YYYY-MM-DD HH:MM]: note`. Creates audit trail.

3. **Soft normalization:** Free-text fields (department, attorney names) are case-normalized to match existing values. "public works" saves as "Public Works" if that exists.

4. **HTMX-first interactivity:** Server returns HTML fragments, not JSON. Logic stays in Python/Jinja. Minimal vanilla JS.

5. **No authentication for MVP:** Code structured with `get_current_user()` patterns so auth can be added later via Microsoft Entra ID.

## Implementation Plan

Development is organized into 7 phases across 16 sprints in IMPLEMENTATION_PLAN.md. Sprints are marked as:
- **Ralph-friendly:** Can run automated with clear acceptance criteria
- **Interactive:** Requires human judgment for UI/UX decisions

Use `/ralph-loop` for Ralph-friendly sprints and the `frontend-design` plugin for Interactive UI sprints.

## Data Model

Single `projects` table with: project_name, project_group, department, date_to_client, date_assigned_to_us, assigned_attorney, qcp_attorney, internal_deadline, delivery_deadline, status, notes, created_at, updated_at, deleted_at.

Status enum: In Progress, Under Review, Waiting on Client, On-Hold, Completed.

## Coding Standards

- PEP 8 with 100-character line length
- Type hints for function signatures
- f-strings for formatting
- Docstrings for public functions
- Imports organized: stdlib → third-party → local (separated by blank lines)

## Environment Variables

```
DATABASE_URL=postgresql://user:pass@host:5432/legal_tracker
SECRET_KEY=your-secret-key-here
DEBUG=true
```
