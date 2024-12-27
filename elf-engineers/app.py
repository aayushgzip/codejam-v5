from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_login import logout_user
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import pytz
from flask_mail import Mail, Message
import os
import random
import string
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, template_folder='templates')
app.secret_key = "your_secret_key"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAIL_SERVER'] = 'smtp.gmail.com' 
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('focusapp2524@gmail.com')
app.config['MAIL_PASSWORD'] = os.environ.get('focusapp2524ELF-ENG')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('focusapp2524@gmail.com') 
mail = Mail(app)


db = SQLAlchemy(app)
migrate = Migrate(app, db)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    class_sem = db.Column(db.String(50), nullable=False)
    college = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    streak = db.Column(db.Integer, default=0)
    gems = db.Column(db.Integer, default=0)
    last_focus_date = db.Column(db.Date, nullable=True)
    most_productive_day = db.Column(db.String(50), nullable=True)
    total_focus_time = db.Column(db.Integer, default=0)
    reset_token = db.Column(db.String(100), nullable=True)  # Add this column

@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        name = request.form.get('name')
        class_sem = request.form.get('class_sem')
        college = request.form.get('college')
        age = request.form.get('age')
        password = request.form.get('password')

       
        if not all([email, name, class_sem, college, age, password]):
            flash('All fields are required.', 'error')
            return redirect(url_for('register'))

        try:
            age = int(age)
        except ValueError:
            flash('Age must be a valid number.', 'error')
            return redirect(url_for('register'))

    
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already registered. Please login.', 'error')
            return redirect(url_for('home'))

        
        hashed_password = generate_password_hash(password)

        
        try:
            user = User(email=email, name=name, class_sem=class_sem, college=college, age=age, password=hashed_password)
            db.session.add(user)
            db.session.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('home'))
        except Exception as e:
            db.session.rollback()
            flash(f'Registration failed: {str(e)}', 'error')
            return redirect(url_for('register'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not email or not password:
            flash('Please provide both email and password.', 'error')
            return redirect(url_for('login'))

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['start_time'] = datetime.now(pytz.UTC)  # Store timezone-aware datetime
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password. Please try again.', 'error')
            return redirect(url_for('login'))
    
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please login first.', 'error')
        return redirect(url_for('home'))

    user = User.query.get(session['user_id'])
    if user:
        try:
            return render_template('dashboard.html', user=user)
        except Exception as e:
            flash('Error loading dashboard. Please try again.', 'error')
            print(f"Dashboard error: {str(e)}")  # Log the error
            return redirect(url_for('home'))
    else:
        session.pop('user_id', None)
        flash('User not found. Please login again.', 'error')
        return redirect(url_for('home'))

@app.route('/focus', methods=['POST'])
def focus():
    if 'user_id' not in session:
        return redirect(url_for('home'))

    user = User.query.get(session['user_id'])
    today = datetime.now(pytz.UTC).date()

    
    if user.last_focus_date == today:
        flash("You have already activated focus mode today!", 'warning')
        return redirect(url_for('dashboard'))

    user.last_focus_date = today
    user.streak += 1

    
    if user.streak % 7 == 0:
        user.gems += 50 if user.streak == 7 else 100

    
    user.most_productive_day = today.strftime('%A')
    db.session.commit()

    flash("Focus mode activated successfully!", 'success')
    return redirect(url_for('dashboard'))

@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if 'user_id' not in session:
        flash('Please login first.', 'error')
        return redirect(url_for('home'))

    user = User.query.get(session['user_id'])

    if request.method == 'POST':
        # Retrieve updated data from the form
        user.name = request.form.get('name')
        user.class_sem = request.form.get('class_sem')
        user.college = request.form.get('college')
        user.age = request.form.get('age')

        # Validate and update the database
        try:
            user.age = int(user.age)  # Ensure age is an integer
        except ValueError:
            flash('Age must be a valid number.', 'error')
            return redirect(url_for('edit_profile'))

        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('dashboard'))

    try:
        return render_template('edit_profile.html', user=user)
    except Exception as e:
        flash('Unable to load profile page. Please try again.', 'error')
        return redirect(url_for('home'))

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        if user:
            # Generate a random token
            reset_token = ''.join(random.choices(string.ascii_letters + string.digits, k=20))
            user.reset_token = reset_token
            
            try:
                db.session.commit()
                
                # Create reset password link
                reset_link = url_for('reset_password', token=reset_token, _external=True)
                
                # Setup email
                msg = Message(
                    subject="Password Reset Request",
                    sender=app.config['MAIL_DEFAULT_SENDER'],
                    recipients=[email]
                )
                msg.body = f"""
                Hello,
                
                You have requested to reset your password. Please click on the following link to reset your password:
                
                {reset_link}
                
                If you did not request this password reset, please ignore this email.
                
                Best regards,
                Focus App Team
                """
                
                # Send email
                mail.send(msg)
                flash('Password reset instructions have been sent to your email.', 'success')
                return redirect(url_for('home'))
                
            except Exception as e:
                print(f"Error sending email: {str(e)}")
                db.session.rollback()
                flash('There was an error sending the password reset email. Please verify your email settings or try again later.', 'error')
                return redirect(url_for('forgot_password'))
        else:
            flash('No account found with that email address.', 'error')
            return redirect(url_for('forgot_password'))

    return render_template('forgot_password.html')

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if not token:
        flash('Invalid reset token.', 'error')
        return redirect(url_for('home'))

    user = User.query.filter_by(reset_token=token).first()
    if not user:
        flash('Invalid or expired password reset token.', 'error')
        return redirect(url_for('home'))

    if request.method == 'POST':
        new_password = request.form.get('password')
        if not new_password:
            flash('Password cannot be empty.', 'error')
            return render_template('reset_password.html', token=token)

        # Hash the new password and update user
        try:
            user.password = generate_password_hash(new_password)
            user.reset_token = None  # Clear the reset token
            db.session.commit()
            flash('Your password has been reset successfully.', 'success')
            return redirect(url_for('home'))
        except Exception as e:
            db.session.rollback()
            flash('Error resetting password. Please try again.', 'error')
            return render_template('reset_password.html', token=token)

    return render_template('reset_password.html', token=token)



@app.route('/logout')
def logout():
    if 'start_time' in session:
        start_time = session.pop('start_time', None)
        
        if start_time:
            try:
                # Ensure start_time is timezone-aware
                if start_time.tzinfo is None:
                    start_time = pytz.UTC.localize(start_time)  # Localize to UTC

                # Ensure current_time is timezone-aware as well
                current_time = datetime.now(pytz.UTC)

                # Calculate the duration in minutes
                focus_duration = int((current_time - start_time).total_seconds() // 60)  # Convert seconds to minutes

                user = User.query.get(session.get('user_id'))
                if user:
                    # Ensure total_focus_time is initialized if None
                    if user.total_focus_time is None:
                        user.total_focus_time = 0
                    user.total_focus_time += focus_duration
                    db.session.commit()

            except (TypeError, AttributeError) as e:
                # Log the error but continue with logout
                print(f"Error during focus time calculation: {e}")
                # Ensure session is cleared even if there's an error
                pass

        session.pop('user_id', None)
        flash('Logged out successfully.', 'success')

    return redirect(url_for('home'))
@app.route('/About')
def About():
    return render_template('About.html')
if __name__ == "__main__":
    with app.app_context():
        db.create_all() 
    app.run(debug=True)
