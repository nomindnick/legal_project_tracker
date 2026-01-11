"""Flask application factory.

This module contains the create_app factory function that initializes
and configures the Flask application.
"""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

from app.config import Config

# Initialize extensions without app context
# These will be initialized with the app in create_app()
db = SQLAlchemy()
migrate = Migrate()


def create_app(config_class: type = Config) -> Flask:
    """Create and configure the Flask application.

    Uses the application factory pattern to allow creating multiple
    app instances with different configurations (e.g., for testing).

    Args:
        config_class: Configuration class to use. Defaults to Config.

    Returns:
        Configured Flask application instance.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)

    # Register blueprints
    # (Will be added in later sprints as routes are created)

    # Simple health check route
    @app.route('/health')
    def health_check():
        return {'status': 'healthy'}

    return app
