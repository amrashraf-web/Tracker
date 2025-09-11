from flask import Flask, render_template, request, jsonify, make_response
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
load_dotenv()

app = Flask(__name__, template_folder='frontend/templates', static_folder='frontend/static')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
CORS(app)

EGYPT_TZ = pytz.timezone('Africa/Cairo')
UTC_TZ = pytz.UTC

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
    last_open_time = db.Column(db.DateTime, nullable=True)
    last_ip = db.Column(db.String(100), nullable=True)
    last_port = db.Column(db.String(10), nullable=True)
    last_latitude = db.Column(db.Float, nullable=True)  # Add this
    last_longitude = db.Column(db.Float, nullable=True)  # Add this
    last_location = db.Column(db.String(255), nullable=True)  # Add this
    created_at = db.Column(db.DateTime, default=lambda: get_egypt_time().replace(tzinfo=None))

    def to_dict(self):
        return {
            'id': self.id,
            'tracking_id': self.tracking_id,
            'recipient_email': self.recipient_email,
            'subject': self.subject,
            'open_count': self.open_count,
            'last_open_time': to_egypt_dict_time(self.last_open_time),
            'last_ip': self.last_ip,
            'last_port': self.last_port,
            'last_latitude': self.last_latitude,
            'last_longitude': self.last_longitude,
            'last_location': self.last_location,
            'created_at': to_egypt_dict_time(self.created_at)
        }

class OpenEvent(db.Model):
    __tablename__ = 'open_events'
    id = db.Column(db.Integer, primary_key=True)
    tracking_id = db.Column(db.String(64), db.ForeignKey('email_tracking.tracking_id'), nullable=False, index=True)
    open_time = db.Column(db.DateTime, default=lambda: get_egypt_time().replace(tzinfo=None), nullable=False)
    ip_address = db.Column(db.String(100), nullable=True)
    port = db.Column(db.String(10), nullable=True)
    latitude = db.Column(db.Float, nullable=True)  # Add this
    longitude = db.Column(db.Float, nullable=True)  # Add this
    location = db.Column(db.String(255), nullable=True)  # Add this
    user_agent = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'tracking_id': self.tracking_id,
            'open_time': to_egypt_dict_time(self.open_time),
            'ip_address': self.ip_address,
            'port': self.port,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'location': self.location,
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

def inject_tracking_pixel(html_body, tracking_id):
    """Inject tracking pixel into HTML email body"""
    base_url = request.url_root.rstrip('/')
    tracking_url = f"{base_url}/track/{tracking_id}.gif"
    tracking_pixel = f'<img src="{tracking_url}" width="1" height="1" style="display:none;" alt="">'

    # Try to inject before </body> tag, otherwise append
    if '</body>' in html_body.lower():
        html_body = re.sub(r'</body>', f'{tracking_pixel}</body>', html_body, flags=re.IGNORECASE)
    else:
        html_body += tracking_pixel

    return html_body

# Routes
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
    body = data.get('body', '')
    emails = data.get('emails', [])

    if not emails:
        return jsonify({'success': False, 'message': 'No recipient emails provided'}), 400

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

                # Inject tracking pixel into email body
                tracked_body = inject_tracking_pixel(body, tracking_id)

                # Send email
                msg = MIMEMultipart()
                msg['From'] = config.username
                msg['To'] = email
                msg['Subject'] = subject

                msg.attach(MIMEText(tracked_body, 'html'))

                server = smtplib.SMTP(config.host, config.port)
                if config.use_tls:
                    server.starttls()
                server.login(config.username, config.password)
                server.send_message(msg)
                server.quit()

                results.append({
                    'email': email,
                    'success': True,
                    'tracking_id': tracking_id
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

            # Get location from IP
            latitude, longitude, location = get_location_from_ip(client_ip)

            # Create actual open event record
            open_event = OpenEvent(
                tracking_id=tracking_id,
                open_time=get_egypt_time().replace(tzinfo=None),
                ip_address=client_ip,
                port=client_port,
                latitude=latitude,
                longitude=longitude,
                location=location,
                user_agent=request.headers.get('User-Agent', '')[:500]
            )
            db.session.add(open_event)

            # Update tracking summary
            tracking.open_count = (tracking.open_count or 0) + 1
            tracking.last_open_time = get_egypt_time().replace(tzinfo=None)
            tracking.last_ip = client_ip
            tracking.last_port = client_port
            tracking.last_latitude = latitude
            tracking.last_longitude = longitude
            tracking.last_location = location

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

        # Get real open events
        open_events = OpenEvent.query.filter_by(tracking_id=tracking_id)\
                                   .order_by(OpenEvent.open_time.desc())\
                                   .all()

        opens = []
        for event in open_events:
            opens.append({
                'open_time': to_egypt_dict_time(event.open_time),
                'ip': event.ip_address or 'Unknown',
                'port': event.port or 'Unknown'
            })

        return jsonify({
            'success': True,
            'tracking': tracking.to_dict(),
            'opens': opens
        })

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


def get_location_from_ip(ip_address):
    """Get location from IP address using a free API"""
    if not ip_address or ip_address in ['127.0.0.1', 'localhost']:
        return None, None, None

    # Skip internal/private IP addresses
    if (ip_address.startswith('192.168.') or
        ip_address.startswith('10.') or
        ip_address.startswith('172.16.') or
        ip_address.startswith('172.17.') or
        ip_address.startswith('172.18.') or
        ip_address.startswith('172.19.') or
        ip_address.startswith('172.2') or
        ip_address.startswith('172.3')):
        print(f"Skipping private IP: {ip_address}")
        return None, None, None

    try:
        import requests
        print(f"Getting location for IP: {ip_address}")

        # Try ipapi.co first
        response = requests.get(f'https://ipapi.co/{ip_address}/json/', timeout=10)

        if response.status_code == 200:
            data = response.json()
            print(f"API response: {data}")

            if 'latitude' in data and 'longitude' in data and data['latitude'] and data['longitude']:
                latitude = float(data['latitude'])
                longitude = float(data['longitude'])

                # Build location string
                location_parts = []
                if data.get('city'):
                    location_parts.append(data['city'])
                if data.get('region'):
                    location_parts.append(data['region'])
                if data.get('country_name'):
                    location_parts.append(data['country_name'])

                location = ', '.join(location_parts) if location_parts else 'Unknown'

                print(f"Location found: {latitude}, {longitude} - {location}")
                return latitude, longitude, location
        else:
            print(f"API request failed with status: {response.status_code}")

    except Exception as e:
        print(f"Geolocation error for IP {ip_address}: {e}")

    return None, None, None
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
        # db.drop_all()
        db.create_all()
        print("Database tables created successfully!")

if __name__ == '__main__':
    create_tables()
    app.run(host='0.0.0.0', port=5000, debug=True)