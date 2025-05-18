from database import db
from datetime import datetime

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(50), nullable=False)

class RawMaterial(db.Model):
    __tablename__ = 'raw_materials'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    material_type = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    source_location = db.Column(db.String(200), nullable=False)
    supply_date = db.Column(db.DateTime, nullable=False)
    qr_code = db.Column(db.Text)  # Store base64 QR code
    user = db.relationship('User', backref='raw_materials')

class Medicine(db.Model):
    __tablename__ = 'medicines'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    raw_material_id = db.Column(db.Integer, db.ForeignKey('raw_materials.id'), nullable=False)
    medicine_name = db.Column(db.String(100), nullable=False)
    batch_number = db.Column(db.String(50), nullable=False)
    production_date = db.Column(db.DateTime, nullable=False)
    expiry_date = db.Column(db.DateTime, nullable=False)
    qr_code = db.Column(db.Text)  # Store base64 QR code
    user = db.relationship('User', backref='medicines')
    raw_material = db.relationship('RawMaterial', backref='medicines')

class Distribution(db.Model):
    __tablename__ = 'distributions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    medicine_id = db.Column(db.Integer, db.ForeignKey('medicines.id'), nullable=False)
    shipment_date = db.Column(db.DateTime, nullable=False)
    transport_method = db.Column(db.String(100), nullable=False)
    destination = db.Column(db.String(200), nullable=False)
    storage_condition = db.Column(db.String(200), nullable=False)
    qr_code = db.Column(db.Text)  # Store base64 QR code
    user = db.relationship('User', backref='distributions')
    medicine = db.relationship('Medicine', backref='distributions')

class RetailSale(db.Model):
    __tablename__ = 'retail_sales'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    distribution_id = db.Column(db.Integer, db.ForeignKey('distributions.id'), nullable=False)
    received_date = db.Column(db.DateTime, nullable=False)
    price = db.Column(db.Float, nullable=False)
    retail_location = db.Column(db.String(200), nullable=False)
    qr_code = db.Column(db.Text)  # Store base64 QR code
    user = db.relationship('User', backref='retail_sales')
    distribution = db.relationship('Distribution', backref='retail_sales')