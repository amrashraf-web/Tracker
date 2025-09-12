from flask import Flask, render_template, request, jsonify, make_response,send_from_directory
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine, text
from flask_cors import CORS
import datetime
import uuid
import base64
import os
import re
from dotenv import load_dotenv
import pytz
from werkzeug.utils import secure_filename
import os
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

# Create upload directory if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
db = SQLAlchemy(app)
CORS(app)

EGYPT_TZ = pytz.timezone('Africa/Cairo')
UTC_TZ = pytz.UTC

@app.route('/static/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/upload-image', methods=['POST'])
def upload_image():
    try:
        if 'image' not in request.files:
            return jsonify({'success': False, 'message': 'No image file provided'}), 400

        file = request.files['image']

        if file.filename == '':
            return jsonify({'success': False, 'message': 'No file selected'}), 400

        if not allowed_file(file.filename):
            return jsonify({'success': False, 'message': 'Invalid file type. Allowed: PNG, JPG, JPEG, GIF, WEBP'}), 400

        # Check file size
        file.seek(0, os.SEEK_END)
        file_length = file.tell()
        if file_length > MAX_FILE_SIZE:
            return jsonify({'success': False, 'message': 'File too large. Maximum size: 5MB'}), 400

        file.seek(0)

        # Generate unique filename
        filename = str(uuid.uuid4()) + '.' + file.filename.rsplit('.', 1)[1].lower()
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        # Save file
        file.save(file_path)

        # Get image dimensions
        try:
            with Image.open(file_path) as img:
                width, height = img.size
        except Exception:
            width, height = None, None

        # Return file info
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


def get_egypt_time():
    """Get current time in Egypt timezone"""
    return datetime.datetime.now(EGYPT_TZ)

def convert_to_egypt_time(utc_time):
    """Convert UTC time to Egypt time"""
    if utc_time is None:
        return None
    if utc_time.tzinfo is None:
        utc_time = UTC_TZ.localize(utc_time)
    return utc_time.astimezone(EGYPT_TZ)

def to_egypt_dict_time(dt):
    """Convert datetime to Egypt timezone for API responses"""
    if dt is None:
        return None

    # If dt is naive (no timezone), assume it's already in Egypt time
    if dt.tzinfo is None:
        egypt_dt = EGYPT_TZ.localize(dt)
    else:
        egypt_dt = dt.astimezone(EGYPT_TZ)

    # Return ISO format that JavaScript can parse correctly
    return egypt_dt.strftime('%Y-%m-%dT%H:%M:%S%z')
# Models

class SMTPConfig(db.Model):
    __tablename__ = 'smtp_configs'
    id = db.Column(db.Integer, primary_key=True)
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
            'password': '********',  # Hide password in responses
            'use_tls': self.use_tls,
            'created_at': to_egypt_dict_time(self.created_at)
        }

class EmailTracking(db.Model):
    __tablename__ = 'email_tracking'
    id = db.Column(db.Integer, primary_key=True)
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

# Utility Functions
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
    """Create email body with normal design (text + optional small image + tracking pixel)"""
    base_url = request.url_root.rstrip('/')

    # Ensure image URL is absolute
    if image_url and not image_url.startswith('http'):
        image_url = f"{base_url}/{image_url.lstrip('/')}"

    # Click tracking URL
    click_tracking_url = f"{base_url}/click/{tracking_id}?redirect={redirect_url}"

    # Tracking pixel URL
    pixel_url = f"{base_url}/track/{tracking_id}.gif"

    # Build email body
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Email</title>
    </head>
    <body style="margin:0; padding:20px; font-family: Arial, sans-serif; background-color:#f4f4f4;">
        <div style="max-width:600px; margin:0 auto; background-color:white; 
                    border-radius:8px; padding:20px; 
                    box-shadow:0 2px 10px rgba(0,0,0,0.1);">
            
            <!-- Email body text -->
            <div style="font-size:15px; color:#333; line-height:1.6;">
                {body_text}
            </div>
            
            <!-- Optional image -->
            {"<div style='margin-top:20px; text-align:center;'>"
             f"<a href='{click_tracking_url}' target='_blank'>"
             f"<img src='{image_url}' alt='Email Image' style='max-width:200px; height:auto; border-radius:6px;' onerror=\"this.style.display='none';\">"
             "</a></div>" if image_url else ""}
        </div>

        <!-- Tracking pixel -->
        <img src="{pixel_url}" width="1" height="1" style="display:none;" alt="">
    </body>
    </html>
    """

    return html_body, click_tracking_url


@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/admin')
def admin():
    return render_template('admin.html')

# API Routes
@app.route('/api/smtp/config', methods=['GET'])
def get_smtp_config():
    config = SMTPConfig.query.first()
    if config:
        return jsonify({'success': True, 'config': config.to_dict()})
    return jsonify({'success': False, 'message': 'No SMTP configuration found'})

@app.route('/api/smtp/config', methods=['POST'])
def save_smtp_config():
    data = request.get_json()

    # Validate required fields
    required_fields = ['host', 'port', 'username', 'password']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'success': False, 'message': f'{field} is required'}), 400

    # Delete existing config and create new one (simple approach)
    SMTPConfig.query.delete()

    config = SMTPConfig(
        host=data['host'],
        port=int(data['port']),
        username=data['username'],
        password=data['password'],
        use_tls=data.get('use_tls', True)
    )

    db.session.add(config)
    db.session.commit()

    return jsonify({'success': True, 'message': 'SMTP configuration saved successfully'})


@app.route('/click/<tracking_id>')
def track_click(tracking_id):
    try:
        # Find tracking record
        tracking = EmailTracking.query.filter_by(tracking_id=tracking_id).first()

        if tracking:
            client_ip = get_client_ip()
            client_port = get_client_port()

            # Create click event record
            click_event = ClickEvent(
                tracking_id=tracking_id,
                click_time=get_egypt_time().replace(tzinfo=None),
                ip_address=client_ip,
                port=client_port,
                user_agent=request.headers.get('User-Agent', '')[:500]
            )
            db.session.add(click_event)

            # Update tracking summary for clicks
            tracking.click_count = (tracking.click_count or 0) + 1
            tracking.last_click_time = get_egypt_time().replace(tzinfo=None)
            tracking.last_ip = client_ip
            tracking.last_port = client_port

            db.session.commit()

        # Get redirect URL from query params or use default
        redirect_url = request.args.get('redirect', 'https://www.google.com')

        # Redirect to the intended destination
        from flask import redirect
        return redirect(redirect_url)

    except Exception as e:
        print(f"Click tracking error: {e}")
        # Redirect to default URL even on error
        redirect_url = request.args.get('redirect', 'https://www.google.com')
        from flask import redirect
        return redirect(redirect_url)


@app.route('/api/smtp/test', methods=['POST'])
def test_smtp_config():
    data = request.get_json()
    test_email = data.get('test_email')

    if not test_email:
        return jsonify({'success': False, 'message': 'Test email is required'}), 400

    config = SMTPConfig.query.first()
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


@app.route('/api/send-email', methods=['POST'])
def send_email():
    data = request.get_json()

    subject = data.get('subject', '')
    body_text = data.get('body', '')
    image_url = data.get('image_url', '')  # Change from body to image_url
    redirect_url = data.get('redirect_url', 'https://www.google.com')  # Add redirect URL
    emails = data.get('emails', [])

    if not emails:
        return jsonify({'success': False, 'message': 'No recipient emails provided'}), 400

    if not image_url:
        return jsonify({'success': False, 'message': 'No image provided'}), 400

    config = SMTPConfig.query.first()
    if not config:
        return jsonify({'success': False, 'message': 'No SMTP configuration found'}), 400

    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        results = []

        for email in emails:
            try:
                # Generate unique tracking ID for each email
                tracking_id = generate_tracking_id()

                # Create tracking record
                tracking = EmailTracking(
                    tracking_id=tracking_id,
                    recipient_email=email,
                    subject=subject
                )
                db.session.add(tracking)

                # Create email body with clickable image
                email_body, click_url = create_email_body_with_image(image_url, tracking_id, redirect_url,body_text)

                # Send email
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


@app.route('/api/tracking', methods=['GET'])
def get_tracking_data():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    per_page = 50

    query = EmailTracking.query

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



@app.route('/track/<tracking_id>.gif')
def track_pixel(tracking_id):
    try:
        # Find tracking record
        tracking = EmailTracking.query.filter_by(tracking_id=tracking_id).first()

        if tracking:
            client_ip = get_client_ip()
            client_port = get_client_port()

            # Create open event record (keep existing OpenEvent for opens)
            open_event = OpenEvent(
                tracking_id=tracking_id,
                open_time=get_egypt_time().replace(tzinfo=None),
                ip_address=client_ip,
                port=client_port,
                user_agent=request.headers.get('User-Agent', '')[:500]
            )
            db.session.add(open_event)

            # Update tracking summary for opens only
            tracking.open_count = (tracking.open_count or 0) + 1
            tracking.last_open_time = get_egypt_time().replace(tzinfo=None)
            # Don't update last_ip and last_port here since this is just an open, not a click

            db.session.commit()

        # Return 1x1 transparent GIF
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
        # Still return GIF even on error
        gif_data = base64.b64decode('R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7')
        response = make_response(gif_data)
        response.headers['Content-Type'] = 'image/gif'
        return response



@app.route('/api/tracking/<tracking_id>/details', methods=['GET'])
def get_tracking_details(tracking_id):
    """Get detailed tracking information for a specific tracking ID"""
    try:
        # Get the main tracking record
        tracking = EmailTracking.query.filter_by(tracking_id=tracking_id).first()
        if not tracking:
            return jsonify({'success': False, 'message': 'Tracking record not found'}), 404

        # Get open events
        open_events = OpenEvent.query.filter_by(tracking_id=tracking_id)\
                                   .order_by(OpenEvent.open_time.desc())\
                                   .all()

        # Get click events
        click_events = ClickEvent.query.filter_by(tracking_id=tracking_id)\
                                     .order_by(ClickEvent.click_time.desc())\
                                     .all()

        opens = []
        for event in open_events:
            opens.append({
                'open_time': to_egypt_dict_time(event.open_time),
                'ip': event.ip_address or 'Unknown',
                'port': event.port or 'Unknown'
            })

        clicks = []
        for event in click_events:
            clicks.append({
                'click_time': to_egypt_dict_time(event.click_time),
                'ip': event.ip_address or 'Unknown',
                'port': event.port or 'Unknown'
            })

        return jsonify({
            'success': True,
            'tracking': tracking.to_dict(),
            'opens': opens,
            'clicks': clicks
        })

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500



@app.route('/api/admin/clear-database', methods=['POST'])
def clear_database():
    """Clear all tracking data from database"""
    try:
        # Verify admin access by requiring a confirmation
        data = request.get_json(silent=True) or {}
        confirmation = data.get('confirmation', '').strip()

        if confirmation != 'DELETE ALL':
            return jsonify({'success': False, 'message': 'Invalid confirmation'}), 400

        # Delete all data
        with db.engine.connect() as conn:
            # Delete in correct order to avoid foreign key constraints
            conn.execute(text("DELETE FROM click_events"))  # ADD this line
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

# Initialize database
def create_tables():
    with app.app_context():
        # db.drop_all()  # Uncomment if you want to recreate tables
        db.create_all()

        # Add new columns if they don't exist
        try:
            with db.engine.connect() as conn:  # Use proper connection context
                conn.execute(text('ALTER TABLE email_tracking ADD COLUMN click_count INTEGER DEFAULT 0'))
                conn.execute(text('ALTER TABLE email_tracking ADD COLUMN last_click_time DATETIME'))
                conn.commit()
        except Exception as e:
            print(f"Columns might already exist: {e}")
            pass  # Columns already exist

        print("Database tables created successfully!")

if __name__ == '__main__':
    create_tables()
    app.run(host='0.0.0.0', port=5000, debug=True)