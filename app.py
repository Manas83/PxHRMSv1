import os
import logging
from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from extensions import db, login_manager, mail
# DO NOT import routes here yet (avoid circular import)

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///hrms.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Configure mail
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', '587'))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@hrms.com')

# Configure file uploads
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Initialize extensions
db.init_app(app)
login_manager.init_app(app)
mail.init_app(app)

# Now import blueprints (AFTER extensions are initialized)



# Login manager configuration
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))

# Register blueprints
from routes.main import main_bp
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.employee import employee_bp
from routes.manager import manager_bp
from routes.reports import reports_bp
from routes.recruitment import recruitment_bp
from routes.training import training_bp
from routes.exit_management import exit_management_bp
from routes.self_service import self_service_bp
from routes.hr_admin import hr_admin_bp

app.register_blueprint(main_bp)
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(employee_bp, url_prefix='/employee')
app.register_blueprint(manager_bp, url_prefix='/manager')
app.register_blueprint(reports_bp, url_prefix='/reports')
app.register_blueprint(recruitment_bp, url_prefix='/recruitment')
app.register_blueprint(training_bp, url_prefix='/training')
app.register_blueprint(exit_management_bp, url_prefix='/exit')
app.register_blueprint(self_service_bp, url_prefix='/self-service')
app.register_blueprint(hr_admin_bp, url_prefix='/hr-admin')

with app.app_context():
    # Import models to ensure tables are created
    import models
    db.create_all()

    # Create default admin user if none exists
    from models import User
    from werkzeug.security import generate_password_hash

    admin_user = User.query.filter_by(email='admin@hrms.com').first()
    if not admin_user:
        # First ensure we have a default designation
        from models import Designation
        admin_designation = Designation.query.filter_by(name='System Administrator').first()
        if not admin_designation:
            admin_designation = Designation(
                name='System Administrator',
                level=6,
                department='IT',
                description='System Administrator role',
                min_experience_years=0,
                created_by=1  # Will be updated after admin user is created
            )
            db.session.add(admin_designation)
            db.session.flush()  # Get the ID without committing
        
        admin_user = User(
            email='admin@hrms.com',
            employee_id='ADMIN001',
            first_name='System',
            last_name='Administrator',
            role='admin',
            password_hash=generate_password_hash('admin123'),
            active=True,
            department='IT',
            designation_id=admin_designation.id,
            work_mode='onsite'
        )
        db.session.add(admin_user)
        db.session.commit()
        
        # Update the designation's created_by to point to the admin user
        admin_designation.created_by = admin_user.id
        db.session.commit()
        
        logging.info("Default admin user created: admin@hrms.com / admin123")