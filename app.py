from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate
from database import db, init_db
from models import User, RawMaterial, Medicine, Distribution, RetailSale
import qrcode
import os
from datetime import datetime
import base64
from io import BytesIO
import logging
import traceback
from sqlalchemy.exc import SQLAlchemyError, OperationalError

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # Ensure logs are output to console for Render
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://supply_chain_db_0hs0_user:YVg8UvpzmgrJPWBGRYTaAPczQfIdKTyi@dpg-d0kjfd56ubrc73bbn1bg-a.oregon-postgres.render.com/supply_chain_db_0hs0')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize Bcrypt
bcrypt = Bcrypt(app)

# Initialize Migrate
migrate = Migrate(app, db)

# Configure CORS
ALLOWED_ORIGINS = os.environ.get('ALLOWED_ORIGINS', 'https://medical-supply-chain.vercel.app,http://localhost:4200').split(',')
CORS(app, resources={r"/*": {
    "origins": ALLOWED_ORIGINS,
    "methods": ["GET", "POST", "OPTIONS"],
    "allow_headers": ["Content-Type", "Authorization"]
}})

# Initialize database
try:
    init_db(app)
    logger.info("Database initialized successfully")
except OperationalError as e:
    logger.error(f"Database connection failed: {str(e)}\n{traceback.format_exc()}")
    raise
except Exception as e:
    logger.error(f"Failed to initialize database: {str(e)}\n{traceback.format_exc()}")
    raise

# Get frontend URL
FRONTEND_URL = os.environ.get("FRONTEND_URL", "https://medical-supply-chain.vercel.app")

@app.route('/register', methods=['POST', 'OPTIONS'])
def register():
    if request.method == 'OPTIONS':
        logger.info("Handling OPTIONS request for /register")
        response = jsonify({'message': 'Preflight OK'})
        response.headers.add('Access-Control-Allow-Origin', request.headers.get('Origin'))
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response

    try:
        data = request.get_json()
        if not data:
            logger.warning("No JSON data provided in register request")
            return jsonify({'error': 'Invalid request: No data provided'}), 400

        logger.info(f"Register request received: {data.get('email')}")

        # Validate required fields
        required_fields = ['first_name', 'last_name', 'email', 'phone', 'password', 'confirm_password', 'role']
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            logger.warning(f"Missing fields: {missing_fields}")
            return jsonify({'error': f'Missing required fields: {", ".join(missing_fields)}'}), 400

        # Validate password
        if data['password'] != data['confirm_password']:
            logger.warning("Passwords do not match")
            return jsonify({'error': 'Passwords do not match'}), 400
        if len(data['password']) < 8:
            logger.warning("Password too short")
            return jsonify({'error': 'Password must be at least 8 characters'}), 400

        # Validate role
        valid_roles = ['Manufacturer', 'Distributor', 'Retailer']
        if data['role'] not in valid_roles:
            logger.warning(f"Invalid role: {data['role']}")
            return jsonify({'error': f'Invalid role. Must be one of: {", ".join(valid_roles)}'}), 400

        with app.app_context():
            if User.query.filter_by(email=data['email']).first():
                logger.warning(f"Email already exists: {data['email']}")
                return jsonify({'error': 'Email already exists'}), 400

            user = User(
                first_name=data['first_name'],
                last_name=data['last_name'],
                email=data['email'],
                phone=data['phone'],
                password=bcrypt.generate_password_hash(data['password']).decode('utf-8'),
                role=data['role']
            )
            db.session.add(user)
            db.session.commit()
            logger.info(f"User registered successfully: {data['email']}")
            return jsonify({'message': 'User registered successfully'})

    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error during registration: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'error': f'Database error: {str(e)}'}), 500
    except Exception as e:
        logger.error(f"Unexpected error during registration: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

@app.route('/login', methods=['POST', 'OPTIONS'])
def login():
    if request.method == 'OPTIONS':
        logger.info("Handling OPTIONS request for /login")
        response = jsonify({'message': 'Preflight OK'})
        response.headers.add('Access-Control-Allow-Origin', request.headers.get('Origin'))
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response

    try:
        data = request.get_json()
        if not data or 'identifier' not in data or 'password' not in data:
            logger.warning("Invalid login request: Missing identifier or password")
            return jsonify({'error': 'Invalid request: Missing identifier or password'}), 400

        with app.app_context():
            user = User.query.filter((User.email == data['identifier']) | (User.phone == data['identifier'])).first()
            if user and bcrypt.check_password_hash(user.password, data['password']):
                logger.info(f"User logged in: {user.email}")
                return jsonify({
                    'id': user.id,
                    'first_name': user.first_name,
                    'role': user.role
                })
            logger.warning(f"Invalid login attempt for {data['identifier']}")
            return jsonify({'error': 'Invalid credentials'}), 401

    except SQLAlchemyError as e:
        logger.error(f"Database error during login: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'error': f'Database error: {str(e)}'}), 500
    except Exception as e:
        logger.error(f"Unexpected error during login: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

@app.route('/manufacturer', methods=['POST', 'OPTIONS'])
def check_manufacturer():
    if request.method == 'OPTIONS':
        logger.info("Handling OPTIONS request for /manufacturer")
        response = jsonify({'message': 'Preflight OK'})
        response.headers.add('Access-Control-Allow-Origin', request.headers.get('Origin'))
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response

    try:
        data = request.get_json()
        if not data or 'user_id' not in data:
            logger.warning("Invalid manufacturer request: Missing user_id")
            return jsonify({'error': 'Invalid request: Missing user_id'}), 400

        with app.app_context():
            user = User.query.filter_by(id=data['user_id']).first()
            if user and user.role == 'Manufacturer':
                logger.info(f"Manufacturer access granted: {user.email}")
                return jsonify({'message': 'Access granted'})
            logger.warning(f"Unauthorized Manufacturer access for user_id: {data['user_id']}")
            return jsonify({'error': 'Unauthorized: Not a Manufacturer'}), 403

    except Exception as e:
        logger.error(f"Error in check_manufacturer: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

@app.route('/distributor', methods=['POST', 'OPTIONS'])
def check_distributor():
    if request.method == 'OPTIONS':
        logger.info("Handling OPTIONS request for /distributor")
        response = jsonify({'message': 'Preflight OK'})
        response.headers.add('Access-Control-Allow-Origin', request.headers.get('Origin'))
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response

    try:
        data = request.get_json()
        if not data or 'user_id' not in data:
            logger.warning("Invalid distributor request: Missing user_id")
            return jsonify({'error': 'Invalid request: Missing user_id'}), 400

        with app.app_context():
            user = User.query.filter_by(id=data['user_id']).first()
            if user and user.role == 'Distributor':
                logger.info(f"Distributor access granted: {user.email}")
                return jsonify({'message': 'Access granted'})
            logger.warning(f"Unauthorized Distributor access for user_id: {data['user_id']}")
            return jsonify({'error': 'Unauthorized: Not a Distributor'}), 403

    except Exception as e:
        logger.error(f"Error in check_distributor: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

@app.route('/retailer', methods=['POST', 'OPTIONS'])
def check_retailer():
    if request.method == 'OPTIONS':
        logger.info("Handling OPTIONS request for /retailer")
        response = jsonify({'message': 'Preflight OK'})
        response.headers.add('Access-Control-Allow-Origin', request.headers.get('Origin'))
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response

    try:
        data = request.get_json()
        if not data or 'user_id' not in data:
            logger.warning("Invalid retailer request: Missing user_id")
            return jsonify({'error': 'Invalid request: Missing user_id'}), 400

        with app.app_context():
            user = User.query.filter_by(id=data['user_id']).first()
            if user and user.role == 'Retailer':
                logger.info(f"Retailer access granted: {user.email}")
                return jsonify({'message': 'Access granted'})
            logger.warning(f"Unauthorized Retailer access for user_id: {data['user_id']}")
            return jsonify({'error': 'Unauthorized: Not a Retailer'}), 403

    except Exception as e:
        logger.error(f"Error in check_retailer: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

@app.route('/raw_material', methods=['POST', 'OPTIONS'])
def add_raw_material():
    if request.method == 'OPTIONS':
        logger.info("Handling OPTIONS request for /raw_material")
        response = jsonify({'message': 'Preflight OK'})
        response.headers.add('Access-Control-Allow-Origin', request.headers.get('Origin'))
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response

    try:
        data = request.get_json()
        required_fields = ['user_id', 'material_type', 'quantity', 'source_location', 'supply_date']
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            logger.warning(f"Missing fields in raw_material: {missing_fields}")
            return jsonify({'error': f'Missing required fields: {", ".join(missing_fields)}'}), 400

        try:
            supply_date = datetime.strptime(data['supply_date'], '%Y-%m-%d')
        except ValueError:
            logger.warning("Invalid date format for supply_date")
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

        with app.app_context():
            user = User.query.get(data['user_id'])
            if not user or user.role != 'Manufacturer':
                logger.warning(f"Unauthorized: User {data['user_id']} is not a Manufacturer")
                return jsonify({'error': 'Unauthorized: Only Manufacturers can add raw materials'}), 403

            raw_material = RawMaterial(
                user_id=data['user_id'],
                material_type=data['material_type'],
                quantity=data['quantity'],
                source_location=data['source_location'],
                supply_date=supply_date
            )
            db.session.add(raw_material)
            db.session.commit()

            # Generate QR code
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(f"{FRONTEND_URL}/consumer/{raw_material.id}")
            qr.make(fit=True)
            img = qr.make_image(fill='black', back_color='white')

            # Save QR code as base64 string
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            raw_material.qr_code = f"data:image/png;base64,{img_str}"
            db.session.commit()

            logger.info(f"Raw material added: ID {raw_material.id}")
            return jsonify({
                'id': raw_material.id,
                'message': 'Raw material added successfully',
                'qr_code': raw_material.qr_code
            })

    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error in add_raw_material: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'error': f'Database error: {str(e)}'}), 500
    except Exception as e:
        logger.error(f"Unexpected error in add_raw_material: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

@app.route('/raw_materials', methods=['GET', 'OPTIONS'])
def get_raw_materials():
    if request.method == 'OPTIONS':
        logger.info("Handling OPTIONS request for /raw_materials")
        response = jsonify({'message': 'Preflight OK'})
        response.headers.add('Access-Control-Allow-Origin', request.headers.get('Origin'))
        response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response

    try:
        with app.app_context():
            used_raw_material_ids = db.session.query(Medicine.raw_material_id).distinct().subquery()
            materials = RawMaterial.query.filter(~RawMaterial.id.in_(used_raw_material_ids)).all()
            logger.info(f"Fetched {len(materials)} available raw materials")
            return jsonify([{
                'id': m.id,
                'material_type': m.material_type,
                'quantity': m.quantity,
                'qr_code': m.qr_code
            } for m in materials])

    except Exception as e:
        logger.error(f"Error in get_raw_materials: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

@app.route('/medicines', methods=['GET', 'OPTIONS'])
def get_medicines():
    if request.method == 'OPTIONS':
        logger.info("Handling OPTIONS request for /medicines")
        response = jsonify({'message': 'Preflight OK'})
        response.headers.add('Access-Control-Allow-Origin', request.headers.get('Origin'))
        response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response

    try:
        with app.app_context():
            used_medicine_ids = db.session.query(Distribution.medicine_id).distinct().subquery()
            medicines = Medicine.query.filter(~Medicine.id.in_(used_medicine_ids)).all()
            logger.info(f"Fetched {len(medicines)} available medicines")
            return jsonify([{
                'id': m.id,
                'medicine_name': m.medicine_name,
                'batch_number': m.batch_number,
                'qr_code': m.qr_code
            } for m in medicines])

    except Exception as e:
        logger.error(f"Error in get_medicines: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

@app.route('/medicine', methods=['POST', 'OPTIONS'])
def add_medicine():
    if request.method == 'OPTIONS':
        logger.info("Handling OPTIONS request for /medicine")
        response = jsonify({'message': 'Preflight OK'})
        response.headers.add('Access-Control-Allow-Origin', request.headers.get('Origin'))
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response

    try:
        data = request.get_json()
        required_fields = ['user_id', 'raw_material_id', 'medicine_name', 'batch_number', 'production_date', 'expiry_date']
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            logger.warning(f"Missing fields in add_medicine: {missing_fields}")
            return jsonify({'error': f'Missing required fields: {", ".join(missing_fields)}'}), 400

        try:
            production_date = datetime.strptime(data['production_date'], '%Y-%m-%d')
            expiry_date = datetime.strptime(data['expiry_date'], '%Y-%m-%d')
        except ValueError:
            logger.warning("Invalid date format for production_date or expiry_date")
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

        with app.app_context():
            user = User.query.get(data['user_id'])
            if not user or user.role != 'Manufacturer':
                logger.warning(f"Unauthorized: User {data['user_id']} is not a Manufacturer")
                return jsonify({'error': 'Unauthorized: Only Manufacturers can add medicines'}), 403

            medicine = Medicine(
                user_id=data['user_id'],
                raw_material_id=data['raw_material_id'],
                medicine_name=data['medicine_name'],
                batch_number=data['batch_number'],
                production_date=production_date,
                expiry_date=expiry_date
            )
            db.session.add(medicine)
            db.session.commit()

            # Generate QR code
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(f"{FRONTEND_URL}/consumer/{medicine.id}")
            qr.make(fit=True)
            img = qr.make_image(fill='black', back_color='white')

            # Save QR code as base64 string
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            medicine.qr_code = f"data:image/png;base64,{img_str}"
            db.session.commit()

            logger.info(f"Medicine added: ID {medicine.id}")
            return jsonify({
                'id': medicine.id,
                'message': 'Medicine added successfully',
                'qr_code': medicine.qr_code
            })

    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error in add_medicine: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'error': f'Database error: {str(e)}'}), 500
    except Exception as e:
        logger.error(f"Unexpected error in add_medicine: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

@app.route('/distributions', methods=['GET', 'OPTIONS'])
def get_distributions():
    if request.method == 'OPTIONS':
        logger.info("Handling OPTIONS request for /distributions")
        response = jsonify({'message': 'Preflight OK'})
        response.headers.add('Access-Control-Allow-Origin', request.headers.get('Origin'))
        response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response

    try:
        with app.app_context():
            used_distribution_ids = db.session.query(RetailSale.distribution_id).distinct().subquery()
            distributions = Distribution.query.filter(~Distribution.id.in_(used_distribution_ids)).all()
            logger.info(f"Fetched {len(distributions)} available distributions")
            return jsonify([{
                'id': d.id,
                'medicine_id': d.medicine_id,
                'destination': d.destination,
                'shipment_date': d.shipment_date.strftime('%Y-%m-%d'),
                'qr_code': d.qr_code
            } for d in distributions])

    except Exception as e:
        logger.error(f"Error in get_distributions: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

@app.route('/distribution', methods=['POST', 'OPTIONS'])
def add_distribution():
    if request.method == 'OPTIONS':
        logger.info("Handling OPTIONS request for /distribution")
        response = jsonify({'message': 'Preflight OK'})
        response.headers.add('Access-Control-Allow-Origin', request.headers.get('Origin'))
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response

    try:
        data = request.get_json()
        required_fields = ['user_id', 'medicine_id', 'shipment_date', 'transport_method', 'destination', 'storage_condition']
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            logger.warning(f"Missing fields in add_distribution: {missing_fields}")
            return jsonify({'error': f'Missing required fields: {", ".join(missing_fields)}'}), 400

        try:
            shipment_date = datetime.strptime(data['shipment_date'], '%Y-%m-%d')
        except ValueError:
            logger.warning("Invalid date format for shipment_date")
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

        with app.app_context():
            user = User.query.get(data['user_id'])
            if not user or user.role != 'Distributor':
                logger.warning(f"Unauthorized: User {data['user_id']} is not a Distributor")
                return jsonify({'error': 'Unauthorized: Only Distributors can add distributions'}), 403

            distribution = Distribution(
                user_id=data['user_id'],
                medicine_id=data['medicine_id'],
                shipment_date=shipment_date,
                transport_method=data['transport_method'],
                destination=data['destination'],
                storage_condition=data['storage_condition']
            )
            db.session.add(distribution)
            db.session.commit()

            # Generate QR code
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(f"{FRONTEND_URL}/consumer/{distribution.medicine_id}")
            qr.make(fit=True)
            img = qr.make_image(fill='black', back_color='white')

            # Save QR code as base64 string
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            distribution.qr_code = f"data:image/png;base64,{img_str}"
            db.session.commit()

            logger.info(f"Distribution added: ID {distribution.id}")
            return jsonify({
                'id': distribution.id,
                'message': 'Distribution added successfully',
                'qr_code': distribution.qr_code
            })

    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error in add_distribution: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'error': f'Database error: {str(e)}'}), 500
    except Exception as e:
        logger.error(f"Unexpected error in add_distribution: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

@app.route('/retail', methods=['POST', 'OPTIONS'])
def add_retail():
    if request.method == 'OPTIONS':
        logger.info("Handling OPTIONS request for /retail")
        response = jsonify({'message': 'Preflight OK'})
        response.headers.add('Access-Control-Allow-Origin', request.headers.get('Origin'))
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response

    try:
        data = request.get_json()
        required_fields = ['user_id', 'distribution_id', 'received_date', 'price', 'retail_location']
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            logger.warning(f"Missing fields in add_retail: {missing_fields}")
            return jsonify({'error': f'Missing required fields: {", ".join(missing_fields)}'}), 400

        try:
            received_date = datetime.strptime(data['received_date'], '%Y-%m-%d')
        except ValueError:
            logger.warning("Invalid date format for received_date")
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

        with app.app_context():
            user = User.query.get(data['user_id'])
            if not user or user.role != 'Retailer':
                logger.warning(f"Unauthorized: User {data['user_id']} is not a Retailer")
                return jsonify({'error': 'Unauthorized: Only Retailers can add retail sales'}), 403

            retail = RetailSale(
                user_id=data['user_id'],
                distribution_id=data['distribution_id'],
                received_date=received_date,
                price=data['price'],
                retail_location=data['retail_location']
            )
            db.session.add(retail)
            db.session.commit()

            # Generate QR code
            distribution = Distribution.query.get_or_404(data['distribution_id'])
            medicine_id = distribution.medicine_id
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(f"{FRONTEND_URL}/consumer/{medicine_id}")
            qr.make(fit=True)
            img = qr.make_image(fill='black', back_color='white')

            # Save QR code as base64 string
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            retail.qr_code = f"data:image/png;base64,{img_str}"
            db.session.commit()

            logger.info(f"Retail sale added: ID {retail.id}")
            return jsonify({
                'id': retail.id,
                'message': 'Retail sale added successfully',
                'qr_code': retail.qr_code
            })

    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error in add_retail: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'error': f'Database error: {str(e)}'}), 500
    except Exception as e:
        logger.error(f"Unexpected error in add_retail: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

@app.route('/product_history/<int:id>', methods=['GET', 'OPTIONS'])
def get_product_history(id):
    if request.method == 'OPTIONS':
        logger.info("Handling OPTIONS request for /product_history")
        response = jsonify({'message': 'Preflight OK'})
        response.headers.add('Access-Control-Allow-Origin', request.headers.get('Origin'))
        response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response

    try:
        logger.info(f"Fetching product history for ID: {id}")
        with app.app_context():
            medicine = Medicine.query.get(id)
            if medicine:
                raw_material = RawMaterial.query.get(medicine.raw_material_id)
                distributions = Distribution.query.filter_by(medicine_id=medicine.id).all()
                retail_sales = RetailSale.query.filter(RetailSale.distribution_id.in_([d.id for d in distributions])).all()

                return jsonify({
                    'raw_material': {
                        'material_type': raw_material.material_type,
                        'quantity': raw_material.quantity,
                        'source_location': raw_material.source_location,
                        'supply_date': raw_material.supply_date.strftime('%Y-%m-%d'),
                        'qr_code': raw_material.qr_code
                    } if raw_material else None,
                    'medicine': {
                        'medicine_name': medicine.medicine_name,
                        'batch_number': medicine.batch_number,
                        'production_date': medicine.production_date.strftime('%Y-%m-%d'),
                        'expiry_date': medicine.expiry_date.strftime('%Y-%m-%d'),
                        'qr_code': medicine.qr_code
                    },
                    'distributions': [{
                        'shipment_date': d.shipment_date.strftime('%Y-%m-%d'),
                        'transport_method': d.transport_method,
                        'destination': d.destination,
                        'storage_condition': d.storage_condition,
                        'qr_code': d.qr_code
                    } for d in distributions],
                    'retail_sales': [{
                        'received_date': r.received_date.strftime('%Y-%m-%d'),
                        'price': r.price,
                        'retail_location': r.retail_location,
                        'qr_code': r.qr_code
                    } for r in retail_sales]
                })

            raw_material = RawMaterial.query.get(id)
            if raw_material:
                return jsonify({
                    'raw_material': {
                        'material_type': raw_material.material_type,
                        'quantity': raw_material.quantity,
                        'source_location': raw_material.source_location,
                        'supply_date': raw_material.supply_date.strftime('%Y-%m-%d'),
                        'qr_code': raw_material.qr_code
                    },
                    'medicine': None,
                    'distributions': [],
                    'retail_sales': []
                })

            logger.warning(f"Record not found for ID: {id}")
            return jsonify({'error': 'Record not found'}), 404

    except Exception as e:
        logger.error(f"Error in get_product_history: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))