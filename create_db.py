from models import db, User
from werkzeug.security import generate_password_hash

def init_db(app):
    """Creates database tables and the default Admin user if they don't exist."""
    with app.app_context():
        db.create_all()
        
        admin = User.query.filter_by(role='Admin').first()
        
        if not admin:
            hashed_pw = generate_password_hash('@dmin123')
            new_admin = User(
                full_name='Admin',
                email='admin@gmail.com',
                password=hashed_pw,
                role='Admin',
                status='Approved'
            )
            db.session.add(new_admin)
            db.session.commit()
            print("Database check: Tables created and default Admin verified!")
        else:
            print("Database check: Database already exists. Admin found.")