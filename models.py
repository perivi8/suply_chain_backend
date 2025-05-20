from database import db
from datetime import datetime

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(15), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)

class RawMaterial(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    material_type = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    source_location = db.Column(db.String(100), nullable=False)
    supply_date = db.Column(db.Date, nullable=False)
    user = db.relationship('User', backref='raw_materials')

class Medicine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    raw_material_id = db.Column(db.Integer, db.ForeignKey('raw_material.id'), nullable=False)
    medicine_name = db.Column(db.String(100), nullable=False)
    batch_number = db.Column(db.String(50), nullable=False)
    production_date = db.Column(db.Date, nullable=False)
    expiry_date = db.Column(db.Date, nullable=False)
    user = db.relationship('User', backref='medicines')
    raw_material = db.relationship('RawMaterial', backref='medicines')

class Distribution(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    medicine_id = db.Column(db.Integer, db.ForeignKey('medicine.id'), nullable=False)
    shipment_date = db.Column(db.Date, nullable=False)
    transport_method = db.Column(db.String(100), nullable=False)
    destination = db.Column(db.String(100), nullable=False)
    storage_condition = db.Column(db.String(100), nullable=False)
    user = db.relationship('User', backref='distributions')
    medicine = db.relationship('Medicine', backref='distributions')

class RetailSale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    distribution_id = db.Column(db.Integer, db.ForeignKey('distribution.id'), nullable=False)
    received_date = db.Column(db.Date, nullable=False)
    price = db.Column(db.Float, nullable=False)
    retail_location = db.Column(db.String(100), nullable=False)
    qr_code = db.Column(db.Text, nullable=True)  # Only RetailSale has qr_code
    user = db.relationship('User', backref='retail_sales')
    distribution = db.relationship('Distribution', backref='retail_sales')