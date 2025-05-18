from flask_sqlalchemy import SQLAlchemy
import logging

db = SQLAlchemy()
logger = logging.getLogger(__name__)

def init_db(app):
    db.init_app(app)
    with app.app_context():
        db.create_all()
        logger.info("Database tables created or already exist")