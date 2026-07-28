from app import app
from models import db, User

with app.app_context():

    db.create_all()
    
    admin = User.query.filter_by(role='Admin').first()
    
    if not admin:

        new_admin = User(
            full_name='Admin Superuser',
            email='admin@gmail.com',
            password='@dmin123',
            role='Admin',
            status='Approved'
        )
        db.session.add(new_admin)
        db.session.commit()
        print("Database tables created and Admin user added successfully!")
    else:
        print("Database already initialized. Admin exists.")