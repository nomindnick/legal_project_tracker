# Legal Project Tracker

A web-based project management system for law firms tracking legal work on large client engagements. Replaces spreadsheet-based tracking with a purpose-built application featuring a dashboard for deadline visibility, an Excel-style project list for daily management, and automated report generation for client communication.

## Features

- **Dashboard**: At-a-glance view of overdue, due soon, and upcoming projects
- **Projects Page**: Excel-style table with filtering, sorting, and search
- **New Project Form**: Clean form for project entry with autocomplete
- **Reports**: Weekly status and monthly statistics reports
- **CSV Export**: Export project data for use in Excel

## Tech Stack

- **Backend**: Python 3.11+, Flask, SQLAlchemy
- **Database**: PostgreSQL (Railway), SQLite for local development
- **Frontend**: Jinja2 templates, Bootstrap 5, HTMX
- **Deployment**: Railway with Gunicorn

## Local Development Setup

### Prerequisites

- Python 3.11 or higher
- pip (Python package manager)
- PostgreSQL (optional, SQLite works for development)

### Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd legal_project_tracker
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file based on `.env.example`:
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

5. Run database migrations:
   ```bash
   flask db upgrade
   ```

6. (Optional) Seed the database with test data:
   ```bash
   python scripts/seed_data.py
   ```

   To reset the database and re-seed (clears all data):
   ```bash
   python scripts/reset_db.py
   ```

7. Run the development server:
   ```bash
   flask run
   ```

   The application will be available at http://localhost:5000

## Running Tests

```bash
pytest
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection URL | SQLite (local file) |
| `SECRET_KEY` | Flask session secret key | Dev key (change in production) |
| `DEBUG` | Enable debug mode | false |

## Deployment

This application is configured for deployment on Railway:

1. Create a new Railway project
2. Add a PostgreSQL database
3. Set environment variables in Railway dashboard
4. Deploy from GitHub

The `Procfile` is configured to use Gunicorn as the production server.

## Project Structure

```
legal_project_tracker/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── config.py            # Configuration
│   ├── models/              # SQLAlchemy models
│   ├── routes/              # Flask blueprints
│   ├── services/            # Business logic
│   ├── templates/           # Jinja2 templates
│   └── static/              # CSS/JS assets
├── tests/                   # pytest tests
├── migrations/              # Alembic migrations
├── scripts/                 # Utility scripts
├── requirements.txt
├── Procfile
└── README.md
```

## License

Proprietary - All rights reserved.
