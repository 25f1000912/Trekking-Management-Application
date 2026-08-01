from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from models import db, User, Trek, Booking
from create_db import init_db

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
    # Ensure only Staff can access
    if session.get('role') != 'Staff':
        return redirect(url_for('login'))
        
    trek = Trek.query.get_or_404(id)
    
    # Ensure the staff member manages this specific trek
    if trek.staff_id != session.get('user_id'):
        flash('You do not have permission to modify this trek.', 'danger')
        return redirect(url_for('staff_dashboard'))
        
    # Update status to Completed
    trek.status = 'Completed'
    db.session.commit()
    
    flash(f'Trek "{trek.name}" has been marked as Completed. No new registrations are allowed.', 'success')
    return redirect(url_for('staff_dashboard'))


@app.route('/user')
@login_required
def user_dashboard():
    # Strict check: Only User role can access
    if session.get('role') != 'User':
        flash('Unauthorized access. User privileges required.')
        return redirect(url_for('login'))
        
    return render_template('user_dashboard.html')

@app.route('/book_trek/<int:trek_id>', methods=['GET', 'POST'])
@login_required
def book_trek(trek_id):
    trek = Trek.query.get_or_404(trek_id)
    
    if request.method == 'POST':
        # CHECK: Prevent booking if the trek is not Open
        if trek.status != 'Open':
            flash('Registration is closed. This trek has already been completed or is no longer accepting participants.', 'danger')
            return redirect(url_for('user'))
            

if __name__ == '__main__':
    init_db(app)
    app.run(debug=True)