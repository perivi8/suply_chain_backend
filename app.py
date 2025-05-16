from flask import Flask, request, jsonify
from flask_cors import CORS
from models import db, User, RawMaterial, Medicine, Distribution, RetailSale
from database import init_db
import qrcode
import os
from datetime import datetime
import base64
from io import BytesIO

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///supply_chain.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
CORS(app)

init_db(app)

# Ensure QR code directories exist
QR_CODE_DIR = os.path.join(os.getcwd(), 'qr_code')
QR_CODE_FARMER_DIR = os.path.join(QR_CODE_DIR, 'farmer')
QR_CODE_MANUFACTURER_DIR = os.path.join(QR_CODE_DIR, 'manufacturer')
QR_CODE_DISTRIBUTOR_DIR = os.path.join(QR_CODE_DIR, 'distributor')
QR_CODE_RETAILER_DIR = os.path.join(QR_CODE_DIR, 'retailer')
os.makedirs(QR_CODE_FARMER_DIR, exist_ok=True)
os.makedirs(QR_CODE_MANUFACTURER_DIR, exist_ok=True)
os.makedirs(QR_CODE_DISTRIBUTOR_DIR, exist_ok=True)
os.makedirs(QR_CODE_RETAILER_DIR, exist_ok=True)

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    
    # Define required credentials for each role
    required_credentials = {
        'Manufacturer': {
            'first_name': 'manufacturer',
            'last_name': 'manufacturer',
            'email': 'manufacturer@gmail.com',
            'phone': '2222222222',
            'password': 'manufacturer',
            'confirm_password': 'manufacturer'
        },
        'Distributor': {
            'first_name': 'distributor',
            'last_name': 'distributor',
            'email': 'distributor@gmail.com',
            'phone': '3333333333',
            'password': 'distributor',
            'confirm_password': 'distributor'
        },
        'Retailer': {
            'first_name': 'retailer',
            'last_name': 'retailer',
            'email': 'retailer@gmail.com',
            'phone': '4444444444',
            'password': 'retailer',
            'confirm_password': 'retailer'
        }
    }

    role = data.get('role')
    if role in required_credentials:
        # Validate credentials for Manufacturer, Distributor, Retailer
        expected = required_credentials[role]
        if (
            data.get('first_name') != expected['first_name'] or
            data.get('last_name') != expected['last_name'] or
            data.get('email') != expected['email'] or
            data.get('phone') != expected['phone'] or
            data.get('password') != expected['password'] or
            data.get('confirm_password') != expected['confirm_password'] or
            data.get('password') != data.get('confirm_password')
        ):
            return jsonify({'error': f'Invalid credentials for {role}. Please use the specified credentials.'}), 400

    # Check for existing email
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already exists'}), 400
    
    # Register user
    user = User(
        first_name=data['first_name'],
        last_name=data['last_name'],
        email=data['email'],
        phone=data['phone'],
        password=data['password'],
        role=data['role']
    )
    db.session.add(user)
    db.session.commit()
    return jsonify({'message': 'User registered successfully'})

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter((User.email == data['identifier']) | (User.phone == data['identifier'])).first()
    if user and user.password == data['password']:
        return jsonify({
            'id': user.id,
            'first_name': user.first_name,
            'role': user.role
        })
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/manufacturer', methods=['GET'])
def check_manufacturer():
    data = request.get_json()
    user = User.query.filter_by(id=data['user_id']).first()
    if user and user.role == 'Manufacturer':
        expected = {
            'first_name': 'manufacturer',
            'last_name': 'manufacturer',
            'email': 'manufacturer@gmail.com',
            'phone': '2222222222'
        }
        if (
            user.first_name == expected['first_name'] and
            user.last_name == expected['last_name'] and
            user.email == expected['email'] and
            user.phone == expected['phone']
        ):
            return jsonify({'message': 'Access granted'})
        return jsonify({'error': 'Unauthorized: Invalid Manufacturer credentials'}), 403
    return jsonify({'error': 'Unauthorized: Not a Manufacturer'}), 403

@app.route('/distributor', methods=['GET'])
def check_distributor():
    data = request.get_json()
    user = User.query.filter_by(id=data['user_id']).first()
    if user and user.role == 'Distributor':
        expected = {
            'first_name': 'distributor',
            'last_name': 'distributor',
            'email': 'distributor@gmail.com',
            'phone': '3333333333'
        }
        if (
            user.first_name == expected['first_name'] and
            user.last_name == expected['last_name'] and
            user.email == expected['email'] and
            user.phone == expected['phone']
        ):
            return jsonify({'message': 'Access granted'})
        return jsonify({'error': 'Unauthorized: Invalid Distributor credentials'}), 403
    return jsonify({'error': 'Unauthorized: Not a Distributor'}), 403

@app.route('/retailer', methods=['GET'])
def check_retailer():
    data = request.get_json()
    user = User.query.filter_by(id=data['user_id']).first()
    if user and user.role == 'Retailer':
        expected = {
            'first_name': 'retailer',
            'last_name': 'retailer',
            'email': 'retailer@gmail.com',
            'phone': '4444444444'
        }
        if (
            user.first_name == expected['first_name'] and
            user.last_name == expected['last_name'] and
            user.email == expected['email'] and
            user.phone == expected['phone']
        ):
            return jsonify({'message': 'Access granted'})
        return jsonify({'error': 'Unauthorized: Invalid Retailer credentials'}), 403
    return jsonify({'error': 'Unauthorized: Not a Retailer'}), 403

@app.route('/raw_material', methods=['POST'])
def add_raw_material():
    data = request.get_json()
    raw_material = RawMaterial(
        user_id=data['user_id'],
        material_type=data['material_type'],
        quantity=data['quantity'],
        source_location=data['source_location'],
        supply_date=datetime.strptime(data['supply_date'], '%Y-%m-%d')
    )
    db.session.add(raw_material)
    db.session.commit()
    
    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(f"http://localhost:4200/consumer/{raw_material.id}")
    qr.make(fit=True)
    img = qr.make_image(fill='black', back_color='white')
    
    # Save QR code
    qr_path = os.path.join(QR_CODE_FARMER_DIR, f"raw_material_{raw_material.id}.png")
    img.save(qr_path)
    
    # Convert to base64 for response
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    
    return jsonify({
        'id': raw_material.id,
        'message': 'Raw material added successfully',
        'qr_code': f"data:image/png;base64,{img_str}"
    })

@app.route('/raw_materials', methods=['GET'])
def get_raw_materials():
    # Get raw materials not used in any Medicine
    used_raw_material_ids = db.session.query(Medicine.raw_material_id).distinct().subquery()
    materials = RawMaterial.query.filter(~RawMaterial.id.in_(used_raw_material_ids)).all()
    return jsonify([{
        'id': m.id,
        'material_type': m.material_type,
        'quantity': m.quantity
    } for m in materials])

@app.route('/medicines', methods=['GET'])
def get_medicines():
    # Get medicines not used in any Distribution
    used_medicine_ids = db.session.query(Distribution.medicine_id).distinct().subquery()
    medicines = Medicine.query.filter(~Medicine.id.in_(used_medicine_ids)).all()
    return jsonify([{
        'id': m.id,
        'medicine_name': m.medicine_name,
        'batch_number': m.batch_number
    } for m in medicines])

@app.route('/medicine', methods=['POST'])
def add_medicine():
    data = request.get_json()
    medicine = Medicine(
        user_id=data['user_id'],
        raw_material_id=data['raw_material_id'],
        medicine_name=data['medicine_name'],
        batch_number=data['batch_number'],
        production_date=datetime.strptime(data['production_date'], '%Y-%m-%d'),
        expiry_date=datetime.strptime(data['expiry_date'], '%Y-%m-%d')
    )
    db.session.add(medicine)
    db.session.commit()
    
    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(f"http://localhost:4200/consumer/{medicine.id}")
    qr.make(fit=True)
    img = qr.make_image(fill='black', back_color='white')
    
    # Save QR code to both locations
    qr_path = os.path.join(QR_CODE_DIR, f"medicine_{medicine.id}.png")
    qr_path_manufacturer = os.path.join(QR_CODE_MANUFACTURER_DIR, f"medicine_{medicine.id}.png")
    img.save(qr_path)
    img.save(qr_path_manufacturer)
    
    # Convert to base64 for response
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    
    return jsonify({
        'id': medicine.id,
        'message': 'Medicine added successfully',
        'qr_code': f"data:image/png;base64,{img_str}"
    })

@app.route('/distributions', methods=['GET'])
def get_distributions():
    # Get distributions not used in any RetailSale
    used_distribution_ids = db.session.query(RetailSale.distribution_id).distinct().subquery()
    distributions = Distribution.query.filter(~Distribution.id.in_(used_distribution_ids)).all()
    return jsonify([{
        'id': d.id,
        'medicine_id': d.medicine_id,
        'destination': d.destination,
        'shipment_date': d.shipment_date.strftime('%Y-%m-%d')
    } for d in distributions])

@app.route('/distribution', methods=['POST'])
def add_distribution():
    data = request.get_json()
    distribution = Distribution(
        user_id=data['user_id'],
        medicine_id=data['medicine_id'],
        shipment_date=datetime.strptime(data['shipment_date'], '%Y-%m-%d'),
        transport_method=data['transport_method'],
        destination=data['destination'],
        storage_condition=data['storage_condition']
    )
    db.session.add(distribution)
    db.session.commit()
    
    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(f"http://localhost:4200/consumer/{distribution.medicine_id}")
    qr.make(fit=True)
    img = qr.make_image(fill='black', back_color='white')
    
    # Save QR code
    qr_path = os.path.join(QR_CODE_DISTRIBUTOR_DIR, f"medicine_{distribution.medicine_id}.png")
    img.save(qr_path)
    
    # Convert to base64 for response
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    
    return jsonify({
        'id': distribution.id,
        'message': 'Distribution added successfully',
        'qr_code': f"data:image/png;base64,{img_str}"
    })

@app.route('/retail', methods=['POST'])
def add_retail():
    data = request.get_json()
    retail = RetailSale(
        user_id=data['user_id'],
        distribution_id=data['distribution_id'],
        received_date=datetime.strptime(data['received_date'], '%Y-%m-%d'),
        price=data['price'],
        retail_location=data['retail_location']
    )
    db.session.add(retail)
    db.session.commit()
    
    # Get medicine_id from distribution
    distribution = Distribution.query.get_or_404(data['distribution_id'])
    medicine_id = distribution.medicine_id
    
    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(f"http://localhost:4200/consumer/{medicine_id}")
    qr.make(fit=True)
    img = qr.make_image(fill='black', back_color='white')
    
    # Save QR code
    qr_path = os.path.join(QR_CODE_RETAILER_DIR, f"medicine_{medicine_id}.png")
    img.save(qr_path)
    
    # Convert to base64 for response
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    
    return jsonify({
        'id': retail.id,
        'message': 'Retail sale added successfully',
        'qr_code': f"data:image/png;base64,{img_str}"
    })

@app.route('/product_history/<int:id>', methods=['GET'])
def get_product_history(id):
    # Try to find a medicine first
    medicine = Medicine.query.get(id)
    if medicine:
        raw_material = RawMaterial.query.get(medicine.raw_material_id)
        distributions = Distribution.query.filter_by(medicine_id=medicine.id).all()
        retail_sales = RetailSale.query.filter(RetailSale.distribution_id.in_(
            [d.id for d in distributions])).all()
        
        return jsonify({
            'raw_material': {
                'material_type': raw_material.material_type,
                'quantity': raw_material.quantity,
                'source_location': raw_material.source_location,
                'supply_date': raw_material.supply_date.strftime('%Y-%m-%d')
            } if raw_material else None,
            'medicine': {
                'medicine_name': medicine.medicine_name,
                'batch_number': medicine.batch_number,
                'production_date': medicine.production_date.strftime('%Y-%m-%d'),
                'expiry_date': medicine.expiry_date.strftime('%Y-%m-%d')
            },
            'distributions': [{
                'shipment_date': d.shipment_date.strftime('%Y-%m-%d'),
                'transport_method': d.transport_method,
                'destination': d.destination,
                'storage_condition': d.storage_condition
            } for d in distributions],
            'retail_sales': [{
                'received_date': r.received_date.strftime('%Y-%m-%d'),
                'price': r.price,
                'retail_location': r.retail_location
            } for r in retail_sales]
        })
    
    # Try to find a raw material
    raw_material = RawMaterial.query.get(id)
    if raw_material:
        return jsonify({
            'raw_material': {
                'material_type': raw_material.material_type,
                'quantity': raw_material.quantity,
                'source_location': raw_material.source_location,
                'supply_date': raw_material.supply_date.strftime('%Y-%m-%d')
            },
            'medicine': None,
            'distributions': [],
            'retail_sales': []
        })
    
    return jsonify({'error': 'Record not found'}), 404

if __name__ == '__main__':
    app.run(debug=True)