#!/usr/bin/env python3
"""
Script to create test users with different roles for testing role-based access control
"""

from app import app
from models import User
from extensions import db
from werkzeug.security import generate_password_hash

def create_test_users():
    with app.app_context():
        # Check if users already exist
        if User.query.count() > 0:
            print("Users already exist. Skipping user creation.")
            return
        
        # Create admin user
        admin = User(
            email='admin@company.com',
            employee_id='EMP001',
            first_name='Admin',
            last_name='User',
            phone='1234567890',
            department='IT',
            designation='System Administrator',
            work_mode='onsite',
            role='admin',
            password_hash=generate_password_hash('admin123'),
            active=True
        )
        
        # Create HR user
        hr_user = User(
            email='hr@company.com',
            employee_id='EMP002',
            first_name='HR',
            last_name='Manager',
            phone='1234567891',
            department='HR',
            designation='HR Manager',
            work_mode='onsite',
            role='hr',
            password_hash=generate_password_hash('hr123'),
            active=True
        )
        
        # Create manager user
        manager = User(
            email='manager@company.com',
            employee_id='EMP003',
            first_name='Team',
            last_name='Manager',
            phone='1234567892',
            department='IT',
            designation='Team Lead',
            work_mode='onsite',
            role='manager',
            password_hash=generate_password_hash('manager123'),
            active=True
        )
        
        # Create employee user
        employee = User(
            email='employee@company.com',
            employee_id='EMP004',
            first_name='John',
            last_name='Doe',
            phone='1234567893',
            department='IT',
            designation='Software Developer',
            work_mode='onsite',
            role='employee',
            manager_id=None,  # Will be set after manager is created
            password_hash=generate_password_hash('employee123'),
            active=True
        )
        
        try:
            # Add all users
            db.session.add(admin)
            db.session.add(hr_user)
            db.session.add(manager)
            db.session.commit()
            
            # Set manager relationship
            employee.manager_id = manager.id
            db.session.add(employee)
            db.session.commit()
            
            print("Test users created successfully!")
            print("\nLogin credentials:")
            print("Admin: admin@company.com / admin123")
            print("HR: hr@company.com / hr123")
            print("Manager: manager@company.com / manager123")
            print("Employee: employee@company.com / employee123")
            
        except Exception as e:
            db.session.rollback()
            print(f"Error creating users: {e}")

if __name__ == '__main__':
    create_test_users()