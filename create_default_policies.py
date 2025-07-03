#!/usr/bin/env python3
"""
Script to create default leave policies for the HRMS system
"""

from app import app, db
from models import LeavePolicy, User

def create_default_policies():
    """Create default leave policies for probation and confirmed employees"""
    
    with app.app_context():
        # Get admin user to set as creator
        admin_user = User.query.filter_by(role='admin').first()
        admin_id = admin_user.id if admin_user else None
        
        # Default policies for Probation employees
        probation_policies = [
            {
                'leave_type': 'sick',
                'leave_type_display_name': 'Sick Leave',
                'employment_status': 'probation',
                'annual_allocation': 6,  # Reduced for probation
                'max_encashable': 0,
                'carry_forward_limit': 2,
                'min_service_months': 0
            },
            {
                'leave_type': 'casual',
                'leave_type_display_name': 'Casual Leave',
                'employment_status': 'probation',
                'annual_allocation': 8,  # Reduced for probation
                'max_encashable': 0,
                'carry_forward_limit': 3,
                'min_service_months': 3  # Must complete 3 months
            }
        ]
        
        # Default policies for Confirmed employees
        confirmed_policies = [
            {
                'leave_type': 'sick',
                'leave_type_display_name': 'Sick Leave',
                'employment_status': 'confirmed',
                'annual_allocation': 12,
                'max_encashable': 5,
                'carry_forward_limit': 5,
                'min_service_months': 0
            },
            {
                'leave_type': 'casual',
                'leave_type_display_name': 'Casual Leave',
                'employment_status': 'confirmed',
                'annual_allocation': 18,
                'max_encashable': 10,
                'carry_forward_limit': 8,
                'min_service_months': 0
            },
            {
                'leave_type': 'earned',
                'leave_type_display_name': 'Earned Leave',
                'employment_status': 'confirmed',
                'annual_allocation': 24,
                'max_encashable': 15,
                'carry_forward_limit': 12,
                'min_service_months': 12  # Must complete 1 year
            },
            {
                'leave_type': 'optional',
                'leave_type_display_name': 'Optional Holiday',
                'employment_status': 'confirmed',
                'annual_allocation': 2,
                'max_encashable': 0,
                'carry_forward_limit': 0,
                'min_service_months': 6
            }
        ]
        
        # Universal policies (for all employees)
        universal_policies = [
            {
                'leave_type': 'emergency',
                'leave_type_display_name': 'Emergency Leave',
                'employment_status': 'all',
                'annual_allocation': 3,
                'max_encashable': 0,
                'carry_forward_limit': 0,
                'min_service_months': 0
            }
        ]
        
        all_policies = probation_policies + confirmed_policies + universal_policies
        
        created_count = 0
        updated_count = 0
        
        for policy_data in all_policies:
            # Check if policy already exists
            existing_policy = LeavePolicy.query.filter_by(
                leave_type=policy_data['leave_type'],
                employment_status=policy_data['employment_status']
            ).first()
            
            if existing_policy:
                # Update existing policy
                for key, value in policy_data.items():
                    setattr(existing_policy, key, value)
                existing_policy.created_by = admin_id
                updated_count += 1
                print(f"Updated: {policy_data['leave_type_display_name']} for {policy_data['employment_status']}")
            else:
                # Create new policy
                policy = LeavePolicy(
                    created_by=admin_id,
                    **policy_data
                )
                db.session.add(policy)
                created_count += 1
                print(f"Created: {policy_data['leave_type_display_name']} for {policy_data['employment_status']}")
        
        try:
            db.session.commit()
            print(f"\nSuccess! Created {created_count} new policies, updated {updated_count} existing policies.")
            print("\nDefault leave policies have been set up:")
            print("• Probation employees: Limited sick and casual leave")
            print("• Confirmed employees: Full leave benefits including earned leave")
            print("• Emergency leave: Available to all employees")
            
        except Exception as e:
            db.session.rollback()
            print(f"Error creating policies: {str(e)}")
            return False
        
        return True

if __name__ == '__main__':
    success = create_default_policies()
    if success:
        print("\n✓ Default leave policies created successfully!")
    else:
        print("\n✗ Failed to create default leave policies.")