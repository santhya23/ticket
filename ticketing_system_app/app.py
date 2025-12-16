from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_mail import Mail, Message
from tinydb import TinyDB, Query
import os


from werkzeug.utils import secure_filename

# Admin credentials and department list
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'ngmc@admin'  # Change this to your desired password

DEPARTMENTS = [
    "AI", "APD", "BCA", "BBA", "BPS", "BI", "BOTANY", "CA", "CHEMISTRY", "COMMERCE", "CT",
    "DA", "ECO", "EC", "ENGLISH", "FINANCE", "HINDI", "HISTORY", "IB", "IT",
    "MATHS", "PA", "PHYSICS", "TAMIL", "ZOOLOGY"
]

app = Flask(__name__)
app.secret_key = 'santhyakavi'  # Change this to a strong secret key

# Upload folder configuration
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Flask-Mail configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'       # or your SMTP server
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'santhyalogu2006@gmail.com'   # Admin email
app.config['MAIL_PASSWORD'] = 'kkczqddepgeuanjy'            # App password (use app-specific password)
app.config['MAIL_DEFAULT_SENDER'] = ('Ticket System', 'santhyalogu2006@gmail.com')

mail = Mail(app)

# Initialize TinyDB
db = TinyDB('db.json')
tickets_table = db.table('tickets')
feedback_table = db.table('feedback')

# Helper to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid username or password!')
    return render_template('admin_login.html')


@app.route('/')
def home():
    tickets = tickets_table.all()  # Fetch all tickets from TinyDB

    total = len(tickets)  # Total tickets
    in_process = len([t for t in tickets if t.get('status') == 'In Process'])  # Count 'In Process'
    solved = len([t for t in tickets if t.get('status') == 'Solved'])          # Count 'Solved'

    # Pass these counts along with departments to the template
    return render_template('create_ticket.html',
                           total=total,
                           in_process=in_process,
                           solved=solved,
                           departments=DEPARTMENTS)


@app.route('/create_ticket', methods=['POST'])
def create_ticket():
    department = request.form.get('department')
    system = request.form.get('system')
    problem = request.form.get('problem')
    email = request.form.get('email')
    severity = request.form.get('severity')

    # Handle image upload
    image_file = request.files.get('image')
    image_filename = None

    if image_file and allowed_file(image_file.filename):
        filename = secure_filename(image_file.filename)
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image_file.save(image_path)
        image_filename = filename

    if not all([department, system, problem, email, severity]):
        flash("Please fill all required fields!")
        return redirect(url_for('home'))

    tickets_table.insert({
        'department': department,
        'system': system,
        'problem': problem,
        'email': email,
        'severity': severity,
        'status': 'New',
        'image_filename': image_filename,
    })

    # Send notification email to admin
    msg = Message(
        subject="New Ticket Created",
        recipients=[app.config['MAIL_USERNAME']],
    )
    msg.body = f"""
A new ticket has been created.

Department: {department}
System/Projector: {system}
Problem: {problem}
Severity: {severity}
Contact Email: {email}

Please check the admin dashboard to manage this ticket.
"""
    mail.send(msg)

    flash("Ticket created successfully! Admin has been notified.")
    return redirect(url_for('home'))


@app.route('/test_email')
def test_email():
    msg = Message("Test email", recipients=[app.config['MAIL_USERNAME']])
    msg.body = "This is a test email sent from Flask app."
    mail.send(msg)
    return "Test email sent!"


@app.route('/admin')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    tickets = tickets_table.all()
    return render_template('admin_tickets.html', tickets=tickets)


@app.route('/admin_logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    flash('Logged out successfully!')
    return redirect(url_for('home'))



@app.route('/update_ticket/<int:ticket_id>', methods=['POST'])
def update_ticket(ticket_id):
    new_status = request.form.get('status')
    ticket = tickets_table.get(doc_id=ticket_id)
    if ticket:
        tickets_table.update({'status': new_status}, doc_ids=[ticket_id])
        flash('Ticket status updated!')

        if new_status == 'Solved':
            try:
                feedback_link = url_for('feedback', ticket_id=ticket_id, _external=True)  # Absolute URL

                msg = Message(
                    subject="Your Ticket Has Been Solved",
                    recipients=[ticket['email']],
                )
                msg.body = f"""
Hello,

Your ticket has been marked as SOLVED.

Ticket details:
Department: {ticket['department']}
System/Projector: {ticket['system']}
Problem: {ticket['problem']}
Severity: {ticket['severity']}

Please provide your feedback here:
{feedback_link}

Thank you!
"""
                mail.send(msg)
            except Exception as e:
                flash(f"Warning: Could not send solution email to user ({e})")

    else:
        flash('Ticket not found!')

    return redirect(url_for('admin_dashboard'))

@app.route('/feedback/<int:ticket_id>', methods=['GET', 'POST'])
def feedback(ticket_id):
    if request.method == 'POST':
        feedback_text = request.form.get('feedback', '').strip()
        if not feedback_text:
            flash('Please enter your feedback before submitting.')
            return redirect(url_for('feedback', ticket_id=ticket_id))

        feedback_table.insert({
            'ticket_id': ticket_id, 
            'feedback': feedback_text,
        })
        flash('Thank you for your feedback!')
        return redirect(url_for('home'))

    return render_template('feedback.html', ticket_id=ticket_id)

@app.route('/admin_feedback')
def admin_feedback():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    all_feedback = feedback_table.all()
    return render_template('admin_feedback.html', feedback_list=all_feedback)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)