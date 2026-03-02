from app import db
from datetime import datetime
from sqlalchemy import Index
from werkzeug.security import generate_password_hash, check_password_hash

class ProcessingSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(64), unique=True, nullable=False)
    chat_filename = db.Column(db.String(255))
    conversations_filename = db.Column(db.String(255))
    status = db.Column(db.String(50), default='pending')
    result_filename = db.Column(db.String(255))
    user_name = db.Column(db.String(100))  # User's actual name
    companion_name = db.Column(db.String(100))  # Companion's actual name
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    error_message = db.Column(db.Text)
    
    # Processing statistics
    total_conversations = db.Column(db.Integer, default=0)
    total_messages = db.Column(db.Integer, default=0)
    traits_extracted = db.Column(db.Integer, default=0)
    memories_indexed = db.Column(db.Integer, default=0)
    file_size = db.Column(db.Integer, default=0)
    processing_time = db.Column(db.Float, default=0.0)
    selected_conversations = db.Column(db.Integer, default=0)
    memory_anchors_found = db.Column(db.Integer, default=0)
    full_downloaded = db.Column(db.Boolean, default=False)
    condensed_downloaded = db.Column(db.Boolean, default=False)
    
    __table_args__ = (
        Index('idx_created_at', 'created_at'),
        Index('idx_status', 'status'),
    )


class AnalyticsMetric(db.Model):
    __tablename__ = 'analytics_metrics'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(64), db.ForeignKey('processing_session.session_id'), nullable=False)
    metric_name = db.Column(db.String(100), nullable=False)  # 'download_full', 'download_condensed', 'session_view', etc.
    metric_value = db.Column(db.String(500))  # JSON data or simple values
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_metric_name', 'metric_name'),
        Index('idx_session_id', 'session_id'),
        Index('idx_analytics_created_at', 'created_at'),
    )


class AdminUser(db.Model):
    __tablename__ = 'admin_users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
