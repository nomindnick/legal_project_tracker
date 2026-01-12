# Implementation Plan: Legal Project Tracker

> **Reference:** See [SPEC.md](./SPEC.md) for full project context, architecture decisions, and feature details.

## Overview

This plan organizes development into seven phases, progressing from foundation through core features to polish. Each sprint is 1-2 hours and results in testable, working code. Sprints are tagged as **Ralph-friendly** (can run automated with clear success criteria) or **Interactive** (requires human judgment for UI/UX).

**Estimated Total Time:** 18-22 hours across 16 sprints

---

## Phase 1: Foundation

**Goal:** Project scaffolding, dependencies installed, database connected, basic app runs.

### Sprint 1.1: Project Setup
**Estimated Time:** 1 hour  
**Mode:** Ralph-friendly

**Objective:** Create project structure, install dependencies, configure Flask app factory.

**Tasks:**
- [x] Create directory structure per SPEC.md architecture section
- [x] Create `requirements.txt` with: Flask, SQLAlchemy, Flask-SQLAlchemy, psycopg2-binary, python-dotenv, pytest, alembic
- [x] Create `app/__init__.py` with Flask app factory pattern
- [x] Create `app/config.py` with Config class reading from environment variables (DATABASE_URL, SECRET_KEY, DEBUG)
- [x] Create `.env.example` with placeholder values
- [x] Create `.gitignore` (Python defaults, .env, __pycache__, .pytest_cache)
- [x] Create `Procfile` with `web: gunicorn app:create_app()`
- [x] Create basic `README.md` with setup instructions
- [x] Add gunicorn to requirements.txt

**Acceptance Criteria:**
- `pip install -r requirements.txt` succeeds
- `flask run` starts server without errors (may 404, that's fine)
- All directories exist per structure in SPEC.md
- `.env.example` contains DATABASE_URL, SECRET_KEY, DEBUG

**Sprint Update:**
> **Completed 2026-01-10** - All tasks completed successfully. Added Flask-Migrate for easier database migrations with Flask integration. Created virtual environment (venv/) for development. All acceptance criteria verified: dependencies install, flask runs, directory structure complete, .env.example has all required variables. Added /health endpoint for basic server health checks.

---

### Sprint 1.2: Database Model & Migrations
**Estimated Time:** 1-1.5 hours  
**Mode:** Ralph-friendly

**Objective:** Create Project model, set up Alembic, run initial migration.

**Tasks:**
- [x] Create `app/models/__init__.py` that imports and exposes all models
- [x] Create `app/models/project.py` with Project model matching SPEC.md data model
- [x] Configure Flask-SQLAlchemy in app factory
- [x] Initialize Alembic (`flask db init` or `alembic init migrations`)
- [x] Create initial migration for projects table
- [x] Apply migration to create table
- [x] Create `tests/conftest.py` with pytest fixtures for test database
  - **Important:** Configure separate test database (SQLite in-memory or `test_` prefixed DB) to avoid wiping dev data during test runs
- [x] Create `tests/test_models.py` with basic model tests

**Acceptance Criteria:**
- `flask db upgrade` runs without errors
- Database contains `projects` table with all columns from SPEC
- `pytest tests/test_models.py` passes
- Model includes: id, project_name, project_group, department, date_to_client, date_assigned_to_us, assigned_attorney, qcp_attorney, internal_deadline, delivery_deadline, status, notes, created_at, updated_at, deleted_at
- Test database is isolated from development database (verified by checking test fixtures)

**Sprint Update:**
> **Completed 2026-01-10** - All tasks completed successfully. Created Project model with all 15 fields from SPEC.md including soft delete support via deleted_at timestamp. Added ProjectStatus class with all 5 status values. Initialized Flask-Migrate and created initial migration for projects table. Set up pytest fixtures with isolated in-memory SQLite test database (sqlite:///:memory:) to avoid affecting dev data. All 14 model tests pass. Committed as 82ab7ed.

---

## Phase 2: Core Backend Services

**Goal:** Business logic layer complete. Projects can be created, read, updated via service functions.

### Sprint 2.1: Project Service
**Estimated Time:** 1.5 hours  
**Mode:** Ralph-friendly

**Objective:** Implement service layer for project CRUD operations.

**Tasks:**
- [x] Create `app/services/__init__.py`
- [x] Create `app/services/project_service.py` with functions:
  - `create_project(data: dict) -> Project`
  - `get_project(id: int) -> Project | None` (excludes soft-deleted)
  - `get_all_projects(filters: dict = None) -> list[Project]` (excludes soft-deleted by default)
  - `update_project(id: int, data: dict) -> Project`
  - `delete_project(id: int) -> bool` (soft delete: sets deleted_at timestamp)
  - `append_note(id: int, note: str) -> Project` (appends with timestamp format: `[YYYY-MM-DD HH:MM]: note`)
  - `get_distinct_values(field: str) -> list[str]` (for autocomplete)
- [x] Implement **soft normalization** in create/update: when saving department, assigned_attorney, or qcp_attorney, check for case-insensitive match to existing value and use canonical version
- [x] Implement filtering in `get_all_projects`: by status, department, assigned_attorney, qcp_attorney, date ranges
- [x] Implement sorting in `get_all_projects`: by any field, ascending or descending
- [x] Create `tests/test_services.py` with comprehensive tests for each function

**Acceptance Criteria:**
- All service functions work correctly (verified by tests)
- `pytest tests/test_services.py` passes
- Filtering by status correctly excludes/includes Completed projects
- `get_distinct_values('department')` returns unique department names
- `delete_project(id)` sets deleted_at timestamp (not hard delete); deleted projects excluded from normal queries
- `append_note` adds timestamped entry without overwriting existing notes
- Soft normalization: saving "public works" when "Public Works" exists results in "Public Works"

**Sprint Update:**
> **Completed 2026-01-11** - All tasks completed successfully. Created project_service.py with 7 service functions: create_project, get_project, get_all_projects, update_project, delete_project, append_note, and get_distinct_values. Implemented soft normalization for department, assigned_attorney, and qcp_attorney fields. Added comprehensive filtering (status, department, attorneys, date ranges) and sorting (any field, asc/desc with nulls-last). Created 43 tests covering all functionality. All 57 tests pass (14 model + 43 service).

---

### Sprint 2.2: Project Routes (API)
**Estimated Time:** 1.5 hours  
**Mode:** Ralph-friendly

**Objective:** HTTP routes that call service layer. RESTful endpoints for projects.

**Tasks:**
- [x] Create `app/routes/__init__.py` with blueprint registration helper
- [x] Create `app/routes/projects.py` with Flask blueprint:
  - `GET /projects` - list all (with query params for filters/sort)
  - `GET /projects/<id>` - single project
  - `POST /projects` - create new
  - `PUT /projects/<id>` - update existing
  - `DELETE /projects/<id>` - delete project
  - `GET /api/autocomplete/<field>` - distinct values for autocomplete
- [x] Register blueprint in app factory
- [x] Add proper error handling (400 for bad input, 404 for not found)
- [x] Create `tests/test_routes.py` with route tests using Flask test client

**Acceptance Criteria:**
- All endpoints return correct status codes
- `GET /projects` returns JSON array of projects
- `GET /projects?status=In+Progress` filters correctly
- `POST /projects` with valid data returns 201 and created project
- `PUT /projects/<id>` with valid data returns 200 and updated project
- `DELETE /projects/<id>` returns 200 and removes project from database
- `pytest tests/test_routes.py` passes

**Sprint Update:**
> **Completed 2026-01-11** - All tasks completed successfully. Created projects blueprint with 6 RESTful endpoints: GET/POST /projects, GET/PUT/DELETE /projects/<id>, and GET /api/autocomplete/<field>. Added register_blueprints() helper in routes/__init__.py. Implemented comprehensive query parameter handling for filtering (status, department, attorneys, date ranges, include_completed, include_deleted) and sorting. Also added POST /projects/<id>/notes endpoint for append-only notes (ahead of Sprint 4.3 schedule). Created 47 route tests covering all endpoints and edge cases. All 104 tests pass (14 model + 43 service + 47 route).

---

### Sprint 2.3: Seed Data
**Estimated Time:** 1 hour  
**Mode:** Ralph-friendly

**Objective:** Create realistic fake data so all subsequent UI sprints can be tested against real scenarios.

**Tasks:**
- [x] Create `scripts/seed_data.py`:
  - Generates 25-30 fake projects with realistic:
    - Department names (Public Works, Human Resources, Finance, IT, Parks & Recreation, Sheriff's Office, County Counsel, Planning, Health Services, etc.)
    - Project names (legal-sounding: "Review of Procurement Policy", "Employment Investigation - HR-2024-03", "Easement Agreement - Parks", "Public Records Request #2024-156")
    - Date ranges spanning last 3 months
    - Mix of statuses (ensure some In Progress, some Under Review, some Completed)
    - Some with project groups (e.g., "Municipal Code Updates" with 3 related projects)
    - Variety of deadlines: some overdue, some due this week, some with longer deadlines, some with no deadline
    - Sample notes with timestamps demonstrating append-only format
- [x] Create `scripts/reset_db.py` - drops and recreates tables, runs seed
- [x] Ensure seed script is idempotent (can run multiple times safely)

**Acceptance Criteria:**
- `python scripts/seed_data.py` populates database with 25-30 projects
- Projects span all status types
- At least 3 projects are overdue (delivery_deadline in past)
- At least 5 projects are due this week
- At least 2 project groups with multiple related projects exist
- `python scripts/reset_db.py` cleanly resets database and re-seeds

**Sprint Update:**
> **Completed 2026-01-11** - All tasks completed successfully. Created seed_data.py that generates 33 fake projects with realistic legal project names, 10 departments, and 8 attorneys. Distribution: 4 overdue, 8 due this week, 8 longer deadline, 4 no deadline, and 5 completed. Created 2 project groups ("Municipal Code Updates" and "Q4 Public Records Requests") with 3 related projects each. Notes demonstrate timestamped append-only format. reset_db.py clears all projects and re-seeds. Scripts are idempotent (seed_data.py skips if data exists). All 104 tests pass.

---

## Phase 3: Dashboard

**Goal:** Dashboard page shows projects organized by deadline urgency.

### Sprint 3.1: Dashboard Backend
**Estimated Time:** 1 hour  
**Mode:** Ralph-friendly

**Objective:** Service functions and route for dashboard data.

**Tasks:**
- [x] Add to `app/services/project_service.py`:
  - `get_overdue_projects() -> list[Project]` (delivery_deadline < today, status != Completed)
  - `get_due_this_week() -> list[Project]` (delivery_deadline within 7 days, not overdue, status != Completed)
  - `get_longer_deadline() -> list[Project]` (delivery_deadline > 7 days out, status != Completed)
  - `get_recently_completed(limit: int = 10) -> list[Project]`
- [x] Create `app/routes/dashboard.py` with:
  - `GET /` or `GET /dashboard` - renders dashboard template with all four project lists
- [x] Add tests for dashboard service functions

**Acceptance Criteria:**
- Dashboard route returns 200
- Overdue query correctly identifies projects past delivery deadline
- Due this week excludes overdue projects
- Recently completed returns max 10, ordered by updated_at descending
- `pytest` passes for new tests

**Sprint Update:**
> **Completed 2026-01-11** - All tasks completed successfully. Added 4 dashboard service functions to project_service.py: get_overdue_projects, get_due_this_week, get_longer_deadline, and get_recently_completed. Created dashboard.py blueprint with GET / and GET /dashboard routes returning JSON with four project sections. Added 21 new service tests (TestDashboardFunctions) and 8 new route tests (TestDashboardRoute). All 133 tests pass (14 model + 66 service + 53 route). Projects with NULL delivery_deadline are excluded from deadline-based queries.
>
> **Note for Sprint 3.2:** Current routes return JSON. Per SPEC.md HTMX pattern ("Filter/sort operations return HTML fragments, not JSON"), Sprint 3.2 should modify GET / and GET /dashboard to render HTML templates. A separate GET /api/dashboard endpoint has been added to preserve JSON access for testing and potential future API consumers.

---

### Sprint 3.2: Dashboard Frontend
**Estimated Time:** 1.5-2 hours  
**Mode:** Interactive

**Objective:** Build the dashboard UI with four quadrants, visually scannable.

**Tasks:**
- [x] Create `app/templates/base.html` with:
  - HTML5 doctype, meta viewport
  - Bootstrap 5 via CDN
  - HTMX via CDN
  - Navigation bar with links: Dashboard, Projects, New Project, Reports
  - Flash message display area (Bootstrap alerts)
  - Block for page content
- [x] Create `app/templates/dashboard.html`:
  - Four sections using Bootstrap cards: Overdue (red/danger accent), Due This Week (amber/warning), Longer Deadline (neutral/secondary), Recently Completed (green/success muted)
  - Each section shows count in header badge
  - Project cards showing: name, department, assigned attorney, QCP attorney, delivery deadline, status badge
  - Cards link to project detail
  - Empty state messaging for sections with no projects
- [x] Style for visual hierarchy: Overdue draws eye first, clear separation between sections
- [x] Responsive: Bootstrap grid works on tablet-width and up

**Acceptance Criteria:**
- Dashboard loads without errors
- All four sections render with correct projects (verify against seed data)
- Color coding distinguishes urgency levels
- Clicking a project card navigates to detail view (can 404 for now)
- Layout is clean and scannable (human judgment)

**Sprint Update:**
> **Completed 2026-01-11** - All tasks completed successfully. Created base.html with Bootstrap 5.3.3, HTMX 1.9.10 via CDN, dark navbar, and flash message support. Created dashboard.html with four sections (Overdue/danger, Due This Week/warning, Longer Deadline/secondary, Recently Completed/success muted) using Bootstrap cards and grid layout (col-12 col-lg-6). Created reusable partials: _project_card.html for clickable project cards and _status_badge.html for color-coded status badges. Added custom.css for card hover effects. Modified dashboard.py to render HTML templates (GET / and /dashboard) while preserving /api/dashboard JSON endpoint for testing. Updated route tests to handle HTML responses. All 138 tests pass.

---

## Phase 4: Projects Page

**Goal:** Excel-style table with all projects, filtering, sorting, search.

### Sprint 4.1: Projects List Backend
**Estimated Time:** 1 hour  
**Mode:** Ralph-friendly

**Objective:** Enhance routes to support table view with all filter/sort options.

**Tasks:**
- [x] Enhance `GET /projects` route to accept query parameters:
  - `status` (can be comma-separated for multiple)
  - `department`
  - `assigned_attorney`
  - `qcp_attorney`
  - `search` (searches project_name, department, notes, project_group)
  - `sort_by` (field name)
  - `sort_dir` (asc/desc)
  - `include_completed` (boolean, default false)
  - `include_deleted` (boolean, default false) — for potential admin view
- [x] Implement search using PostgreSQL `ilike` for case-insensitivity
- [x] Implement multi-term search: "Smith HR" should match projects where any field contains "Smith" AND any field contains "HR"
- [x] Add route `GET /projects/page` that renders HTML template (vs JSON)
- [x] Add route `GET /projects/table_rows` that returns just table body HTML (for HTMX updates)
- [x] Add tests for new query parameters

**Acceptance Criteria:**
- `GET /projects?include_completed=false` excludes completed
- `GET /projects?search=public+works` finds matching projects (case-insensitive)
- `GET /projects?search=smith+hr` finds projects matching both terms across any fields
- `GET /projects?sort_by=delivery_deadline&sort_dir=asc` sorts correctly
- Multiple filters can be combined
- Soft-deleted projects excluded by default
- All tests pass

**Sprint Update:**
> **Completed 2026-01-12** - All tasks completed successfully. Added multi-term search to get_all_projects() service function using ilike for case-insensitive partial matching across project_name, department, notes, and project_group fields. Multiple search terms are ANDed together. Added search parameter handling to routes. Created two new HTML routes: GET /projects/page (full page with filter controls) and GET /projects/table_rows (HTMX partial for table updates). Created placeholder templates projects.html and partials/project_table_rows.html with basic filter form and table structure. Added 14 new service tests (TestSearchFunctionality) and 21 new route tests (8 search + 13 HTML routes). All 173 tests pass (14 model + 86 service + 73 route).
>
> **Note:** Test count breakdowns in Sprint 2.2 through 3.1 updates contained transposition errors between service and route counts. Totals were always correct; only the per-file breakdowns were swapped.
>
> **Post-review fix:** Removed onclick handler from project_table_rows.html that was navigating to `/projects/<id>` (a JSON endpoint). Clicking table rows would have displayed raw JSON instead of an HTML page. The `data-project-id` attribute is preserved for future use. Clickable rows will be implemented in Sprint 4.3 when the HTML detail page route is added.

---

### Sprint 4.2: Projects Table Frontend
**Estimated Time:** 2 hours  
**Mode:** Interactive

**Objective:** Excel-style table UI with filter controls and sortable columns using HTMX.

**Tasks:**
- [x] Create `app/templates/projects.html`:
  - Filter bar at top with:
    - Status dropdown (multi-select or checkboxes)
    - Search text input
    - Assigned Attorney dropdown (populated from autocomplete)
    - Department dropdown (populated from autocomplete)
    - "Include Completed" checkbox (unchecked by default)
    - Apply/Clear buttons
  - "Export to CSV" button
  - Data table with Bootstrap table styling, columns: ID, Project Name, Project Group, Department, Date Assigned, Assigned Attorney, QCP Attorney, Internal Deadline, Delivery Deadline, Status, Notes (truncated)
  - Clickable column headers for sorting (show sort indicator)
  - Status column with color-coded Bootstrap badges
  - Notes truncated to ~50 chars with "..."
  - Rows clickable to open detail/edit
- [x] Create `app/templates/partials/project_table_rows.html` for HTMX partial updates
- [x] HTMX for dynamic updates:
  - Filter form uses `hx-get="/projects/table_rows"` `hx-target="#table-body"` `hx-trigger="submit"`
  - Column headers use `hx-get` with sort params to update table
  - No custom JavaScript for table rendering—server returns HTML
- [x] Responsive table (Bootstrap `table-responsive` wrapper for horizontal scroll on small screens)

**Acceptance Criteria:**
- Table displays all expected columns
- Filters update the displayed projects via HTMX (no full page reload)
- Sorting works by clicking column headers
- Status badges are color-coded
- Default view excludes Completed projects
- Clicking row opens detail view
- Table updates feel snappy (HTMX swap)

**Sprint Update:**
> **Completed 2026-01-12** - All tasks completed successfully. Completely redesigned projects.html with professional "Legal Precision" styling featuring Libre Baskerville serif headers and Source Sans 3 body text. Implemented comprehensive filter bar with Search, Status, Department, Assigned Attorney, and QCP Attorney dropdowns, plus Include Completed checkbox with Apply/Clear buttons. Added sortable column headers (all except Notes) with visual indicators and sort direction toggle via JavaScript + HTMX. Created custom status badges with semantic colors. Updated project_table_rows.html with clickable rows (visual feedback now, navigation deferred to Sprint 4.3). Added qcp_attorneys to route context. Updated custom.css with table styles and base.html navigation link. All 173 tests pass.
>
> **Design notes:** Used "Legal Precision" aesthetic with deep slate (#1e293b) and warm brass (#b8860b) color scheme appropriate for law firm context. Avoided generic Bootstrap defaults per frontend-design guidance.

---

### Sprint 4.3: Project Detail & Edit Modal
**Estimated Time:** 1.5 hours  
**Mode:** Interactive

**Objective:** View and edit individual projects, including clone and delete.

**Tasks:**
- [ ] Create `app/templates/project_detail.html`:
  - All fields displayed in organized layout (Bootstrap card or grid)
  - Edit button to switch to edit mode (or open modal)
  - Clone button to create new project with same metadata
  - Full notes displayed (not truncated), showing timestamped history
  - Back to Projects link
- [ ] Edit mode or `app/templates/project_edit.html`:
  - Form with all fields pre-populated
  - Status dropdown with all options
  - Notes section: existing notes displayed read-only above, "Add Note" textarea below for appending
  - Save and Cancel buttons
  - Delete button (styled as danger/destructive, Bootstrap btn-outline-danger)
  - Success/error flash messages
- [ ] Create route `GET /projects/<id>/clone` that redirects to New Project form with fields pre-populated (empty dates)
- [ ] Wire up `PUT /projects/<id>` to handle form submission (calls `append_note` service if new note provided)
- [ ] Wire up `DELETE /projects/<id>` with JavaScript confirmation dialog ("Are you sure? This cannot be undone.")
- [ ] Autocomplete on attorney and department fields (calls `/api/autocomplete/<field>`)

**Acceptance Criteria:**
- Detail page shows all project information including full notes history
- Edit form loads with current values
- Adding a note appends with timestamp, doesn't overwrite existing notes
- Saving updates the project and shows success message
- Cancel returns to previous view without saving
- Clone opens new project form with metadata pre-filled, dates empty
- Delete prompts for confirmation, then soft-deletes project and redirects to Projects page
- Autocomplete suggests existing values

**Sprint Update:**
> _[To be completed by Claude Code]_

---

## Phase 5: New Project Form

**Goal:** Clean form for creating new projects.

### Sprint 5.1: New Project Form
**Estimated Time:** 1.5 hours  
**Mode:** Interactive

**Objective:** Build the new project creation form with validation.

**Tasks:**
- [ ] Create `app/templates/project_form.html`:
  - All fields from SPEC (Project Name, Project Group, Department, etc.)
  - Required field indicators
  - Date pickers for date fields
  - Status defaults to "In Progress"
  - Date Assigned defaults to today
  - Autocomplete on Department, Assigned Attorney, QCP Attorney
  - Submit button
  - Client-side validation for required fields
- [ ] Create route `GET /projects/new` - renders form
- [ ] Wire `POST /projects` to handle form submission (already exists from 2.2, may need to handle form data vs JSON)
- [ ] On success: redirect to Projects page with flash message
- [ ] On validation error: re-render form with error messages and preserved input

**Acceptance Criteria:**
- Form renders all fields correctly
- Required fields show validation errors if empty
- Date pickers work
- Autocomplete suggests existing departments/attorneys
- Successful submission creates project and redirects
- Failed submission preserves entered data

**Sprint Update:**
> _[To be completed by Claude Code]_

---

## Phase 6: Reports

**Goal:** Generate weekly status and monthly statistics reports.

### Sprint 6.1: Report Service & CSV Export
**Estimated Time:** 1.5 hours  
**Mode:** Ralph-friendly

**Objective:** Backend logic for report data aggregation and CSV export.

**Tasks:**
- [ ] Create `app/services/report_service.py`:
  - `get_weekly_status_data(fields: list[str]) -> list[dict]`
    - Returns active projects with only requested fields
    - Renames delivery_deadline to "Anticipated Completion"
  - `get_monthly_stats(year: int, month: int) -> dict`
    - projects_opened: count created this month
    - projects_completed: count completed this month
    - by_department: dict of department -> count
    - by_attorney: dict of attorney -> count
    - avg_days_to_completion: average of (date_completed - date_assigned) for completed
  - `export_projects_csv(filters: dict = None) -> str`
    - Returns CSV string of projects matching filters
    - All fields included (notes truncated to 200 chars)
- [ ] Create `app/routes/reports.py` with:
  - `GET /reports` - report builder page
  - `GET /reports/weekly` - generates weekly status HTML
  - `GET /reports/monthly` - generates monthly stats HTML
  - `GET /projects/export` - returns CSV file download
  - Query params for field selection and date range
- [ ] Add tests for report service functions

**Acceptance Criteria:**
- `get_monthly_stats` returns correct counts
- `get_weekly_status_data` filters out completed and excludes unrequested fields
- `GET /projects/export` returns valid CSV with correct Content-Type header
- CSV opens correctly in Excel
- Routes return 200 with correct content type
- Tests pass

**Sprint Update:**
> _[To be completed by Claude Code]_

---

### Sprint 6.2: Report Builder UI
**Estimated Time:** 1.5 hours  
**Mode:** Interactive

**Objective:** Build report configuration UI and output templates.

**Tasks:**
- [ ] Create `app/templates/reports/report_builder.html`:
  - Section for Weekly Status Report:
    - Checkboxes for includable fields (Project Name always included)
    - Preview/Generate button
  - Section for Monthly Stats:
    - Month/Year selector
    - Generate button
  - Section for CSV Export:
    - Filter options matching Projects page
    - Export button
- [ ] Create `app/templates/reports/weekly_status.html`:
  - Clean, printable layout
  - Table with selected columns (Bootstrap table)
  - Header with report title and date generated
  - Professional styling for print/PDF
- [ ] Create `app/templates/reports/monthly_stats.html`:
  - Summary numbers at top (Bootstrap cards)
  - Department breakdown table
  - Attorney breakdown table
  - Clean print styling
- [ ] Add comprehensive `@media print` CSS:
  - Hide navigation, sidebar, and action buttons
  - Force `background-color` and `-webkit-print-color-adjust: exact` so status badges keep colors
  - Ensure tables don't break awkwardly across pages
  - Set appropriate margins for printing

**Acceptance Criteria:**
- Report builder page shows all report options
- Checkboxes correctly control which fields appear in weekly report
- Monthly report shows all statistics
- Reports look professional when printed/saved as PDF
- Status badge colors print correctly (not just borders)
- Date headers are correct

**Sprint Update:**
> _[To be completed by Claude Code]_

---

## Phase 7: Polish & Deployment

**Goal:** Integration testing, UI polish, seed data, deployment-ready.

### Sprint 7.1: Integration Testing
**Estimated Time:** 1.5 hours  
**Mode:** Ralph-friendly

**Objective:** End-to-end tests covering full user workflows.

**Tasks:**
- [ ] Create `tests/test_integration.py`:
  - Test: Create project via form → appears in projects list → edit status → appears in dashboard section
  - Test: Create multiple projects → filter works → sort works
  - Test: Complete project → disappears from default projects view → appears in Recently Completed
  - Test: Generate weekly report → all active projects appear
  - Test: Generate monthly report → stats are accurate
- [ ] Fix any bugs discovered during integration testing
- [ ] Ensure all tests pass: `pytest` with no failures

**Acceptance Criteria:**
- All integration tests pass
- `pytest` runs all tests with 0 failures
- No console errors in browser during manual testing

**Sprint Update:**
> _[To be completed by Claude Code]_

---

### Sprint 7.2: UI Polish & Responsiveness
**Estimated Time:** 1.5 hours  
**Mode:** Interactive

**Objective:** Visual polish, consistent styling, responsive refinements.

**Tasks:**
- [ ] Review all pages for visual consistency:
  - Consistent spacing and margins
  - Consistent button styles
  - Consistent color usage for status badges across pages
  - Consistent typography
- [ ] Add loading states where appropriate
- [ ] Add empty states with helpful messaging (no projects yet, no results for filter)
- [ ] Ensure all forms have proper labels and error states
- [ ] Test at various screen widths (1024px, 768px minimum)
- [ ] Fix any layout issues on smaller screens
- [ ] Add favicon

**Acceptance Criteria:**
- All pages look consistent and professional
- No visual bugs at tablet width and above
- Empty states are helpful, not confusing
- Forms are accessible (labels linked to inputs)

**Sprint Update:**
> _[To be completed by Claude Code]_

---

### Sprint 7.3: Documentation & Deployment Prep
**Estimated Time:** 1 hour  
**Mode:** Ralph-friendly

**Objective:** Final documentation and Railway deployment verification.

**Tasks:**
- [ ] Update README.md with:
  - Project overview and features
  - Local setup instructions (clone, install deps, configure .env, run migrations, seed data)
  - How to run tests
  - How to run seed data scripts
  - Railway deployment instructions
  - Tech stack overview
- [ ] Verify Procfile works: `gunicorn "app:create_app()"`
- [ ] Verify all environment variables documented in `.env.example`
- [ ] Test deployment to Railway:
  - Create Railway project
  - Add PostgreSQL database
  - Set environment variables
  - Deploy and verify app runs
- [ ] Add inline code comments where logic is non-obvious
- [ ] Ensure no hardcoded secrets or debug flags in committed code

**Acceptance Criteria:**
- README provides clear, complete setup instructions
- New developer can clone and run locally following README
- App deploys successfully to Railway
- All environment variables documented
- No secrets in codebase
- Seed data (from Sprint 2.3) demonstrates all dashboard sections when deployed

**Sprint Update:**
> _[To be completed by Claude Code]_

---

## Implementation Notes

### Dependencies Between Sprints

- Phase 2 requires Phase 1 complete
- Sprint 2.3 (Seed Data) should be completed before Phase 3 begins (enables visual testing)
- Phase 3-5 require Sprint 2.2 complete (but can be done in parallel with each other)
- Phase 6 requires Phase 4 complete (needs projects to report on)
- Phase 7 requires all features complete

### Testing Strategy

Tests are written alongside features, not deferred. Each sprint with backend logic includes corresponding tests. Integration tests in Phase 7 catch gaps.

### Definition of Done

A sprint is complete when:
1. All tasks are checked off
2. Acceptance criteria are met
3. Code runs without errors
4. Tests pass (for Ralph-friendly sprints)
5. Sprint Update is filled in with key decisions and notes for future sprints

### Ralph-Wiggum Usage

For sprints marked **Ralph-friendly**, you can invoke automated iteration:

```
/ralph-loop "@IMPLEMENTATION_PLAN.md Implement Sprint 2.1. Run tests after each change. Output <promise>DONE</promise> when all acceptance criteria pass." --max-iterations 20
```

For **Interactive** sprints, work through them with human review, especially for UI decisions.

### Frontend-Design Plugin

For Interactive sprints in Phases 3-5 (UI work), consider activating the frontend-design plugin to ensure polished, professional styling rather than generic Bootstrap defaults.

---

## Environment Variables Reference

```
DATABASE_URL=postgresql://user:pass@host:5432/legal_tracker
SECRET_KEY=your-secret-key-here
DEBUG=true
```

For Railway, set these in the Variables tab. For local development, create `.env` file (not committed to git).
