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
            
            if user.status == 'Pending':
                flash('Your staff account is pending admin approval.')
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
        # Extract data from the form
        new_trek = Trek(
            name=request.form.get('name'),
            location=request.form.get('location'),
            difficulty=request.form.get('difficulty'),
            duration=request.form.get('duration'),
            available_slots=request.form.get('slots'),
            status=request.form.get('status')
        )
        
        # Save to database
        db.session.add(new_trek)
        db.session.commit()
        
        flash('Trek added successfully!', 'success')
        return redirect(url_for('manage_treks'))
        
    return render_template('add_trek.html')

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
        
        db.session.commit()
        flash('Trek updated successfully!', 'success')
        return redirect(url_for('manage_treks'))
        
    return render_template('edit_trek.html', trek=trek)

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


@app.route('/staff')
@login_required
def staff_dashboard():
    # Strict check: Only Staff role can access
    if session.get('role') != 'Staff':
        flash('Unauthorized access. Staff privileges required.')
        return redirect(url_for('login'))
        
    # Check if staff is approved by querying the database using session user_id
    user = User.query.get(session['user_id'])
    if user.status == 'Pending':
        flash('Access denied. Your staff account is pending Admin approval.')
        session.clear() # Log them out forcefully
        return redirect(url_for('login'))
        
    return render_template('staff_dashboard.html')


@app.route('/user')
@login_required
def user_dashboard():
    # Strict check: Only User role can access
    if session.get('role') != 'User':
        flash('Unauthorized access. User privileges required.')
        return redirect(url_for('login'))
        
    return render_template('user_dashboard.html')

if __name__ == '__main__':
    init_db(app)
    app.run(debug=True)