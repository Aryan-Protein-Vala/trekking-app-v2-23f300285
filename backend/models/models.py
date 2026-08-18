# flask_sqlalchemy is an extension for Flask that adds support for SQLAlchemy.
# SQLAlchemy is an Object Relational Mapper (ORM).
# It allows us to interact with our database (SQLite in this case) using Python classes and objects 
# instead of writing raw SQL queries (like "SELECT * FROM users").
from flask_sqlalchemy import SQLAlchemy

# Initialize the SQLAlchemy object. 
# We don't attach it to the Flask app yet (that happens in app.py with db.init_app(app)).
# This pattern is called the "Application Factory" pattern, which prevents circular imports.
db = SQLAlchemy()

# -------------------------------------------------------------------
# MODEL: User
# Represents the 'user' table in the database.
# ---> CROSS-REFERENCE: This model is used heavily in `app.py` inside the `login()` and `register()` API routes.
# ---> The `role` column here dictates whether a user sees the Admin, Staff, or User dashboard in `index.html`.
# -------------------------------------------------------------------
class User(db.Model):
    # Primary Key: A unique integer identifier for every user (auto-increments automatically)
    id = db.Column(db.Integer, primary_key=True)
    
    # Username must be unique (no two users can have the same username). nullable=False means it cannot be empty.
    username = db.Column(db.String(80), unique=True, nullable=False)
    
    # Stores the user's password. In a real-world app, you MUST hash this (e.g., using bcrypt or werkzeug.security).
    # Storing plaintext passwords is a major security risk, but kept simple here for educational purposes.
    password = db.Column(db.String(120), nullable=False)
    
    # Role-based access control (RBAC). Default role is 'User'. Other options: 'Admin', 'Staff'.
    role = db.Column(db.String(20), nullable=False, default='User')
    
    # Used for Staff approval logic. Admin might need to approve Staff accounts before they can login.
    is_approved = db.Column(db.Boolean, default=True)

    # --- RELATIONSHIPS ---
    # db.relationship does NOT create a column in the 'user' table.
    # Instead, it acts as a magical list that queries the related table when accessed.
    
    # 'bookings' allows us to do: user.bookings (returns a list of Booking objects for this user)
    # backref='user' creates a virtual column on the Booking model so we can do: booking.user (returns the User object)
    # lazy=True means SQLAlchemy will only query the bookings table when we actually access user.bookings
    bookings = db.relationship('Booking', backref='user', lazy=True)
    
    # 'assigned_treks' allows us to see which treks a 'Staff' member is managing.
    assigned_treks = db.relationship('Trek', backref='staff', lazy=True)

# -------------------------------------------------------------------
# MODEL: Trek
# Represents the 'trek' table (the list of available treks).
# ---> CROSS-REFERENCE: Fetched by `get_treks()` in `app.py` and sent to `treks` array in `app.js`.
# ---> Displayed in `index.html` using `v-for="trek in treks"`.
# -------------------------------------------------------------------
class Trek(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    difficulty = db.Column(db.String(50), nullable=False)
    duration_days = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text(1000), nullable=True)
    
    # How many spots are left. When a user books, this number decreases.
    # ---> CROSS-REFERENCE: Updated in `book_trek()` in `app.py` when a User clicks "Book Now" in `index.html`.
    available_slots = db.Column(db.Integer, nullable=False)
    
    # Status can be 'Open' (bookable) or 'Closed' (cannot be booked).
    # ---> CROSS-REFERENCE: Updated in `update_trek()` in `app.py` when Staff clicks "Save" on the edit form in `index.html`.
    status = db.Column(db.String(50), default='Open')
    
    # Foreign Key: Links this Trek to a specific User (Staff). 
    # 'user.id' refers to the table name ('user' - SQLAlchemy lowercases class names by default for tables).
    # nullable=True because an Admin might create a trek without immediately assigning staff to it.
    assigned_staff_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    # One-to-Many relationship: One Trek can have multiple Bookings.
    bookings = db.relationship('Booking', backref='trek', lazy=True)

# -------------------------------------------------------------------
# MODEL: Booking
# Represents the 'booking' table. This is an associative table connecting Users and Treks.
# ---> CROSS-REFERENCE: Created in `book_trek()` in `app.py`. 
# ---> Exported by the Celery task `export_bookings_csv()` in `app.py` when User clicks "Export My Bookings (CSV)" in `index.html`.
# -------------------------------------------------------------------
class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    
    # Foreign Key linking to the User who made the booking.
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Foreign Key linking to the Trek being booked.
    trek_id = db.Column(db.Integer, db.ForeignKey('trek.id'), nullable=False)
    
    # Status of the booking.
    status = db.Column(db.String(50), default='Confirmed')

