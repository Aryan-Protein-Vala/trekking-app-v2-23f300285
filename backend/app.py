import os
import json
import csv
from datetime import timedelta
import requests

# Flask: The core web framework.
# request: Allows us to access incoming HTTP request data (e.g., JSON payload).
# jsonify: Converts Python dictionaries into JSON HTTP responses.
# send_file, send_from_directory: Used to serve static files (like CSVs or frontend HTML).
from flask import Flask, request, jsonify, send_file, send_from_directory

# Flask-JWT-Extended: Handles JSON Web Token authentication.
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity

# CORS: Cross-Origin Resource Sharing. Allows our frontend (if running on a different port) to talk to this API.
from flask_cors import CORS

# Celery & crontab: For running background tasks and scheduled tasks.
from celery import Celery
from celery.schedules import crontab

# Redis: An in-memory data store used for caching and as a message broker for Celery.
from redis import Redis

# Import our database models defined in models.py
from models.models import db, User, Trek, Booking

# ==========================================
# 1. FLASK APP INITIALIZATION
# ==========================================
app = Flask('app')
CORS(app) # Enable CORS for all routes

# Configure the SQLite database location
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Security key used to sign the JWT tokens. NEVER hardcode this in a real production app!
app.config['JWT_SECRET_KEY'] = 'super-secret-key-for-mad2'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24) # Tokens expire after 24 hours

# Attach the SQLAlchemy instance to our Flask app
db.init_app(app)
# Initialize the JWT manager
jwt = JWTManager(app)

# Connect to Redis server (must be running locally on port 6379)
redis_client = Redis(host='localhost', port=6379, db=0, decode_responses=True)

# ==========================================
# 2. CELERY SETUP (Background Jobs)
# ==========================================
# This function wraps Celery to integrate it tightly with Flask.
# It ensures background tasks run inside the Flask Application Context (so they can access the DB).
def make_celery(app):
    celery = Celery(
        app.import_name,
        backend='redis://localhost:6379/1', # Where task results are stored
        broker='redis://localhost:6379/2'   # Where task messages are sent
    )
    celery.conf.update(app.config)
    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)
    celery.Task = ContextTask
    return celery

celery_app = make_celery(app)

# --- BACKGROUND TASKS DEFINITIONS ---

# @celery_app.task registers this function as a background task.
@celery_app.task(name='app.daily_trek_reminder')
def daily_trek_reminder():
    # Example of a webhook call for daily reminders
    webhook_url = 'http://localhost:5000/mock_webhook'
    try:
        requests.post(webhook_url, json={'text': 'Reminder: Upcoming treks tomorrow!'})
    except:
        pass
    return "Daily reminder sent"

@celery_app.task(name='app.monthly_admin_report')
def monthly_admin_report():
    # Queries the database for total stats
    total_treks = Trek.query.count()
    total_bookings = Booking.query.count()
    report_content = f"<h1>Monthly Report</h1><p>Treks: {total_treks}</p><p>Bookings: {total_bookings}</p>"
    
    # Ensures the directory exists before writing the file
    os.makedirs('static/reports', exist_ok=True)
    with open('static/reports/monthly_report.html', 'w') as f:
        f.write(report_content)
    return "Monthly report generated"

# Takes user_id as an argument. Generates a CSV file of their bookings.
@celery_app.task(name='app.export_bookings_csv')
def export_bookings_csv(user_id):
    os.makedirs('static/exports', exist_ok=True)
    filename = f"static/exports/bookings_{user_id}.csv"
    
    # Query only the bookings belonging to this specific user
    bookings = Booking.query.filter_by(user_id=user_id).all()
    
    # Write the data to a CSV file
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Booking ID', 'Trek Name', 'Location', 'Status']) # Header row
        for b in bookings:
            writer.writerow([b.id, b.trek.name, b.trek.location, b.status])
    return filename

# --- SCHEDULED TASKS (Celery Beat) ---
# This dictionary tells Celery Beat when to run certain tasks automatically.
celery_app.conf.beat_schedule = {
    'daily-reminder': {
        'task': 'app.daily_trek_reminder',
        'schedule': crontab(hour=8, minute=0), # Runs every day at 8:00 AM
    },
    'monthly-report': {
        'task': 'app.monthly_admin_report',
        'schedule': crontab(day_of_month='1', hour=0, minute=0), # Runs the 1st of every month at midnight
    },
}

# ==========================================
# 3. DATABASE INITIALIZATION
# ==========================================
# Before the first request, we ensure the tables exist and an Admin is present.
with app.app_context():
    db.create_all() # Creates tables based on models.py (if they don't exist)
    
    # Seed the database with an initial Admin user if one doesn't exist
    admin = User.query.filter_by(role='Admin').first()
    if not admin:
        new_admin = User(username='admin', password='asdfghjkl;', role='Admin')
        db.session.add(new_admin)
        db.session.commit()

# ==========================================
# 4. API ROUTES
# ==========================================

# LOGIN API
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json() # Extract JSON sent by the frontend
    username = data.get('username')
    password = data.get('password')
    
    # Look up the user in the database
    user = User.query.filter_by(username=username).first()
    
    # Verify password (in reality, you'd use check_password_hash here)
    if user and user.password == password:
        # Example of Staff approval logic
        if user.role == 'Staff' and not user.is_approved:
            return jsonify({"msg": "Staff account pending approval"}), 403
            
        # Create the JWT token. The identity is the user.id.
        # We also embed their role in the token claims so we can check it later.
        access_token = create_access_token(
            identity=str(user.id),
            additional_claims={'role': user.role, 'username': user.username}
        )
        return jsonify({"token": access_token, "role": user.role}), 200
        
    return jsonify({"msg": "Invalid credentials"}), 401

# REGISTER API
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    role = data.get('role', 'User')
    
    # Prevent duplicate usernames
    if User.query.filter_by(username=data.get('username')).first():
        return jsonify({"msg": "Username already exists"}), 400
        
    # Only regular 'User' roles are auto-approved. Staff needs manual approval later.
    is_approved = True if role == 'User' else False
    
    new_user = User(username=data.get('username'), password=data.get('password'), role=role, is_approved=is_approved)
    db.session.add(new_user)
    db.session.commit() # Save to database
    return jsonify({"msg": "Registered successfully"}), 201

# GET TREKS API (with Caching and Personalization)
@app.route('/api/treks', methods=['GET'])
@jwt_required(optional=True) # Optional so logged-out users can still see treks
def get_treks():
    from flask_jwt_extended import get_jwt_identity
    current_user_id = get_jwt_identity() # Returns None if not logged in

    # 1. Try to get data from Redis cache first
    cached_treks = redis_client.get('all_treks')
    if cached_treks:
        result = json.loads(cached_treks)
    else:
        # 2. If not in cache, query the database (Slow response)
        treks = Trek.query.all()
        result = []
        for t in treks:
            result.append({
                'id': t.id, 'name': t.name, 'location': t.location, 
                'difficulty': t.difficulty, 'duration_days': t.duration_days,
                'available_slots': t.available_slots, 'status': t.status,
                'assigned_staff_id': t.assigned_staff_id, 'description': t.description
            })
        # Store the generic result in Redis for future requests (expires in 60 seconds)
        redis_client.set('all_treks', json.dumps(result), ex=60)
    
    # 3. Personalize the data for the current user!
    # We do this AFTER caching, so we don't accidentally cache User A's bookings for User B!
    if current_user_id:
        user_bookings = Booking.query.filter_by(user_id=current_user_id).all()
        booked_trek_ids = [b.trek_id for b in user_bookings]
        for t in result:
            t['is_booked_by_user'] = t['id'] in booked_trek_ids
    else:
        for t in result:
            t['is_booked_by_user'] = False

    return jsonify(result), 200

# CREATE TREK API (Protected, Admin Only)
@app.route('/api/admin/treks', methods=['POST'])
@jwt_required() # Ensures the user provided a valid token
def create_trek():
    from flask_jwt_extended import get_jwt
    claims = get_jwt() # Extract the additional claims we embedded during login
    
    # RBAC: Role-Based Access Control. Only Admins can hit this route.
    if claims.get('role') != 'Admin':
        return jsonify({"msg": "Unauthorized"}), 403
        
    data = request.get_json()
    new_trek = Trek(
        name=data['name'], location=data['location'], difficulty=data['difficulty'],
        duration_days=data['duration_days'], available_slots=data['available_slots'],
        assigned_staff_id=data.get('assigned_staff_id'), description=data.get('description', 'No description provided')
    )
    db.session.add(new_trek)
    db.session.commit()
    
    # CRITICAL: We changed the database, so we MUST delete the old cache!
    # Otherwise, users will see stale data for up to 60 seconds.
    redis_client.delete('all_treks')
    return jsonify({"msg": "Trek created"}), 201

# UPDATE TREK API (Protected, Staff Only)
@app.route('/api/staff/treks/<int:trek_id>', methods=['PUT'])
@jwt_required()
def update_trek(trek_id):
    from flask_jwt_extended import get_jwt
    claims = get_jwt()
    current_user_id = int(get_jwt_identity()) # get_jwt_identity() returns the 'identity' we set at login (user.id)
    
    if claims.get('role') != 'Staff':
        return jsonify({"msg": "Unauthorized"}), 403
        
    trek = Trek.query.get(trek_id)
    
    # Ensure trek exists AND this specific staff member is assigned to it
    if not trek or trek.assigned_staff_id != current_user_id:
        return jsonify({"msg": "Unauthorized or not found"}), 403
        
    data = request.get_json()
    # Update fields. If a field isn't in the request, keep the old value.
    trek.status = data.get('status', trek.status)
    trek.available_slots = data.get('available_slots', trek.available_slots)
    db.session.commit()
    
    redis_client.delete('all_treks') # Invalidate cache
    return jsonify({"msg": "Trek updated"}), 200

# BOOK TREK API (Protected, Users Only)
@app.route('/api/user/book', methods=['POST'])
@jwt_required()
def book_trek():
    from flask_jwt_extended import get_jwt
    claims = get_jwt()
    current_user_id = int(get_jwt_identity())
    
    if claims.get('role') != 'User':
        return jsonify({"msg": "Unauthorized"}), 403
        
    data = request.get_json()
    trek_id = data.get('trek_id')
    trek = Trek.query.get(trek_id)
    
    # Validation: Trek must exist, have slots, and be 'Open'
    if not trek or trek.available_slots <= 0 or trek.status != 'Open':
        return jsonify({"msg": "Trek unavailable"}), 400
        
    # Prevent duplicate bookings
    existing_booking = Booking.query.filter_by(user_id=current_user_id, trek_id=trek_id).first()
    if existing_booking:
        return jsonify({"msg": "You have already booked this trek!"}), 400
        
    booking = Booking(user_id=current_user_id, trek_id=trek_id)
    trek.available_slots -= 1 # Decrement slots
    
    db.session.add(booking)
    db.session.commit()
    
    redis_client.delete('all_treks') # Invalidate cache
    return jsonify({"msg": "Trek booked", "booking_id": booking.id}), 201

# CANCEL BOOKING API (Protected, Users Only)
@app.route('/api/user/cancel/<int:trek_id>', methods=['DELETE'])
@jwt_required()
def cancel_booking(trek_id):
    from flask_jwt_extended import get_jwt
    claims = get_jwt()
    current_user_id = int(get_jwt_identity())
    
    if claims.get('role') != 'User':
        return jsonify({"msg": "Unauthorized"}), 403
        
    # Find the specific booking for this user and this trek
    booking = Booking.query.filter_by(user_id=current_user_id, trek_id=trek_id).first()
    
    if not booking:
        return jsonify({"msg": "Booking not found or unauthorized"}), 404
        
    # Get the related trek to increment its slots
    trek = Trek.query.get(trek_id)
    
    # Refund the slot
    if trek:
        trek.available_slots += 1
    
    db.session.delete(booking)
    db.session.commit()
    
    redis_client.delete('all_treks') # Invalidate cache
    return jsonify({"msg": "Booking cancelled"}), 200


# EXPORT BOOKINGS API (Triggers Background Task)
@app.route('/api/user/export', methods=['POST'])
@jwt_required()
def export_bookings():
    current_user_id = int(get_jwt_identity())
    
    # .delay() tells Celery to run this function in the background.
    # Flask does NOT wait for it to finish; it moves to the next line immediately.
    task = export_bookings_csv.delay(current_user_id)
    
    # Return HTTP 202 (Accepted) meaning "We got the request and are working on it."
    return jsonify({"msg": "Export started", "task_id": task.id, "filename": f"bookings_{current_user_id}.csv"}), 202

# ROUTE TO DOWNLOAD STATIC FILES (like the exported CSV)
@app.route('/static/exports/<filename>')
def download_export(filename):
    import os
    filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'exports', filename)
    return send_file(filepath)

# ==========================================
# 5. FRONTEND SERVING ROUTES
# ==========================================
# These routes serve the Vue.js frontend files. 

@app.route('/api/stats')
@jwt_required()
def get_stats():
    from flask_jwt_extended import get_jwt
    from flask_jwt_extended import get_jwt_identity
    claims = get_jwt()
    current_user_id = int(get_jwt_identity())
    
    if claims.get('role') != 'Admin':
        return jsonify({"msg": "Unauthorized"}), 403
        
    stats = {
        'total_treks': Trek.query.count()
    }
    return jsonify(stats), 200

@app.route('/')
def serve_frontend():
    import os
    # Move up one folder to 'trekking_app_23f3000285' then into 'frontend'
    frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'frontend')
    return send_from_directory(frontend_dir, 'index.html')

@app.route('/app.js')
def serve_app_js():
    import os
    frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'frontend')
    return send_from_directory(frontend_dir, 'app.js')

# Run the server when this file is executed directly
if __name__ == '__main__':
    app.run(debug=True, port=5000)

