from app import app
from models import db, User

# We use app_context() because SQLAlchemy needs to know which Flask app it is working with
with app.app_context():
    # 1. Create all tables defined in models.py
    db.create_all()
    
    # 2. Check if an Admin already exists
    admin = User.query.filter_by(role='Admin').first()
    
    if not admin:
        # 3. Create the default Admin user
        new_admin = User(
            full_name='Admin Superuser',
            email='admin@trek.com',
            password='adminpassword', # We will hash this securely in Phase 4
            role='Admin',
            status='Approved'
        )
        db.session.add(new_admin)
        db.session.commit()
        print("Database tables created and Admin user added successfully!")
    else:
        print("Database already initialized. Admin exists.")