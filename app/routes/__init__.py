"""Flask blueprints package.

This package contains all route blueprints for the application.
Each blueprint handles a specific area of functionality.
"""
from flask import Flask


def register_blueprints(app: Flask) -> None:
    """Register all application blueprints.

    Called by the app factory to set up all routes.

    Args:
        app: The Flask application instance.
    """
    from app.routes.dashboard import dashboard_bp
    from app.routes.projects import projects_bp

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(projects_bp)
