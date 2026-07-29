from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User
from create_db import init_db

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.sqlite'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'your_super_secret_key' 

db.init_app(app)

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
                return redirect('/admin_dashboard')
            elif user.role == 'Staff':
                return redirect('/staff_dashboard')
            else:
                return redirect('/user_dashboard')
                
        else:
            flash('Invalid email or password.')
            return redirect(url_for('login'))
            
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.')
    return redirect(url_for('login'))


@app.route('/admin_dashboard')
def admin_dashboard():
    return render_template('admin_dashboard.html')

@app.route('/staff_dashboard')
def staff_dashboard():
    return render_template('staff_dashboard.html')

@app.route('/user_dashboard')
def user_dashboard():
    return render_template('user_dashboard.html')

if __name__ == '__main__':
    init_db(app)
    app.run(debug=True)