import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "companion-bridge-secret-key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure upload settings
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['RESULT_FOLDER'] = 'results'

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///companion_bridge.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}




# Initialize the app with the extension
db.init_app(app)

# Create upload and result directories
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['RESULT_FOLDER'], exist_ok=True)

with app.app_context():
    # Import models and routes
    import models
    import routes
    
    db.create_all()
    
    # Create default admin user if none exists
    from models import AdminUser
    if AdminUser.query.count() == 0:
        admin_password = os.environ.get("ADMIN_PASSWORD")
        if not admin_password:
            raise RuntimeError(
                "ADMIN_PASSWORD environment variable is not set. "
                "Please set it before starting the application."
            )
        admin = AdminUser()
        admin.username = 'admin'
        admin.set_password(admin_password)
        db.session.add(admin)
        db.session.commit()
        print("Created default admin user: admin")
