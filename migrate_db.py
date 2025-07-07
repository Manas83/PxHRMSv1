
#!/usr/bin/env python3
"""
Database migration script to create missing ATS tables and columns
"""

from app import create_app
from extensions import db
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)

def migrate_database():
    app = create_app()
    
    with app.app_context():
        try:
            # Create all tables first
            db.create_all()
            logging.info("Created all tables")
            
            # Check if job_applications table exists and has all required columns
            result = db.session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'job_applications' 
                AND table_schema = 'public'
            """))
            
            existing_columns = [row[0] for row in result.fetchall()]
            logging.info(f"Existing columns in job_applications: {existing_columns}")
            
            # Required columns for job_applications table
            required_columns = {
                'candidate_linkedin': 'VARCHAR(200)',
                'candidate_portfolio': 'VARCHAR(200)', 
                'current_company': 'VARCHAR(100)',
                'current_designation': 'VARCHAR(100)',
                'experience_years': 'INTEGER',
                'current_salary': 'FLOAT',
                'expected_salary': 'FLOAT',
                'notice_period': 'INTEGER',
                'stage': 'VARCHAR(50) DEFAULT \'application_review\'',
                'priority': 'VARCHAR(20) DEFAULT \'medium\'',
                'source': 'VARCHAR(50) DEFAULT \'website\'',
                'referral_by': 'INTEGER REFERENCES users(id)',
                'last_activity_date': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
                'notes': 'TEXT',
                'internal_notes': 'TEXT',
                'resume_score': 'FLOAT',
                'skills_matched': 'TEXT',
                'overall_rating': 'FLOAT',
                'is_archived': 'BOOLEAN DEFAULT FALSE',
                'rejection_reason': 'VARCHAR(200)'
            }
            
            # Add missing columns
            for column, column_def in required_columns.items():
                if column not in existing_columns:
                    try:
                        db.session.execute(text(f"""
                            ALTER TABLE job_applications 
                            ADD COLUMN {column} {column_def}
                        """))
                        logging.info(f"Added column {column} to job_applications")
                    except Exception as e:
                        logging.warning(f"Could not add column {column}: {e}")
            
            # Update existing records to have proper defaults
            db.session.execute(text("""
                UPDATE job_applications 
                SET stage = 'application_review' 
                WHERE stage IS NULL
            """))
            
            db.session.execute(text("""
                UPDATE job_applications 
                SET priority = 'medium' 
                WHERE priority IS NULL
            """))
            
            db.session.execute(text("""
                UPDATE job_applications 
                SET source = 'website' 
                WHERE source IS NULL
            """))
            
            db.session.execute(text("""
                UPDATE job_applications 
                SET is_archived = FALSE 
                WHERE is_archived IS NULL
            """))
            
            db.session.execute(text("""
                UPDATE job_applications 
                SET last_activity_date = applied_date 
                WHERE last_activity_date IS NULL
            """))
            
            db.session.commit()
            logging.info("Database migration completed successfully!")
            
        except Exception as e:
            db.session.rollback()
            logging.error(f"Migration failed: {e}")
            raise

if __name__ == '__main__':
    migrate_database()
