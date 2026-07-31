from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False) 
    status = db.Column(db.String(20), default='Approved')

    # Relationships
    bookings = db.relationship('Booking', backref='user', lazy=True)
    assigned_treks = db.relationship('Trek', back_populates='staff')

class Trek(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    difficulty = db.Column(db.String(20), nullable=False)
    duration = db.Column(db.Integer, nullable=False) # in days
    available_slots = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='Open') # 'Open', 'Closed', 'Completed'

    

    # Foreign Key linking to the User table
    staff_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    staff = db.relationship('User', foreign_keys=[staff_id], back_populates='assigned_treks')
    
    # Relationship
    bookings = db.relationship('Booking', backref='trek', lazy=True)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    trek_id = db.Column(db.Integer, db.ForeignKey('trek.id'), nullable=False)
    booking_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='Booked') # 'Booked', 'Cancelled', 'Completed'