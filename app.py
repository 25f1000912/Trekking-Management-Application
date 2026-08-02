from functools import wraps
from datetime import datetime
from create_db import init_db
from models import db, User, Trek, Booking
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.sqlite'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'your_super_secret_key' 

db.init_app(app)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if user_id exists in the current session
        if 'user_id' not in session:
            flash('Please log in to access this page.')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def home():
    return redirect(url_for('login'))

# --- Registration Route ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')
        
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already registered. Please log in.')
            return redirect(url_for('register'))
            
        hashed_pw = generate_password_hash(password)
        
        status = 'Pending' if role == 'Staff' else 'Approved'
        
        new_user = User(full_name=full_name, email=email, password=hashed_pw, role=role, status=status)
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! You can now log in.')
        return redirect(url_for('login'))
        
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password, password):
                    
            # BLOCK to prevent blacklisted or pending staff from logging in
            if user.role == 'Staff':
                if user.status == 'Blacklisted':
                    flash('Your account has been blacklisted. Please contact the admin.', 'danger')
                    return redirect(url_for('login'))
                elif user.status == 'Pending':
                    flash('Your account is still pending approval.', 'warning')
                    return redirect(url_for('login'))
                elif user.status == 'Rejected':
                    flash('Your application was rejected.', 'danger')
                    return redirect(url_for('login'))

            if user.role == 'User':
                if user.status == 'Blacklisted':
                    flash('Your account has been suspended. Please contact support.', 'danger')
                    return redirect(url_for('login'))
                
            session['user_id'] = user.id
            session['role'] = user.role
            session['name'] = user.full_name
            
            if user.role == 'Admin':
                return redirect('/admin')
            elif user.role == 'Staff':
                return redirect('/staff')
            else:
                return redirect('/user')
                
        else:
            flash('Invalid email or password.')
            return redirect(url_for('login'))
            
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.')
    return redirect(url_for('login'))


# --- Secure Dashboard Routes ---

@app.route('/admin')
@login_required
def admin():
    if session.get('role') != 'Admin':
        flash('Unauthorized access. Admin privileges required.')
        return redirect(url_for('login'))
        
    # Query the database for live metrics
    total_treks = Trek.query.count()
    total_users = User.query.filter_by(role='User').count()
    total_staff = User.query.filter_by(role='Staff').count()
    total_bookings = Booking.query.count()
    
    # Pass the variables to the Jinja2 template
    return render_template(
        'admin_dashboard.html', 
        total_treks=total_treks,
        total_users=total_users,
        total_staff=total_staff,
        total_bookings=total_bookings
    )

@app.route('/admin/treks')
@login_required
def manage_treks():
    if session.get('role') != 'Admin':
        return redirect(url_for('login'))
        
    all_treks = Trek.query.all()
    return render_template('manage_treks.html', treks=all_treks)


@app.route('/admin/treks/add', methods=['GET', 'POST'])
@login_required
def add_trek():
    if session.get('role') != 'Admin':
        flash('Unauthorized access.')
        return redirect(url_for('login'))

    if request.method == 'POST':

        # Retrieve the staff_id from the form
        staff_id = request.form.get('staff_id')

        staff_id = int(staff_id) if staff_id else None

        # Extract data from the form
        new_trek = Trek(
            name=request.form.get('name'),
            location=request.form.get('location'),
            difficulty=request.form.get('difficulty'),
            duration=request.form.get('duration'),
            available_slots=request.form.get('slots'),
            status=request.form.get('status'),
            staff_id=staff_id
        )
        
        # Save to database
        db.session.add(new_trek)
        db.session.commit()
        
        flash('Trek added successfully!', 'success')
        return redirect(url_for('manage_treks'))
    
    approved_staff = User.query.filter_by(role='Staff', status='Active').all()    
    return render_template('add_trek.html', approved_staff=approved_staff)

@app.route('/admin/treks/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_trek(id):
    if session.get('role') != 'Admin':
        return redirect(url_for('login'))
        
    trek = Trek.query.get_or_404(id)
    
    if request.method == 'POST':

        trek.name = request.form.get('name')
        trek.location = request.form.get('location')
        trek.difficulty = request.form.get('difficulty')
        trek.duration = request.form.get('duration')
        trek.available_slots = request.form.get('slots')
        trek.status = request.form.get('status')
        staff_id = request.form.get('staff_id')
        trek.staff_id = int(staff_id) if staff_id else None
        
        db.session.commit()

        flash('Trek updated successfully!', 'success')
        return redirect(url_for('manage_treks'))

    approved_staff = User.query.filter_by(role='Staff', status='Active').all()
    return render_template('edit_trek.html', trek=trek, approved_staff=approved_staff)

@app.route('/admin/treks/delete/<int:id>', methods=['POST'])
@login_required
def delete_trek(id):
    if session.get('role') != 'Admin':
        return redirect(url_for('login'))
        
    trek = Trek.query.get_or_404(id)
    db.session.delete(trek)
    db.session.commit()
    
    flash('Trek deleted successfully!', 'success')
    return redirect(url_for('manage_treks'))

# --- Admin: Manage Staff ---

@app.route('/manage_staff')
@login_required
def manage_staff():
    if session.get('role') != 'Admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('login'))
        
    # Fetch all users who registered as Staff
    staff_members = User.query.filter_by(role='Staff').all()
    return render_template('manage_staff.html', staff_members=staff_members)

@app.route('/update_staff_status/<int:id>/<string:action>')
@login_required
def update_staff_status(id, action):
    if session.get('role') != 'Admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('login'))
        
    staff = User.query.get_or_404(id)
    
    if action == 'approve' or action == 'whitelist':
        staff.status = 'Active' 
        flash(f'Staff {staff.full_name} is now Active.', 'success')
    elif action == 'blacklist':
        staff.status = 'Blacklisted'
        flash(f'Staff {staff.full_name} has been blacklisted.', 'dark')
    elif action == 'reject':
        staff.status = 'Rejected' 
        flash(f'Staff {staff.full_name} has been rejected.', 'danger')
        
    db.session.commit()
    return redirect(url_for('manage_staff'))

# --- Admin: Manage Users ---

@app.route('/manage_users')
@login_required
def manage_users():
    if session.get('role') != 'Admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('login'))
        
    # Fetch all registered Users
    users = User.query.filter_by(role='User').all()
    
    # Calculate active bookings for each user
    for user in users:
        # Adjust 'Confirmed' or 'Pending' based on your exact Booking model statuses
        active_count = Booking.query.filter(
            Booking.user_id == user.id,
            Booking.status.in_(['Confirmed', 'Pending', 'Active']) 
        ).count()
        user.active_bookings_count = active_count

    return render_template('manage_users.html', users=users)

@app.route('/update_user_status/<int:id>/<string:action>')
@login_required
def update_user_status(id, action):
    if session.get('role') != 'Admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('login'))
        
    user = User.query.get_or_404(id)
    
    if action == 'whitelist':
        user.status = 'Active' 
        flash(f'User {user.full_name} is now Active.', 'success')
    elif action == 'blacklist':
        user.status = 'Blacklisted'
        flash(f'User {user.full_name} has been blacklisted.', 'dark')
        
    db.session.commit()
    return redirect(url_for('manage_users'))

@app.route('/admin/reports')
@login_required
def admin_reports():
    if session.get('role') != 'Admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('login'))
        
    # Query all bookings and order them by the most recent
    all_bookings = Booking.query.order_by(Booking.booking_date.desc()).all()
    
    return render_template('admin_reports.html', bookings=all_bookings)


@app.route('/staff')
@login_required
def staff_dashboard():
    if session.get('role') != 'Staff':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('login'))
        
    assigned_treks = Trek.query.filter_by(staff_id=session.get('user_id')).all()
    
    total_assigned = len(assigned_treks)
    open_treks = sum(1 for trek in assigned_treks if trek.status == 'Open')
    
    total_participants = 0
    for trek in assigned_treks:
        # Fetch actual booking objects instead of just .count()
        participants = Booking.query.filter(
            Booking.trek_id == trek.id, 
            Booking.status.in_(['Confirmed', 'Pending', 'Active'])
        ).all()
        
        trek.participants = participants # Store list of bookings in the trek object
        trek.participant_count = len(participants)
        total_participants += trek.participant_count

    return render_template(
        'staff_dashboard.html', 
        treks=assigned_treks, 
        total_assigned=total_assigned,
        total_participants=total_participants,
        open_treks=open_treks
    )

@app.route('/manage_assigned_trek/<int:id>', methods=['GET', 'POST'])
@login_required
def manage_assigned_trek(id):
    if session.get('role') != 'Staff':
        return redirect(url_for('login'))
        
    trek = Trek.query.get_or_404(id)
    
    # Security check: Ensure the staff member actually manages this trek
    if trek.staff_id != session.get('user_id'):
        flash('You do not have permission to manage this trek.', 'danger')
        return redirect(url_for('staff_dashboard'))
        
    if request.method == 'POST':
        trek.available_slots = int(request.form.get('available_slots'))
        trek.status = request.form.get('status')
        
        db.session.commit()
        flash(f'Trek "{trek.name}" updated successfully.', 'success')
        return redirect(url_for('staff_dashboard'))
        
    return render_template('manage_assigned_trek.html', trek=trek)

@app.route('/complete_trek/<int:id>', methods=['POST'])
@login_required
def complete_trek(id):
    if session.get('role') != 'Staff':
        return redirect(url_for('login'))
        
    trek = Trek.query.get_or_404(id)
    
    if trek.staff_id != session.get('user_id'):
        flash('You do not have permission to modify this trek.', 'danger')
        return redirect(url_for('staff_dashboard'))
        
    # Update Trek Status
    trek.status = 'Completed'
    
    # Dynamically update all active bookings for this trek to 'Completed'
    # Assumes your Booking model has a trek_id column
    bookings_to_update = Booking.query.filter_by(trek_id=trek.id).all()
    for booking in bookings_to_update:
        if booking.status in ['Booked', 'Confirmed', 'Pending']:
            booking.status = 'Completed'
            
    db.session.commit()
    
    flash(f'Trek "{trek.name}" and its associated bookings have been marked as Completed.', 'success')
    return redirect(url_for('staff_dashboard'))


@app.route('/user')
@login_required
def user_dashboard():
    # Ensure only registered Users can access
    if session.get('role') != 'User':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('login'))

    # 1. Handle Filtering for Available Treks
    # Start with base query for Open treks
    query = Trek.query.filter_by(status='Open')
    
    # Get filter parameters from the URL (HTML Form GET request)
    selected_difficulty = request.args.get('difficulty')
    selected_location = request.args.get('location')

    if selected_difficulty and selected_difficulty != 'All':
        query = query.filter_by(difficulty=selected_difficulty)
    
    if selected_location and selected_location != 'All':
        query = query.filter_by(location=selected_location)
        
    available_treks = query.all()

    # Get unique locations dynamically from the database to populate the dropdown
    locations = db.session.query(Trek.location).distinct().all()
    unique_locations = [loc[0] for loc in locations]

    # 2. Retrieve User's Current Bookings
    # Assumes your Booking model has a backref to Trek (e.g., booking.trek.name)
    all_user_bookings = Booking.query.filter_by(user_id=session.get('user_id')).order_by(Booking.booking_date.desc()).all()
    
    # Split into Upcoming (Booked) and Past (Completed/Cancelled)
    upcoming_bookings = [b for b in all_user_bookings if b.status in ['Booked', 'Confirmed', 'Pending']]
    past_bookings = [b for b in all_user_bookings if b.status in ['Completed', 'Cancelled']]

    return render_template(
        'user_dashboard.html',
        available_treks=available_treks,
        upcoming_bookings=upcoming_bookings,
        past_bookings=past_bookings,
        unique_locations=unique_locations,
        selected_difficulty=selected_difficulty,
        selected_location=selected_location
    )

@app.route('/book_trek/<int:trek_id>', methods=['GET', 'POST'])
@login_required
def book_trek(trek_id):
    # Ensure only registered Users can make a booking
    if session.get('role') != 'User':
        flash('Only registered users can book treks.', 'danger')
        return redirect(url_for('login'))

    trek = Trek.query.get_or_404(trek_id)

    # 1. Check if the trek status is Open
    if trek.status != 'Open':
        flash('Registration is closed for this trek.', 'danger')
        return redirect(url_for('user_dashboard'))

    # 2. Check if there are available slots
    if trek.available_slots <= 0:
        flash('Sorry, this trek is fully booked.', 'warning')
        return redirect(url_for('user_dashboard'))

    # 3. Check for duplicate bookings by this user
    existing_booking = Booking.query.filter_by(
        user_id=session.get('user_id'), 
        trek_id=trek.id
    ).first()
    
    if existing_booking:
        flash('You have already booked this trek.', 'info')
        return redirect(url_for('user_dashboard'))

    # Handle the actual booking execution
    if request.method == 'POST':
        try:
            # 4. Create a new Booking record
            new_booking = Booking(
                user_id=session.get('user_id'),
                trek_id=trek.id,
                booking_date=datetime.utcnow(),
                status='Booked'
            )
            db.session.add(new_booking)

            # 5. Decrease the trek's available slots by 1
            trek.available_slots -= 1

            # Commit the transaction safely
            db.session.commit()
            flash(f'Successfully booked {trek.name}!', 'success')
            return redirect(url_for('user_dashboard'))
            
        except Exception as e:
            # Rollback in case of database errors (e.g., race conditions)
            db.session.rollback()
            flash('An error occurred while processing your booking. Please try again.', 'danger')
            return redirect(url_for('user_dashboard'))

    # If GET request, show confirmation page
    return render_template('confirm_booking.html', trek=trek)

@app.route('/view_booking/<int:id>')
@login_required
def view_booking(id):
    if session.get('role') != 'User':
        return redirect(url_for('login'))
        
    booking = Booking.query.get_or_404(id)
    
    # Security: Ensure the logged-in user actually owns this booking
    if booking.user_id != session.get('user_id'):
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('user_dashboard'))
        
    return render_template('view_booking.html', booking=booking)
            

if __name__ == '__main__':
    init_db(app)
    app.run(debug=True)