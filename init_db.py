
#!/usr/bin/env python3
"""
Initialize database with all required tables and default data
"""

from app import create_app
from extensions import db
from models import *
import logging

logging.basicConfig(level=logging.INFO)

def init_database():
    app = create_app()
    
    with app.app_context():
        try:
            # Drop and recreate all tables (use with caution in production)
            print("Creating database tables...")
            db.create_all()
            
            # Create default leave policies if they don't exist
            from create_default_policies import create_default_policies
            create_default_policies()
            
            print("Database initialized successfully!")
            
        except Exception as e:
            print(f"Database initialization failed: {e}")
            raise

if __name__ == '__main__':
    init_database()
