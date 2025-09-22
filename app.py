import os
import random
import string
from datetime import datetime, timedelta
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_migrate import Migrate
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
from config import Config
from models import db, User, Coupon, ScanLog

# ---------------- APP INIT ----------------
app = Flask(__name__)
app.config.from_object(Config)

# Database & migration
db.init_app(app)
migrate = Migrate(app, db)

# Flask-Login
login = LoginManager(app)
login.login_view = 'login'

@login.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ---------------- UTILITY ----------------
def random_code():
    percent = random.choice([10, 15, 20, 25, 30])
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"OFF{percent}-{suffix}", percent

# ---------------- ROUTES ----------------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/offers')
def offers():
    return render_template('index1.html')

@app.route('/test_flash')
def test_flash():
    flash('This is a test message!', 'danger')
    return render_template('auth/login.html')

# ---------------- AUTH ----------------
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username'].strip()
        email = request.form['email'].strip().lower()
        password = request.form['password']
        confirm = request.form.get('confirm_password')
        if confirm and password != confirm:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('signup'))

        role = request.form.get('role', 'user')
        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash('User already exists.', 'warning')
            return redirect(url_for('signup'))

        u = User(username=username, email=email, role=role)
        u.set_password(password)
        db.session.add(u)
        db.session.commit()
        flash('Account created. Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('auth/signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        print(f"DEBUG: Login attempt - Username: {username}")
        
        u = User.query.filter_by(username=username).first()
        print(f"DEBUG: User found: {u is not None}")
        
        if u:
            print(f"DEBUG: User role: {u.role}")
            password_correct = u.check_password(password)
            print(f"DEBUG: Password correct: {password_correct}")
            
            if password_correct:
                login_user(u)
                flash('Logged in successfully.', 'success')
                return redirect(url_for('dashboard'))
        
        print("DEBUG: Adding flash message for invalid login")
        flash('Invalid username or password.', 'danger')
        print("DEBUG: Flash message added, rendering login template")
    
    return render_template('auth/login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# ---------------- DASHBOARD ----------------
@app.route('/dashboard')
@login_required
def dashboard():
    role = getattr(current_user, 'role', None)
    print(f"DEBUG: Current user: {current_user.username}, Role: {role}")  # Debug line
    
    if role == 'admin':
        coupons = Coupon.query.order_by(Coupon.created_at.desc()).all()
        users = User.query.order_by(User.id).all()
        total_bags = sum(user.bags_sold for user in users if user.role == 'sponsor')
        return render_template('dashboard/admin.html', coupons=coupons, users=users, bags_sold=total_bags)
    
    if role == 'sponsor':
        coupons = Coupon.query.order_by(Coupon.created_at.desc()).all()
        return render_template('dashboard/sponsor.html', coupons=coupons, bags_sold=current_user.bags_sold)
    
    if role == 'vendor':
        coupons = Coupon.query.order_by(Coupon.created_at.desc()).all()
        return render_template('dashboard/vendor.html', coupons=coupons)
    
    return render_template('dashboard/user.html')

# ---------------- ADMIN ACTIONS ----------------
@app.route('/update_bags', methods=['POST'])
@login_required
def update_bags():
    if current_user.role != 'admin':
        flash("Unauthorized", "danger")
        return redirect(url_for('dashboard'))

    user_id = request.form.get('user_id')
    bags_val = request.form.get('bags_sold')
    if not user_id:
        flash("Missing user id.", "warning")
        return redirect(url_for('dashboard'))

    try:
        uid = int(user_id)
        new_bags = int(bags_val)
        if new_bags < 0:
            raise ValueError
    except:
        flash("Invalid input.", "danger")
        return redirect(url_for('dashboard'))

    user = User.query.get(uid)
    if not user or user.role != 'sponsor':
        flash("Invalid user.", "warning")
        return redirect(url_for('dashboard'))

    user.bags_sold = new_bags
    db.session.commit()
    flash(f"Bags sold updated for {user.username}.", "success")
    return redirect(url_for('dashboard'))

@app.route('/admin/change_role', methods=['POST'])
@login_required
def change_role():
    if current_user.role != 'admin':
        flash("Unauthorized", "danger")
        return redirect(url_for('dashboard'))

    user_id = request.form.get('user_id')
    new_role = request.form.get('role')
    if not user_id or not new_role:
        flash("Missing parameters.", "warning")
        return redirect(url_for('dashboard'))

    try:
        uid = int(user_id)
    except:
        flash("Invalid user id.", "danger")
        return redirect(url_for('dashboard'))

    user = User.query.get(uid)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for('dashboard'))

    user.role = new_role
    if new_role != 'sponsor':
        user.bags_sold = 0
    db.session.commit()
    flash(f"{user.username}'s role updated to {new_role}.", "success")
    return redirect(url_for('dashboard'))

@app.route('/admin/change_password', methods=['POST'])
@login_required
def change_password():
    if current_user.role != 'admin':
        flash("Unauthorized", "danger")
        return redirect(url_for('dashboard'))

    user_id = request.form.get('user_id')
    new_password = request.form.get('new_password') or request.form.get('password')
    confirm_password = request.form.get('confirm_password')

    if not user_id or not new_password or not confirm_password:
        flash("Missing parameters.", "warning")
        return redirect(url_for('dashboard'))

    if new_password != confirm_password:
        flash("Passwords do not match.", "danger")
        return redirect(url_for('dashboard'))

    try:
        uid = int(user_id)
    except:
        flash("Invalid user id.", "danger")
        return redirect(url_for('dashboard'))

    user = User.query.get(uid)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for('dashboard'))

    user.set_password(new_password)
    db.session.commit()
    flash(f"{user.username}'s password updated.", "success")
    return redirect(url_for('dashboard'))

@app.route('/admin/delete_user', methods=['POST'])
@login_required
def delete_user():
    if current_user.role != 'admin':
        flash("Unauthorized", "danger")
        return redirect(url_for('dashboard'))

    user_id = request.form.get('user_id')
    confirm_delete = request.form.get('confirm_delete')

    if not user_id or confirm_delete != 'DELETE':
        flash("Invalid confirmation. Type 'DELETE' to confirm.", "danger")
        return redirect(url_for('dashboard'))

    try:
        uid = int(user_id)
    except:
        flash("Invalid user id.", "danger")
        return redirect(url_for('dashboard'))

    user = User.query.get(uid)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for('dashboard'))

    # Prevent deleting the admin account
    if user.username == 'admin':
        flash("Cannot delete admin account.", "danger")
        return redirect(url_for('dashboard'))

    # Delete associated scan logs first
    scan_logs = ScanLog.query.join(Coupon).filter(Coupon.created_by_id == user.id).all()
    for log in scan_logs:
        db.session.delete(log)

    # Delete associated coupons
    coupons = Coupon.query.filter_by(created_by_id=user.id).all()
    for coupon in coupons:
        db.session.delete(coupon)

    # Delete the user
    username = user.username
    db.session.delete(user)
    db.session.commit()
    
    flash(f"Account '{username}' has been permanently deleted.", "success")
    return redirect(url_for('dashboard'))

# ---------------- COUPON ROUTES ----------------
@app.route('/generate_coupon', methods=['POST'])
@login_required
def generate_coupon_route():
    print(f"DEBUG: User {current_user.username} (ID: {current_user.id}) attempting to generate coupon")
    
    one_week_ago = datetime.utcnow() - timedelta(days=7)
    
    # Check for recent coupons by this user
    recent_coupon = Coupon.query.filter(
        Coupon.created_by_id == current_user.id,
        Coupon.created_at >= one_week_ago
    ).order_by(Coupon.created_at.desc()).first()
    
    print(f"DEBUG: Recent coupon found: {recent_coupon is not None}")
    if recent_coupon:
        print(f"DEBUG: Recent coupon created at: {recent_coupon.created_at}")
        print(f"DEBUG: One week ago: {one_week_ago}")
        print(f"DEBUG: Current time: {datetime.utcnow()}")

    if recent_coupon:
        next_allowed_time = recent_coupon.created_at + timedelta(days=7)
        return jsonify({
            'error': 'You can only generate one coupon per week.',
            'next_allowed': next_allowed_time.strftime('%Y-%m-%d %H:%M:%S')
        }), 400

    # Generate new coupon
    code, discount = random_code()
    c = Coupon(code=code, discount=discount, created_by_id=current_user.id, created_at=datetime.utcnow())
    db.session.add(c)
    db.session.commit()
    
    print(f"DEBUG: New coupon created: {code}")

    return jsonify({
        'code': code,
        'discount': discount,
        'message': "🎉 Coupon generated! New code after a week."
    })

@app.route('/scan/<code>')
def view_coupon(code):
    coupon = Coupon.query.filter_by(code=code).first_or_404()
    coupon.scanned_count = (coupon.scanned_count or 0) + 1
    cl = ScanLog(
        coupon_id=coupon.id,
        user_agent=request.headers.get('User-Agent'),
        ip=request.remote_addr
    )
    db.session.add(cl)
    db.session.commit()
    return render_template('coupon/view_coupon.html', coupon=coupon)

@app.route('/approve_coupon', methods=['POST'])
@login_required
def approve_coupon():
    if current_user.role not in ('vendor', 'sponsor', 'admin'):
        return jsonify({'error': 'not-authorized'}), 403
    code = request.json.get('code')
    c = Coupon.query.filter_by(code=code).first()
    if not c:
        return jsonify({'error': 'not-found'}), 404
    c.status = 'approved'
    c.approved_by = current_user.role
    c.approved_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'ok': True})

@app.route('/reject_coupon', methods=['POST'])
@login_required
def reject_coupon():
    if current_user.role not in ('vendor', 'sponsor', 'admin'):
        return jsonify({'error': 'not-authorized'}), 403
    code = request.json.get('code')
    c = Coupon.query.filter_by(code=code).first()
    if not c:
        return jsonify({'error': 'not-found'}), 404
    c.status = 'rejected'
    db.session.commit()
    return jsonify({'ok': True})

@app.route('/redeem', methods=['POST'])
@login_required
def redeem():
    code = request.form.get('code')
    c = Coupon.query.filter_by(code=code).first()
    if not c:
        return render_template('coupon/redeem_result.html', success=False, message='Coupon not found')
    if c.status != 'approved':
        return render_template('coupon/redeem_result.html', success=False, message='Coupon not active')
    if c.status == 'used':
        return render_template('coupon/redeem_result.html', success=False, message='Coupon already used')
    c.status = 'used'
    c.used_at = datetime.utcnow()
    db.session.commit()
    return render_template('coupon/redeem_result.html', success=True, coupon=c)

# ---------------- RUN APP ----------------
# ---------------- RUN APP ----------------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # Ensure admin exists, create only if missing
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            # Create new admin with default credentials
            default_admin_password = os.environ.get('ADMIN_PASSWORD', 'ChangeMe123')  # Use env variable if set
            default_admin_email = os.environ.get('ADMIN_EMAIL', 'admin@carrykaro.com')
            
            admin = User(username='admin', email=default_admin_email, role='admin')
            admin.set_password(default_admin_password)
            db.session.add(admin)
            db.session.commit()
            print("Admin user created - check database for credentials")
        else:
            print("Admin user already exists in database")
        
    app.run(debug=True)
