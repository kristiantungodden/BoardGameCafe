#!/usr/bin/env python
"""
Application entry point.

Run with:
    python run.py
    
or with Flask CLI:
    flask run
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "boardgame_cafe", "src"))

from app import create_app, db

app = create_app()


@app.shell_context_processor
def make_shell_context():
    """Add database and models to Flask shell."""
    return {"db": db}


if __name__ == "__main__":
    app.run(
        host=os.getenv("FLASK_HOST", "127.0.0.1"),
        port=int(os.getenv("FLASK_PORT", 5000)),
        debug=os.getenv("FLASK_ENV") == "development"
    )
