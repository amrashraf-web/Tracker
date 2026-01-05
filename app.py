from flask import Flask, render_template, request, jsonify, make_response, send_from_directory, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from sqlalchemy import create_engine, text
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
import uuid
import base64
import os
import re
from dotenv import load_dotenv
import pytz
from werkzeug.utils import secure_filename
from PIL import Image

load_dotenv()

app = Flask(__name__, template_folder='frontend/templates', static_folder='frontend/static')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Image upload configuration
UPLOAD_FOLDER = 'frontend/static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
CORS(app)

EGYPT_TZ = pytz.timezone('Africa/Cairo')
UTC_TZ = pytz.UTC

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ============ MODELS ============

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    # Relationships
    smtp_configs = db.relationship('SMTPConfig', backref='user', lazy=True, cascade='all, delete-orphan')
    email_tracking = db.relationship('EmailTracking', backref='user', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'is_admin': self.is_admin,
            'created_at': to_egypt_dict_time(self.created_at)
        }

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class SMTPConfig(db.Model):
    __tablename__ = 'smtp_configs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    host = db.Column(db.String(255), nullable=False)
    port = db.Column(db.Integer, nullable=False, default=587)
    username = db.Column(db.String(255), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    use_tls = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'host': self.host,
            'port': self.port,
            'username': self.username,
            'password': '********',  # Hide password
            'use_tls': self.use_tls,
            'created_at': to_egypt_dict_time(self.created_at)
        }

class EmailTracking(db.Model):
    __tablename__ = 'email_tracking'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    tracking_id = db.Column(db.String(64), unique=True, nullable=False, index=True)
    recipient_email = db.Column(db.String(255), nullable=False, index=True)
    subject = db.Column(db.Text, nullable=True)
    open_count = db.Column(db.Integer, default=0)
    click_count = db.Column(db.Integer, default=0)
    last_open_time = db.Column(db.DateTime, nullable=True)
    last_click_time = db.Column(db.DateTime, nullable=True)
    last_ip = db.Column(db.String(100), nullable=True)
    last_port = db.Column(db.String(10), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: get_egypt_time().replace(tzinfo=None))

    # Relationships
    open_events = db.relationship('OpenEvent', backref='tracking', lazy=True, cascade='all, delete-orphan')
    click_events = db.relationship('ClickEvent', backref='tracking', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'tracking_id': self.tracking_id,
            'recipient_email': self.recipient_email,
            'subject': self.subject,
            'open_count': self.open_count,
            'click_count': self.click_count,
            'last_open_time': to_egypt_dict_time(self.last_open_time),
            'last_click_time': to_egypt_dict_time(self.last_click_time),
            'last_ip': self.last_ip,
            'last_port': self.last_port,
            'created_at': to_egypt_dict_time(self.created_at)
        }

class ClickEvent(db.Model):
    __tablename__ = 'click_events'
    id = db.Column(db.Integer, primary_key=True)
    tracking_id = db.Column(db.String(64), db.ForeignKey('email_tracking.tracking_id'), nullable=False, index=True)
    click_time = db.Column(db.DateTime, default=lambda: get_egypt_time().replace(tzinfo=None), nullable=False)
    ip_address = db.Column(db.String(100), nullable=True)
    port = db.Column(db.String(10), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'tracking_id': self.tracking_id,
            'click_time': to_egypt_dict_time(self.click_time),
            'ip_address': self.ip_address,
            'port': self.port,
            'user_agent': self.user_agent
        }

class OpenEvent(db.Model):
    __tablename__ = 'open_events'
    id = db.Column(db.Integer, primary_key=True)
    tracking_id = db.Column(db.String(64), db.ForeignKey('email_tracking.tracking_id'), nullable=False, index=True)
    open_time = db.Column(db.DateTime, default=lambda: get_egypt_time().replace(tzinfo=None), nullable=False)
    ip_address = db.Column(db.String(100), nullable=True)
    port = db.Column(db.String(10), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'tracking_id': self.tracking_id,
            'open_time': to_egypt_dict_time(self.open_time),
            'ip_address': self.ip_address,
            'port': self.port,
            'user_agent': self.user_agent
        }

# ============ UTILITY FUNCTIONS ============

def get_egypt_time():
    return datetime.datetime.now(EGYPT_TZ)

def convert_to_egypt_time(utc_time):
    if utc_time is None:
        return None
    if utc_time.tzinfo is None:
        utc_time = UTC_TZ.localize(utc_time)
    return utc_time.astimezone(EGYPT_TZ)

def to_egypt_dict_time(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        egypt_dt = EGYPT_TZ.localize(dt)
    else:
        egypt_dt = dt.astimezone(EGYPT_TZ)
    return egypt_dt.strftime('%Y-%m-%dT%H:%M:%S%z')

def get_client_ip():
    x_forwarded_for = request.headers.get('X-Forwarded-For', '')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.remote_addr

def get_client_port():
    try:
        port = request.environ.get('REMOTE_PORT')
        if port:
            return str(port)
        forwarded_port = request.headers.get('X-Forwarded-Port')
        if forwarded_port:
            return forwarded_port
        return None
    except Exception:
        return None

def generate_tracking_id():
    return uuid.uuid4().hex

def create_email_body_with_image(image_url, tracking_id, redirect_url='https://www.google.com', body_text=""):
    base_url = request.url_root.rstrip('/')
    if image_url and not image_url.startswith('http'):
        image_url = f"{base_url}/{image_url.lstrip('/')}"

    click_tracking_url = f"{base_url}/click/{tracking_id}?redirect={redirect_url}"
    pixel_url = f"{base_url}/track/{tracking_id}.gif"

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Email</title>
    </head>
    <body style="margin:0; padding:0; font-family: Arial, sans-serif; line-height:1.6; color:#333;">
        <p style="margin:0 0 12px 0;">{body_text}</p>
        {f"<p><a href='{click_tracking_url}' target='_blank'><img src='{image_url}' alt='Email Image' style='max-width:200px; max-height:200px; height:auto; width:auto;'></a></p>" if image_url else ""}
        <img src="{pixel_url}" width="1" height="1" style="display:none;" alt="">
    </body>
    </html>
    """

    return html_body, click_tracking_url

# ============ AUTHENTICATION ROUTES ============

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({'success': False, 'message': 'Username and password required'}), 400

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            return jsonify({'success': True, 'message': 'Login successful', 'user': user.to_dict()})
        else:
            return jsonify({'success': False, 'message': 'Invalid username or password'}), 401

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')

        if not all([username, email, password]):
            return jsonify({'success': False, 'message': 'All fields required'}), 400

        if User.query.filter_by(username=username).first():
            return jsonify({'success': False, 'message': 'Username already exists'}), 400

        if User.query.filter_by(email=email).first():
            return jsonify({'success': False, 'message': 'Email already exists'}), 400

        user = User(username=username, email=email)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        login_user(user)
        return jsonify({'success': True, 'message': 'Registration successful', 'user': user.to_dict()})

    return render_template('register.html')

@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({'success': True, 'message': 'Logged out successfully'})

@app.route('/api/me')
@login_required
def get_current_user():
    return jsonify({'success': True, 'user': current_user.to_dict()})

# ============ USER MANAGEMENT (ADMIN ONLY) ============

@app.route('/api/admin/users', methods=['GET'])
@login_required
def get_all_users():
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Admin access required'}), 403

    users = User.query.all()
    return jsonify({'success': True, 'users': [u.to_dict() for u in users]})

@app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
@login_required
def delete_user(user_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Admin access required'}), 403

    if user_id == current_user.id:
        return jsonify({'success': False, 'message': 'Cannot delete yourself'}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'message': 'User not found'}), 404

    db.session.delete(user)
    db.session.commit()

    return jsonify({'success': True, 'message': 'User deleted successfully'})

@app.route('/api/admin/users/<int:user_id>/toggle-admin', methods=['POST'])
@login_required
def toggle_admin(user_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Admin access required'}), 403

    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'message': 'User not found'}), 404

    user.is_admin = not user.is_admin
    db.session.commit()

    return jsonify({'success': True, 'message': 'Admin status updated', 'user': user.to_dict()})

# ============ SMTP CONFIG ROUTES ============

@app.route('/api/smtp/config', methods=['GET'])
@login_required
def get_smtp_config():
    config = SMTPConfig.query.filter_by(user_id=current_user.id).first()

    if config:
        return jsonify({'success': True, 'config': config.to_dict()})
    return jsonify({'success': False, 'message': 'No SMTP configuration found'})

@app.route('/api/smtp/config', methods=['POST'])
@login_required
def save_smtp_config():
    data = request.get_json()

    required_fields = ['host', 'port', 'username', 'password']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'success': False, 'message': f'{field} is required'}), 400

    # Delete existing config for this user
    SMTPConfig.query.filter_by(user_id=current_user.id).delete()

    config = SMTPConfig(
        user_id=current_user.id,
        host=data['host'],
        port=int(data['port']),
        username=data['username'],
        password=data['password'],
        use_tls=data.get('use_tls', True)
    )

    db.session.add(config)
    db.session.commit()

    return jsonify({'success': True, 'message': 'SMTP configuration saved successfully'})

@app.route('/api/smtp/test', methods=['POST'])
@login_required
def test_smtp_config():
    data = request.get_json()
    test_email = data.get('test_email')

    if not test_email:
        return jsonify({'success': False, 'message': 'Test email is required'}), 400

    config = SMTPConfig.query.filter_by(user_id=current_user.id).first()
    if not config:
        return jsonify({'success': False, 'message': 'No SMTP configuration found'}), 400

    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        msg = MIMEMultipart()
        msg['From'] = config.username
        msg['To'] = test_email
        msg['Subject'] = 'SMTP Test Email'

        body = 'This is a test email from Simple Email Tracker.'
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP(config.host, config.port)
        if config.use_tls:
            server.starttls()
        server.login(config.username, config.password)
        server.send_message(msg)
        server.quit()

        return jsonify({'success': True, 'message': 'Test email sent successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'SMTP test failed: {str(e)}'}), 500

# ============ EMAIL SENDING ROUTES ============

@app.route('/api/send-email', methods=['POST'])
@login_required
def send_email():
    data = request.get_json()

    subject = data.get('subject', '')
    body_text = data.get('body', '')
    image_url = data.get('image_url', '')
    redirect_url = data.get('redirect_url', 'https://www.google.com')
    emails = data.get('emails', [])

    if not emails:
        return jsonify({'success': False, 'message': 'No recipient emails provided'}), 400

    if not image_url:
        return jsonify({'success': False, 'message': 'No image provided'}), 400

    config = SMTPConfig.query.filter_by(user_id=current_user.id).first()
    if not config:
        return jsonify({'success': False, 'message': 'No SMTP configuration found'}), 400

    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        results = []

        for email in emails:
            try:
                tracking_id = generate_tracking_id()

                tracking = EmailTracking(
                    user_id=current_user.id,
                    tracking_id=tracking_id,
                    recipient_email=email,
                    subject=subject
                )
                db.session.add(tracking)

                email_body, click_url = create_email_body_with_image(image_url, tracking_id, redirect_url, body_text)

                msg = MIMEMultipart()
                msg['From'] = config.username
                msg['To'] = email
                msg['Subject'] = subject

                msg.attach(MIMEText(email_body, 'html'))

                server = smtplib.SMTP(config.host, config.port)
                if config.use_tls:
                    server.starttls()
                server.login(config.username, config.password)
                server.send_message(msg)
                server.quit()

                results.append({
                    'email': email,
                    'success': True,
                    'tracking_id': tracking_id,
                    'click_url': click_url
                })

            except Exception as e:
                results.append({
                    'email': email,
                    'success': False,
                    'error': str(e)
                })

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Processed {len(emails)} emails',
            'results': results
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Failed to send emails: {str(e)}'}), 500

# ============ TRACKING ROUTES ============

@app.route('/api/tracking', methods=['GET'])
@login_required
def get_tracking_data():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    per_page = 50

    query = EmailTracking.query

    # If not admin, only show own emails
    if not current_user.is_admin:
        query = query.filter_by(user_id=current_user.id)

    if search:
        query = query.filter(EmailTracking.recipient_email.contains(search))

    pagination = query.order_by(EmailTracking.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        'success': True,
        'data': [item.to_dict() for item in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page,
        'per_page': per_page
    })

@app.route('/api/tracking/<tracking_id>/details', methods=['GET'])
@login_required
def get_tracking_details(tracking_id):
    tracking = EmailTracking.query.filter_by(tracking_id=tracking_id).first()
    if not tracking:
        return jsonify({'success': False, 'message': 'Tracking record not found'}), 404

    # Check access
    if not current_user.is_admin and tracking.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Access denied'}), 403

    open_events = OpenEvent.query.filter_by(tracking_id=tracking_id).order_by(OpenEvent.open_time.desc()).all()
    click_events = ClickEvent.query.filter_by(tracking_id=tracking_id).order_by(ClickEvent.click_time.desc()).all()

    opens = [{'open_time': to_egypt_dict_time(e.open_time), 'ip': e.ip_address or 'Unknown', 'port': e.port or 'Unknown'} for e in open_events]
    clicks = [{'click_time': to_egypt_dict_time(e.click_time), 'ip': e.ip_address or 'Unknown', 'port': e.port or 'Unknown'} for e in click_events]

    return jsonify({
        'success': True,
        'tracking': tracking.to_dict(),
        'opens': opens,
        'clicks': clicks
    })

# ============ PUBLIC TRACKING (No auth needed) ============

@app.route('/click/<tracking_id>')
def track_click(tracking_id):
    try:
        tracking = EmailTracking.query.filter_by(tracking_id=tracking_id).first()

        if tracking:
            client_ip = get_client_ip()
            client_port = get_client_port()

            click_event = ClickEvent(
                tracking_id=tracking_id,
                click_time=get_egypt_time().replace(tzinfo=None),
                ip_address=client_ip,
                port=client_port,
                user_agent=request.headers.get('User-Agent', '')[:500]
            )
            db.session.add(click_event)

            tracking.click_count = (tracking.click_count or 0) + 1
            tracking.last_click_time = get_egypt_time().replace(tzinfo=None)
            tracking.last_ip = client_ip
            tracking.last_port = client_port

            db.session.commit()

        redirect_url = request.args.get('redirect', 'https://www.google.com')
        return redirect(redirect_url)

    except Exception as e:
        print(f"Click tracking error: {e}")
        redirect_url = request.args.get('redirect', 'https://www.google.com')
        return redirect(redirect_url)

@app.route('/track/<tracking_id>.gif')
def track_pixel(tracking_id):
    try:
        tracking = EmailTracking.query.filter_by(tracking_id=tracking_id).first()

        if tracking:
            client_ip = get_client_ip()
            client_port = get_client_port()

            open_event = OpenEvent(
                tracking_id=tracking_id,
                open_time=get_egypt_time().replace(tzinfo=None),
                ip_address=client_ip,
                port=client_port,
                user_agent=request.headers.get('User-Agent', '')[:500]
            )
            db.session.add(open_event)

            tracking.open_count = (tracking.open_count or 0) + 1
            tracking.last_open_time = get_egypt_time().replace(tzinfo=None)

            db.session.commit()

        gif_data = base64.b64decode('R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7')
        response = make_response(gif_data)
        response.headers.update({
            'Content-Type': 'image/gif',
            'Content-Length': str(len(gif_data)),
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0'
        })
        return response

    except Exception as e:
        print(f"Tracking error: {e}")
        gif_data = base64.b64decode('R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7')
        response = make_response(gif_data)
        response.headers['Content-Type'] = 'image/gif'
        return response

# ============ IMAGE UPLOAD ROUTES ============

@app.route('/static/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/upload-image', methods=['POST'])
@login_required
def upload_image():
    try:
        if 'image' not in request.files:
            return jsonify({'success': False, 'message': 'No image file provided'}), 400

        file = request.files['image']

        if file.filename == '':
            return jsonify({'success': False, 'message': 'No file selected'}), 400

        if not allowed_file(file.filename):
            return jsonify({'success': False, 'message': 'Invalid file type. Allowed: PNG, JPG, JPEG, GIF, WEBP'}), 400

        file.seek(0, os.SEEK_END)
        file_length = file.tell()
        if file_length > MAX_FILE_SIZE:
            return jsonify({'success': False, 'message': 'File too large. Maximum size: 5MB'}), 400

        file.seek(0)

        filename = str(uuid.uuid4()) + '.' + file.filename.rsplit('.', 1)[1].lower()
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        file.save(file_path)

        try:
            with Image.open(file_path) as img:
                width, height = img.size
        except Exception:
            width, height = None, None

        base_url = request.url_root.rstrip('/')
        image_url = f"{base_url}/static/uploads/{filename}"

        return jsonify({
            'success': True,
            'filename': filename,
            'url': image_url,
            'width': width,
            'height': height
        })

    except Exception as e:
        return jsonify({'success': False, 'message': f'Upload failed: {str(e)}'}), 500

# ============ ADMIN ROUTES ============

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/admin')
@login_required
def admin():
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
    return render_template('admin.html')

@app.route('/api/admin/clear-database', methods=['POST'])
@login_required
def clear_database():
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Admin access required'}), 403

    data = request.get_json(silent=True) or {}
    confirmation = data.get('confirmation', '').strip()

    if confirmation != 'DELETE ALL':
        return jsonify({'success': False, 'message': 'Invalid confirmation'}), 400

    try:
        with db.engine.connect() as conn:
            conn.execute(text("DELETE FROM click_events"))
            conn.execute(text("DELETE FROM open_events"))
            conn.execute(text("DELETE FROM email_tracking"))
            conn.commit()

        return jsonify({
            'success': True,
            'message': 'All tracking data has been deleted successfully'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Failed to clear database: {str(e)}'
        }), 500

# ============ DATABASE INITIALIZATION ============

def create_tables():
    with app.app_context():
        db.create_all()
        print("Database tables created successfully!")

if __name__ == '__main__':
    create_tables()
    app.run(host='0.0.0.0', port=5000, debug=True)