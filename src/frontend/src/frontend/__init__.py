"""
DevOps Study Timer Frontend

A Flask web application for tracking study time for DevOps certifications.
"""

# Import and expose main functions and app
from .main import app, create_session, get_sessions

# Define public API
__all__ = ["app", "create_session", "get_sessions"]
