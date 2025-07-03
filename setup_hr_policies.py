
#!/usr/bin/env python3
"""
Setup script for HR policies and designations
Run this after updating the database schema
"""

from app import create_app
from extensions import db
from models import LeavePolicy, Designation, User
from datetime import datetime

def setup_initial_data():
    app = create_app()
    
    with app.app_context():
        print("Setting up initial HR policies and designations...")
        
        # Get admin user for created_by field
        admin_user = User.query.filter_by(role='admin').first()
        if not admin_user:
            print("Error: No admin user found. Please create an admin user first.")
            return
        
        # Create default leave policies for different employee statuses
        leave_policies = [
            # Training period policies
            {'leave_type': 'sick', 'display': 'Sick Leave', 'status': 'training', 'allocation': 6},
            {'leave_type': 'casual', 'display': 'Casual Leave', 'status': 'training', 'allocation': 6},
            {'leave_type': 'earned', 'display': 'Earned Leave', 'status': 'training', 'allocation': 0},
            
            # Probation period policies
            {'leave_type': 'sick', 'display': 'Sick Leave', 'status': 'probation', 'allocation': 8},
            {'leave_type': 'casual', 'display': 'Casual Leave', 'status': 'probation', 'allocation': 8},
            {'leave_type': 'earned', 'display': 'Earned Leave', 'status': 'probation', 'allocation': 10},
            
            # Confirmed employee policies
            {'leave_type': 'sick', 'display': 'Sick Leave', 'status': 'confirmed', 'allocation': 12},
            {'leave_type': 'casual', 'display': 'Casual Leave', 'status': 'confirmed', 'allocation': 12},
            {'leave_type': 'earned', 'display': 'Earned Leave', 'status': 'confirmed', 'allocation': 21},
            {'leave_type': 'optional', 'display': 'Optional Holiday', 'status': 'confirmed', 'allocation': 2},
            {'leave_type': 'maternity', 'display': 'Maternity Leave', 'status': 'confirmed', 'allocation': 180},
            {'leave_type': 'paternity', 'display': 'Paternity Leave', 'status': 'confirmed', 'allocation': 15},
        ]
        
        for policy_data in leave_policies:
            existing = LeavePolicy.query.filter_by(
                leave_type=policy_data['leave_type'],
                employee_status=policy_data['status']
            ).first()
            
            if not existing:
                policy = LeavePolicy(
                    leave_type=policy_data['leave_type'],
                    leave_type_display=policy_data['display'],
                    employee_status=policy_data['status'],
                    annual_allocation=policy_data['allocation'],
                    max_encashable=policy_data['allocation'] // 2 if policy_data['leave_type'] == 'earned' else 0,
                    carry_forward_limit=5 if policy_data['leave_type'] == 'earned' else 0,
                    requires_approval=True,
                    min_notice_days=1 if policy_data['leave_type'] in ['sick'] else 3,
                    max_consecutive_days=30 if policy_data['leave_type'] in ['maternity', 'paternity'] else 10,
                    created_by=admin_user.id
                )
                db.session.add(policy)
                print(f"Added leave policy: {policy_data['display']} for {policy_data['status']} employees")
        
        # Create default designations
        designations = [
            # IT Department
            {'name': 'Software Developer Intern', 'level': 1, 'dept': 'IT', 'min_exp': 0, 'max_exp': 1},
            {'name': 'Junior Software Developer', 'level': 2, 'dept': 'IT', 'min_exp': 0, 'max_exp': 2},
            {'name': 'Software Developer', 'level': 3, 'dept': 'IT', 'min_exp': 2, 'max_exp': 5},
            {'name': 'Senior Software Developer', 'level': 4, 'dept': 'IT', 'min_exp': 5, 'max_exp': 8},
            {'name': 'Tech Lead', 'level': 5, 'dept': 'IT', 'min_exp': 6, 'max_exp': None},
            {'name': 'Engineering Manager', 'level': 6, 'dept': 'IT', 'min_exp': 8, 'max_exp': None},
            
            # HR Department
            {'name': 'HR Intern', 'level': 1, 'dept': 'HR', 'min_exp': 0, 'max_exp': 1},
            {'name': 'HR Executive', 'level': 2, 'dept': 'HR', 'min_exp': 0, 'max_exp': 3},
            {'name': 'Senior HR Executive', 'level': 3, 'dept': 'HR', 'min_exp': 3, 'max_exp': 6},
            {'name': 'HR Manager', 'level': 5, 'dept': 'HR', 'min_exp': 5, 'max_exp': None},
            
            # Finance Department
            {'name': 'Finance Trainee', 'level': 1, 'dept': 'Finance', 'min_exp': 0, 'max_exp': 1},
            {'name': 'Accounts Executive', 'level': 2, 'dept': 'Finance', 'min_exp': 1, 'max_exp': 3},
            {'name': 'Finance Analyst', 'level': 3, 'dept': 'Finance', 'min_exp': 2, 'max_exp': 5},
            {'name': 'Finance Manager', 'level': 5, 'dept': 'Finance', 'min_exp': 5, 'max_exp': None},
        ]
        
        for des_data in designations:
            existing = Designation.query.filter_by(name=des_data['name']).first()
            if not existing:
                designation = Designation(
                    name=des_data['name'],
                    level=des_data['level'],
                    department=des_data['dept'],
                    description=f"{des_data['name']} in {des_data['dept']} department",
                    min_experience_years=des_data['min_exp'],
                    max_experience_years=des_data['max_exp'],
                    created_by=admin_user.id
                )
                db.session.add(designation)
                print(f"Added designation: {des_data['name']}")
        
        try:
            db.session.commit()
            print("Successfully set up initial HR policies and designations!")
        except Exception as e:
            db.session.rollback()
            print(f"Error setting up initial data: {e}")

if __name__ == "__main__":
    setup_initial_data()

