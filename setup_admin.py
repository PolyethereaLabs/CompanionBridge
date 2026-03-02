#!/usr/bin/env python3
"""
Setup script for creating admin user and testing analytics functionality
"""
import os
import sys
from datetime import datetime

# Add the current directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import AdminUser, ProcessingSession

def setup_admin_user():
    """Create the admin user if it doesn't exist"""
    with app.app_context():
        # Check if admin user exists
        admin = AdminUser.query.filter_by(username='admin').first()
        if not admin:
            admin = AdminUser()
            admin.username = 'admin'
            admin.set_password('companion2025')
            db.session.add(admin)
            db.session.commit()
            print("✓ Created admin user: admin/companion2025")
        else:
            print("✓ Admin user already exists")

def create_sample_data():
    """Create some sample processing sessions for analytics testing"""
    with app.app_context():
        # Create a few sample sessions if none exist
        if ProcessingSession.query.count() == 0:
            sessions = [
                {
                    'session_id': 'sample001',
                    'chat_filename': 'sample1.json',
                    'status': 'completed',
                    'user_name': 'John',
                    'companion_name': 'ChatGPT',
                    'total_conversations': 15,
                    'total_messages': 250,
                    'file_size': 2048000,  # 2MB
                    'processing_time': 12.5,
                    'memory_anchors_found': 8,
                    'full_downloaded': True,
                    'condensed_downloaded': False
                },
                {
                    'session_id': 'sample002', 
                    'chat_filename': 'sample2.json',
                    'status': 'completed',
                    'user_name': 'Sarah',
                    'companion_name': 'Claude',
                    'total_conversations': 8,
                    'total_messages': 120,
                    'file_size': 1024000,  # 1MB
                    'processing_time': 8.2,
                    'memory_anchors_found': 5,
                    'full_downloaded': False,
                    'condensed_downloaded': True
                },
                {
                    'session_id': 'sample003',
                    'chat_filename': 'sample3.json', 
                    'status': 'error',
                    'user_name': 'Mike',
                    'companion_name': 'Assistant',
                    'total_conversations': 0,
                    'total_messages': 0,
                    'file_size': 5120000,  # 5MB
                    'processing_time': 0.0,
                    'memory_anchors_found': 0,
                    'error_message': 'Invalid JSON format'
                }
            ]
            
            for session_data in sessions:
                session = ProcessingSession()
                for key, value in session_data.items():
                    setattr(session, key, value)
                db.session.add(session)
            
            db.session.commit()
            print(f"✓ Created {len(sessions)} sample processing sessions")
        else:
            print(f"✓ Found {ProcessingSession.query.count()} existing sessions")

if __name__ == '__main__':
    print("Setting up CompanionBridge Analytics...")
    setup_admin_user()
    create_sample_data()
    print("\n🎉 Setup complete!")
    print("\nAdmin Dashboard URLs:")
    print("Login: /admin-access-portal")
    print("Dashboard: /admin-dashboard-analytics")
    print("\nDefault credentials: admin / companion2025")