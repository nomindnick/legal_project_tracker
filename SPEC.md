# Legal Project Tracker

## Overview

A web-based project management system for law firms tracking legal work for large client engagements. Replaces spreadsheet-based tracking with a purpose-built application featuring a dashboard for deadline visibility, an Excel-style project list for daily management, and automated report generation for client communication.

## Problem Statement

Law firms handling ongoing legal work for large clients (counties, municipalities, corporations) often manage dozens of concurrent projects across multiple practice areas. Teams include partners, associates, and support staff working on various projects with different deadlines. Current tracking via Excel spreadsheets lacks:

- At-a-glance visibility into what's overdue or coming due
- Easy filtering and searching across projects
- Audit trail of project history
- Streamlined report generation for client updates

The lead attorney needs a system that surfaces deadline issues proactively, enables the team to self-manage their workload, and simplifies weekly status reporting to the client.

## Goals & Success Criteria

1. **Deadline visibility**: Anyone can glance at the dashboard and immediately see what's overdue, due soon, or needs attention
2. **Self-service for team**: Attorneys can filter to their own projects, update status, add notes without bothering the lead attorney
3. **Client reporting in minutes**: Generate a professional weekly status report with a few clicks, not manual Excel formatting
4. **Institutional memory**: Completed projects remain searchable so the team can reference how similar matters were handled

## Target Users

- **Lead Attorney**: Primary administrator. Creates projects, assigns work, monitors all deadlines, generates client reports. May maintain the codebase.
- **Partners**: QCP (Quality Control Partner) reviewers. Need to see projects awaiting their review and update status when complete.
- **Associates**: Primary workers. Need to see their assigned projects, update status, add notes as work progresses.
- **Legal Secretary**: Data entry support. May create projects or update fields on behalf of attorneys.

All users have basic computer proficiency. They're familiar with Excel-based tracking. The interface must feel intuitive to people who are not technical.

## Core Features

### 1. Dashboard

The home screen providing at-a-glance status of all active projects.

**Sections (based on delivery deadline):**
- **Overdue**: Projects where delivery deadline < today and status ≠ Completed. Red/urgent styling.
- **Due This Week**: Projects with delivery deadline within next 7 days.
- **Longer Deadline**: Active projects with delivery deadline beyond 7 days.
- **Recently Completed**: Last 10 projects marked Completed, for quick reference.

**Each project card shows:**
- Project name
- Department
- Date assigned to outside counsel
- Assigned attorney
- QCP attorney
- Internal deadline
- Delivery deadline
- Current status

Cards are clickable to open detail/edit view.

### 2. Projects Page

The main workhorse—an Excel-style table showing all projects.

**Features:**
- All fields visible (notes truncated with expand option)
- Sort by any column (click header)
- Filter by any field (dropdowns/text inputs above table)
- Search across project name, department, notes, project group
- **Default filter**: Excludes "Completed" status (but user can toggle to include)
- Inline status indicator with color coding
- Click row to open detail/edit modal or page

**Columns:**
ID | Project Name | Project Group | Department | Date to Client | Date Assigned to Us | Assigned Attorney | QCP Attorney | Internal Deadline | Delivery Deadline | Status | Notes (truncated)

### 3. New Project Form

Clean, single-page form for project entry.

**Fields:**
- Project Name (required)
- Project Group (optional) — for linking related deliverables
- Department (required, free text with autocomplete from previous entries)
- Date Given to Client (required, date picker) — when the client received the original request
- Date Assigned to Outside Counsel (required, defaults to today)
- Assigned Attorney (required, free text with autocomplete)
- QCP Attorney (required, free text with autocomplete)
- Internal Deadline (optional, date picker)
- Delivery Deadline (optional, date picker)
- Status (defaults to "In Progress")
- Notes (optional, textarea)

On submit: create project, redirect to Projects page with success message.

### 4. Edit Project

Modal or dedicated page for editing existing project.

- All fields from New Project form, pre-populated
- Status dropdown with all options (In Progress, Under Review, Waiting on Client, On-Hold, Completed)
- Notes field: "Add Note" textarea that appends to existing notes with timestamp (existing notes displayed read-only above)
- Save and Cancel buttons
- Clone button: opens New Project form pre-filled with current project's metadata (attorneys, department, project group) but empty dates
- Delete button with confirmation dialog ("Are you sure? This cannot be undone.") — performs soft delete

### 5. Reports Page

Generate two types of reports as HTML pages.

**Weekly Status Report:**
- List of active projects (non-Completed)
- Customizable fields via checkboxes (user selects which columns to include)
- Delivery deadline shown as "Anticipated Completion" (softer language)
- Excludes: internal deadline, notes (by default, but toggleable)
- Output: Clean HTML page suitable for copy/paste into email or print-to-PDF

**Monthly Statistics Report:**
- Projects opened this month (count)
- Projects completed this month (count)
- Projects by department (breakdown)
- Projects by assigned attorney (breakdown)
- Average days to completion (for completed projects)
- Output: HTML page with simple tables/charts

### 6. CSV Export

Export project data for use in Excel or other tools.

- `GET /projects/export` returns CSV of all projects matching current filters
- Includes all fields (notes may be truncated or excluded based on parameter)
- Uses standard CSV format compatible with Excel
- Available from Projects page via "Export to CSV" button

---

## Data Model

### Projects Table

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | integer | auto | Primary key, auto-increment |
| project_name | text | yes | |
| project_group | text | no | Links related deliverables |
| department | text | yes | Free text (case-normalized to match existing values) |
| date_to_client | date | yes | When client received the original request |
| date_assigned_to_us | date | yes | When outside counsel got it |
| assigned_attorney | text | yes | Free text (case-normalized to match existing values) |
| qcp_attorney | text | yes | Free text (case-normalized to match existing values) |
| internal_deadline | date | no | When work should reach QCP |
| delivery_deadline | date | no | When deliverable goes to client |
| status | text | yes | Enum: In Progress, Under Review, Waiting on Client, On-Hold, Completed |
| notes | text | no | Append-only format: each addition timestamped |
| created_at | timestamp | auto | |
| updated_at | timestamp | auto | |
| deleted_at | timestamp | no | Soft delete - when set, project is hidden from normal views |

### Supporting Data (No Separate Tables for MVP)

- **Departments**: Autocomplete populated from distinct values in projects.department
- **Attorneys**: Autocomplete populated from distinct values in assigned_attorney and qcp_attorney columns
- **Status values**: Hardcoded enum in application code

---

## Technical Architecture

### Technology Stack

- **Language**: Python 3.11+
- **Framework**: Flask
- **Database**: PostgreSQL (Railway provides this; SQLite for local dev acceptable)
- **ORM**: SQLAlchemy
- **Templates**: Jinja2
- **CSS**: Bootstrap 5 (via CDN) — professional components out-of-the-box, no build step
- **JavaScript**: HTMX for interactivity (keeps logic server-side in Python/Jinja), minimal vanilla JS where needed
- **Deployment**: Railway (MVP), Azure or firm infrastructure (production)

### Application Structure

```
legal-project-tracker/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── config.py            # Configuration (env-based)
│   ├── models/
│   │   ├── __init__.py
│   │   └── project.py       # Project model
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── dashboard.py     # Dashboard routes
│   │   ├── projects.py      # Projects CRUD routes
│   │   └── reports.py       # Report generation routes
│   ├── services/
│   │   ├── __init__.py
│   │   ├── project_service.py    # Business logic for projects
│   │   └── report_service.py     # Report generation logic
│   ├── templates/
│   │   ├── base.html        # Base template with nav
│   │   ├── dashboard.html
│   │   ├── projects.html
│   │   ├── project_form.html
│   │   ├── project_detail.html
│   │   └── reports/
│   │       ├── report_builder.html
│   │       ├── weekly_status.html
│   │       └── monthly_stats.html
│   └── static/
│       ├── css/
│       └── js/
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Pytest fixtures
│   ├── test_models.py
│   ├── test_services.py
│   └── test_routes.py
├── migrations/              # Alembic migrations
├── requirements.txt
├── .env.example
├── .gitignore
├── Procfile                 # For Railway
└── README.md
```

### Key Design Decisions

1. **Layered architecture**: Routes handle HTTP, services handle business logic, models handle data. This separation makes the codebase easier to understand and modify. When you want to understand "how does project creation work," look in `services/project_service.py`, not scattered across route handlers.

2. **No authentication for MVP**: Deploy publicly with fake data for feedback. Build with `current_user` patterns so auth can be added later via Microsoft Entra ID (Flask-Login + MSAL).

3. **Free text with soft normalization**: Attorneys and departments are free text to avoid admin overhead, but the service layer normalizes input to match existing values (case-insensitive). If "Public Works" exists and user types "public works", it saves as "Public Works". Prevents report fragmentation.

4. **Append-only notes**: Notes are never overwritten. Adding a note appends with timestamp: `[2024-01-15 14:30]: Note content here`. Prevents data loss from concurrent edits and creates implicit audit trail.

5. **Soft delete**: Projects are never hard-deleted. Setting `deleted_at` hides them from normal views. Critical for legal context where you may need to prove a project existed.

6. **Status as free-flowing**: No enforced transitions. Trust users to set status correctly. Reduces code complexity.

7. **Delivery deadline drives dashboard**: Internal deadline is for individual attorney management; delivery deadline is what matters for client-facing urgency.

8. **PostgreSQL from the start**: Matches Railway production. Avoids SQLite-to-Postgres migration issues.

9. **HTMX over JavaScript frameworks**: Keeps interactivity logic server-side in Python/Jinja. Easier to understand and maintain for non-frontend developers. Filter/sort operations return HTML fragments, not JSON that requires client-side rendering.

### Auth-Ready Patterns

Even without implementing auth, structure code to support it later:

- Use a `get_current_user()` function that returns a placeholder user dict for now
- Store attorney names as strings (will map to user identities later)
- Avoid hardcoding user-specific logic in templates
- Keep session/cookie handling minimal and standard

---

## Constraints & Considerations

### Out of Scope for MVP

- User authentication / permissions
- Email notifications for deadlines
- Client portal access
- Integration with document management or billing systems
- Mobile-specific layouts (responsive is fine, native app is not)
- Activity log with timestamps (single notes field instead)
- Admin panel for managing dropdown values

### Security Considerations (Post-MVP)

- Microsoft Entra ID integration for SSO
- HTTPS everywhere (Railway provides this)
- No real client data in public demo—use realistic fake data
- Production deployment will need IT review

### Known Challenges

- **Autocomplete UX**: Free text fields need good autocomplete to prevent inconsistency. May need debounced API calls.
- **Table performance**: If project count grows large (100+), client-side filtering may need optimization or server-side pagination.
- **Report formatting**: HTML-to-PDF via print is acceptable but may have styling quirks across browsers.

### Future Considerations (Phase 2+)

- Full activity log with author attribution (building on append-only notes)
- Parent/child project relationships (upgrade from project groups)
- Email reminders for approaching deadlines
- Semantic search across project descriptions and notes
- Client portal for direct status viewing
- Integration with firm systems (document management, billing/matter numbers)
- Undo/restore for soft-deleted projects (admin view of deleted items)

---

## Notes for Claude Code

### Implementation Preferences

1. **Modularity over brevity**: Prefer more files with clear single responsibilities over fewer files with mixed concerns. The maintainer needs to understand and maintain this.

2. **Comments for "why"**: Add comments explaining non-obvious decisions, especially in services layer where business logic lives.

3. **Test as you go**: Each feature sprint should include tests for that feature. Don't defer testing to the end.

4. **Consistent patterns**: Establish patterns in early sprints (how routes call services, how services return data, how errors are handled) and follow them throughout.

5. **Semantic HTML**: Use proper HTML elements (table for tabular data, form for forms, button for actions). Helps with accessibility and print styling.

6. **CSS approach**: Use Bootstrap 5 utility classes and components. Avoid custom CSS unless necessary. Keep styling maintainable for a non-frontend developer.

7. **HTMX for interactivity**: Use HTMX attributes (`hx-get`, `hx-post`, `hx-target`, `hx-swap`) for dynamic updates. Server returns HTML fragments, not JSON. Keeps logic in Python/Jinja where it's easier to test and understand. Minimal vanilla JS only where HTMX doesn't fit.

8. **Error handling**: User-friendly error messages. Log details server-side. Never expose stack traces to users.

9. **Database migrations**: Use Alembic. Every schema change gets a migration file.

10. **Environment variables**: All configuration (database URL, secret key, debug mode) via environment variables. Provide `.env.example` with dummy values.

### Coding Standards

- Python: Follow PEP 8, use type hints for function signatures
- Max line length: 100 characters
- Use f-strings for string formatting
- Docstrings for all public functions
- Imports: standard library, then third-party, then local (separated by blank lines)

### Testing Standards

- Use pytest
- Fixtures for database setup/teardown
- Test happy path and key error cases
- Aim for services to be fully testable without HTTP layer
