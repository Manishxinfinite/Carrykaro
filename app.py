import os
import random
import string
from datetime import datetime, timedelta
from flask import Flask, render_template, redirect, url_for, request, flash, send_from_directory, jsonify
from flask_migrate import Migrate
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
from config import Config
from models import db, User, Coupon, ScanLog
import qrcode

# Use ststic as the Flask static folder to match your preference
app = Flask(__name__, static_folder='ststic')
app.config.from_object(Config)

# ensure qrcode folder exists
os.makedirs(app.config['QR_FOLDER'], exist_ok=True)

# init db
db.init_app(app)
migrate = Migrate(app, db)

login = LoginManager(app)
login.login_view = 'login'


@login.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# --- Utility functions

def random_code():
    # OFF{percent}-{6 chars}
    percent = random.choice([10, 15, 20, 25, 30])
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"OFF{percent}-{suffix}", percent


def generate_qr_image(code):
    qr = qrcode.QRCode(box_size=10, border=2)
    url = url_for('view_coupon', code=code, _external=True)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image()
    filename = f"{code}.png"
    path = os.path.join(app.config['QR_FOLDER'], filename)
    img.save(path)
    return filename


# --- Routes

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/offers')
def offers():
    return render_template('index1.html')


# ---------------- AUTH ----------------
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username'].strip()
        email = request.form['email'].strip().lower()
        password = request.form['password']
        # basic server-side confirm password handling if front-end used 'confirm_password'
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
        u = User.query.filter_by(username=username).first()
        if u and u.check_password(password):
            login_user(u)
            flash('Logged in successfully.', 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid username or password.', 'danger')
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
    if role == 'admin':
        coupons = Coupon.query.order_by(Coupon.created_at.desc()).all()
        users = User.query.order_by(User.id).all()
        return render_template('dashboard/admin.html', coupons=coupons, users=users)
    if role == 'vendor':
        coupons = Coupon.query.order_by(Coupon.created_at.desc()).all()
        return render_template('dashboard/vendor.html', coupons=coupons)
    if role == 'sponsor':
        coupons = Coupon.query.order_by(Coupon.created_at.desc()).all()
        return render_template('dashboard/sponsor.html', coupons=coupons)
    # user
    return render_template('dashboard/user.html')


# ---------------- USER MANAGEMENT (ADMIN) ----------------
@app.route('/admin/change_role', methods=['POST'])
@login_required
def change_role():
    # only admins allowed
    if getattr(current_user, 'role', None) != 'admin':
        flash('Not authorized', 'danger')
        return redirect(url_for('dashboard'))

    user_id = request.form.get('user_id')
    new_role = request.form.get('role')
    if not user_id or not new_role:
        flash('Missing parameters for role change.', 'warning')
        return redirect(url_for('dashboard'))

    # ensure user_id is int
    try:
        uid = int(user_id)
    except (ValueError, TypeError):
        flash('Invalid user id.', 'danger')
        return redirect(url_for('dashboard'))

    user = User.query.get(uid)
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('dashboard'))

    user.role = new_role
    db.session.commit()
    flash(f"Role for {user.username} updated to {new_role}.", 'success')
    return redirect(url_for('dashboard'))


@app.route('/admin/change_password', methods=['POST'])
@login_required
def change_password():
    # only admins allowed
    if getattr(current_user, 'role', None) != 'admin':
        flash('Not authorized', 'danger')
        return redirect(url_for('dashboard'))

    user_id = request.form.get('user_id')
    new_password = request.form.get('new_password') or request.form.get('password')
    confirm_password = request.form.get('confirm_password')

    if not user_id or not new_password or not confirm_password:
        flash('Missing parameters for password change.', 'warning')
        return redirect(url_for('dashboard'))

    if new_password != confirm_password:
        flash('Passwords do not match.', 'danger')
        return redirect(url_for('dashboard'))

    try:
        uid = int(user_id)
    except (ValueError, TypeError):
        flash('Invalid user id.', 'danger')
        return redirect(url_for('dashboard'))

    user = User.query.get(uid)
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('dashboard'))

    user.set_password(new_password)
    db.session.commit()
    flash(f"Password for {user.username} has been updated.", 'success')
    return redirect(url_for('dashboard'))


# ---------------- COUPONS ----------------
@app.route('/generate_coupon', methods=['POST'])
@login_required
def generate_coupon_route():
    # Only allow users to generate 1 coupon per week
    one_week_ago = datetime.utcnow() - timedelta(days=7)
    recent_coupon = Coupon.query.filter(
        Coupon.created_by_id == current_user.id,
        Coupon.created_at >= one_week_ago
    ).first()

    if recent_coupon:
        return jsonify({
            'error': 'You can only generate one coupon per week.',
            'next_allowed': (recent_coupon.created_at + timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
        }), 400

    # Generate new coupon
    code, discount = random_code()
    c = Coupon(code=code, discount=discount, created_by_id=current_user.id, created_at=datetime.utcnow())
    db.session.add(c)
    db.session.commit()

    filename = generate_qr_image(code)
    qr_url = url_for('static_qr', filename=filename, _external=True)

    # Add a message to show user
    message = "🎉 QR generated! Please take a screenshot. A new code will be generated after a week."

    return jsonify({
        'code': code,
        'discount': discount,
        'qr': qr_url,
        'message': message
    })




@app.route('/ststic/qrcodes/<path:filename>')
def static_qr(filename):
    return send_from_directory(app.config['QR_FOLDER'], filename)


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
    if getattr(current_user, 'role', None) not in ('vendor', 'sponsor', 'admin'):
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
    if getattr(current_user, 'role', None) not in ('vendor', 'sponsor', 'admin'):
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
    # mark used
    c.status = 'used'
    c.used_at = datetime.utcnow()
    db.session.commit()
    return render_template('coupon/redeem_result.html', success=True, coupon=c)


# --- Run app
if __name__ == '__main__':
    with app.app_context():
        db.create_all()   # create tables automatically if missing
    app.run(debug=True)
