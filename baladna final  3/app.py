import os
from calendar import monthrange
from datetime import datetime
import fitz  # PyMuPDF
import io
from PIL import Image
from flask import Flask, render_template, request, redirect, url_for, session, send_file, flash
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
import config

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Configuration for upload folder
UPLOAD_FOLDER = 'static/admin_pics'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}

# Configuration for SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///employees.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the database and migration objects
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Define the Employee model
class Employee(db.Model):
    __tablename__ = 'employees'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    monthly_salary = db.Column(db.Float, nullable=False)
    phone_number = db.Column(db.String(20), nullable=True)
    id_number = db.Column(db.String(50), unique=True, nullable=False)
    start_date = db.Column(db.String(10), nullable=False)
    address = db.Column(db.String(200), nullable=True)
    holidays_taken = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f'<Employee {self.name}>'

# Ensure the upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Custom number format filter for Jinja2
def number_format(value, decimal_places=2):
    return f"{float(value):,.{decimal_places}f}"

app.jinja_env.filters['number_format'] = number_format

# Function to check if a file is allowed
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Function to calculate the equivalent number based on employee's extra hours
def calculate_equivalent_number(employee, extra_hours):
    salary_before = float(employee['monthly_salary'])
    num_days = monthrange(datetime.now().year, datetime.now().month)[1]
    salary_per_day = salary_before / num_days
    salary_per_hour = salary_per_day / 9
    return extra_hours * salary_per_hour

# Function to calculate the equivalent value of absent hours
def calculate_equivalent_absent_hours(employee, hours_absent):
    salary_before = float(employee['monthly_salary'])
    num_days = monthrange(datetime.now().year, datetime.now().month)[1]
    salary_per_day = salary_before / num_days
    salary_per_hour = salary_per_day / 9  # Assuming 9 working hours per day
    return hours_absent * salary_per_hour

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/create_admin', methods=['GET', 'POST'])
def create_admin():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Save hashed password in the config or database as needed
        hashed_password = generate_password_hash(password)
        # Display success message or save these credentials in config or database
        print(f"Username: {username}, Password Hash: {hashed_password}")
        flash("Admin account created! Update config with the above details.", "success")
        return redirect(url_for('login'))
    
    return render_template('create_admin.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Check if the provided username matches and verify the hashed password
        if username == config.ADMIN_USERNAME and check_password_hash(
                config.ADMIN_PASSWORD, password):
            session['admin'] = {
                'username': username
            }  # Store the admin username in the session
            return redirect(url_for('admin_dashboard'))
        else:
            flash("Invalid credentials, please try again.", "error")
    return render_template('login.html')

@app.route('/admin_dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    if 'admin' not in session:
        return redirect(url_for('login'))

    admin = session['admin']  # Get the current admin from the session

    if request.method == 'POST':
        if 'add_employee' in request.form:
            name = request.form['name']
            monthly_salary = float(request.form['monthly_salary'])
            phone_number = request.form['phone_number']
            id_number = request.form['id_number']
            start_date = request.form['start_date']
            address = request.form['address']

            try:
                # Convert and format the start date
                parsed_start_date = datetime.strptime(start_date, '%d/%m/%Y')
                formatted_start_date = parsed_start_date.strftime('%d/%m/%Y')
            except ValueError:
                flash("Invalid start date format. Please use DD/MM/YYYY.", "danger")
                return redirect(url_for('admin_dashboard'))

            # Create a new employee record
            new_employee = Employee(
                name=name,
                monthly_salary=monthly_salary,
                phone_number=phone_number,
                id_number=id_number,
                start_date=formatted_start_date,
                address=address,
                holidays_taken=0  # Initialize holidays taken
            )

            # Add the new employee to the database
            db.session.add(new_employee)
            db.session.commit()

            # Create a directory for the new employee
            sanitized_name = name.replace(" ", "_")
            employee_directory = os.path.join('baladna final', 'static', 'info_database', 'employees', sanitized_name)
            if not os.path.exists(employee_directory):
                os.makedirs(employee_directory)

            flash(f"Employee {name} added successfully and directory created!", "success")

        elif 'update_employee' in request.form:
            employee_id = int(request.form['employee_id'])
            new_salary = float(request.form['new_salary'])
            new_phone_number = request.form.get('new_phone_number')
            new_address = request.form.get('new_address')

            # Fetch the employee record and update it
            employee = Employee.query.get(employee_id)
            if employee:
                employee.monthly_salary = new_salary
                if new_phone_number:
                    employee.phone_number = new_phone_number
                if new_address:
                    employee.address = new_address
                db.session.commit()
                flash(f"Employee {employee.name} updated successfully!", "success")
            else:
                flash("Employee not found.", "danger")

        elif 'delete_employee' in request.form:
            employee_id = int(request.form['employee_id'])
            # Delete the employee record from the database
            employee = Employee.query.get(employee_id)
            if employee:
                db.session.delete(employee)
                db.session.commit()
                flash(f"Employee {employee.name} deleted successfully!", "success")
            else:
                flash("Employee not found.", "danger")

        return redirect(url_for('admin_dashboard'))

    # Fetch all employees from the database to display on the dashboard
    employees = Employee.query.all()
    return render_template('admin_dashboard.html', admin=admin, employees=employees)

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'admin' not in session:
        return redirect(url_for('login'))

    admins = session.get(
        'admins', [{
            'username': config.ADMIN_USERNAME,
            'password': generate_password_hash(config.ADMIN_PASSWORD),
            'picture': None
        }])

    if request.method == 'POST':
        if 'add_admin' in request.form:
            new_admin_username = request.form['username']
            new_admin_password = request.form['password']
            admin_picture = request.files['picture']

            if new_admin_username and new_admin_password and allowed_file(
                    admin_picture.filename):
                # Create a folder for the new admin
                admin_folder = os.path.join(app.config['UPLOAD_FOLDER'],
                                            new_admin_username)
                if not os.path.exists(admin_folder):
                    os.makedirs(admin_folder)

                # Save the picture in the admin's folder
                filename = secure_filename(admin_picture.filename)
                picture_path = os.path.join(admin_folder, filename)
                admin_picture.save(picture_path)

                hashed_password = generate_password_hash(new_admin_password)

                new_admin = {
                    'username': new_admin_username,
                    'password': hashed_password,
                    'picture': picture_path
                }

                admins.append(new_admin)

                session['admins'] = admins
                print(f"New admin added: {new_admin}"
                      )  # Debug: Confirm new admin details
                flash("Admin added successfully!", "success")
            else:
                flash(
                    "Failed to add admin. Ensure all fields are filled and the picture is valid.",
                    "danger")

        elif 'delete_admin' in request.form:
            admin_username = request.form['username']

            admins = [
                admin for admin in admins
                if admin['username'] != admin_username
            ]

            session['admins'] = admins
            flash("Admin deleted successfully!", "success")

    return render_template('settings.html', admins=admins)

@app.route('/employee_list')
def employee_list():
    if 'admin' not in session:
        return redirect(url_for('login'))

    # Fetch all employees from the database
    employees = Employee.query.all()

    # Format the salary before passing it to the template
    for employee in employees:
        employee.formatted_salary = f"{float(employee.monthly_salary):,.2f}"

    return render_template('employee_list.html', employees=employees)

@app.route('/employee_history/<int:employee_id>', methods=['GET', 'POST'])
def employee_history(employee_id):
    if 'admin' not in session:
        return redirect(url_for('login'))

    employees = session.get('employees', [])
    employee = next((e for e in employees if e['id'] == employee_id), None)
    if not employee:
        return "Employee not found."

    # Format the monthly salary
    employee['formatted_salary'] = f"{float(employee['monthly_salary']):,.2f}"

    sanitized_name = employee['name'].replace(" ", "_")
    file_directory = os.path.join('baladna final', 'static', 'info_database',
                                  'employees', sanitized_name)

    # Initialize an empty list to store files, their URLs, and associated dates
    files = []

    # Check if the directory exists
    if os.path.exists(file_directory):
        # List all image and PDF files in the directory and generate their URLs
        for f in os.listdir(file_directory):
            if f.endswith(('.png', '.jpg', '.jpeg', '.gif', '.pdf')):
                # Generate URL correctly using forward slashes
                file_url = url_for(
                    'static',
                    filename=f'info_database/employees/{sanitized_name}/{f}')

                # Check if a corresponding date file exists
                date_file_path = os.path.join(file_directory, f"{f}_date.txt")
                if os.path.exists(date_file_path):
                    with open(date_file_path, 'r') as date_file:
                        file_date = date_file.read().strip()  # Read the date
                else:
                    file_date = "Date not available"  # Default message if date file is missing

                files.append((f, file_url, file_date))  # Include date in the list

    return render_template('employee_history.html',
                           employee=employee,
                           pdf_files=files)

@app.route('/employee_details/<int:employee_id>', methods=['GET', 'POST'])
def employee_details(employee_id):
    if 'admin' not in session:
        return redirect(url_for('login'))

    employees = session.get('employees', [])
    employee = next((e for e in employees if e['id'] == employee_id), None)

    if not employee:
        return "Employee not found."

    now = datetime.now()
    month = now.strftime('%B')
    number_of_days = monthrange(now.year, now.month)[1]

    salary_before = float(employee['monthly_salary'])
    salary_per_day = round(salary_before / number_of_days, 2)
    salary_per_hour = round(salary_per_day / 9, 2)

    days_absent = employee.get('days_absent', 0)
    hours_absent = employee.get('hours_absent', 0)
    extra_days = employee.get('extra_days', 0)
    extra_hours = employee.get('extra_hours', 0)
    extra_hours_1_5 = employee.get('extra_hours_1_5', 0)
    advanced_payment = employee.get('advanced_payment', 0.0)
    holidays_taken = employee.get('holidays_taken', 0)
    holidays_value = f"{holidays_taken}/14"
    extra_shifts_earnings = round(extra_hours_1_5 * salary_per_hour * 1.5, 2)
    salary_after = employee.get('salary_after', salary_before)

    if request.method == 'POST':
        days_absent = int(request.form['days_absent'])
        hours_absent = int(request.form['hours_absent'])
        extra_days = int(request.form['extra_days'])
        extra_hours = int(request.form['extra_hours'])
        extra_hours_1_5 = int(request.form['extra_hours_1_5'])
        advanced_payment = float(request.form['advanced_payment'])
        holidays_taken = int(request.form['holidays_taken'])

        extra_shifts_earnings = round(extra_hours_1_5 * salary_per_hour * 1.5, 2)

        salary_after = (
            salary_before - advanced_payment - days_absent * salary_per_day -
            hours_absent * salary_per_hour + extra_days * salary_per_day +
            extra_hours * salary_per_hour + extra_shifts_earnings
        )
        salary_after = round(salary_after, 2)

        employee.update({
            'days_absent': days_absent,
            'hours_absent': hours_absent,
            'extra_days': extra_days,
            'extra_hours': extra_hours,
            'extra_hours_1_5': extra_hours_1_5,
            'advanced_payment': advanced_payment,
            'holidays_taken': holidays_taken,
            'salary_after': salary_after,
        })

        session['employees'] = employees

        return redirect(url_for('employee_details', employee_id=employee_id))

    return render_template(
        'employee_details.html',
        employee=employee,
        month=month,
        number_of_days=number_of_days,
        salary_before=round(salary_before, 2),
        salary_per_day=salary_per_day,
        salary_per_hour=salary_per_hour,
        days_absent=days_absent,
        hours_absent=hours_absent,
        extra_days=extra_days,
        extra_hours=extra_hours,
        extra_hours_1_5=extra_hours_1_5,
        advanced_payment=round(advanced_payment, 2),
        holidays_value=holidays_value,
        extra_shifts_earnings=extra_shifts_earnings,
        salary_after=salary_after
    )

@app.route('/generate_pdf/<int:employee_id>', methods=['GET'])
def generate_pdf(employee_id):
    if 'admin' not in session:
        return redirect(url_for('login'))

    employees = session.get('employees', [])
    employee = next((e for e in employees if e['id'] == employee_id), None)

    if not employee:
        return "Employee not found."

    try:
        extra_hours = employee.get('extra_hours', 0)
        extra_hours_1_5 = employee.get('extra_hours_1_5', 0)
        extra_days = employee.get('extra_days', 0)
        days_absent = employee.get('days_absent', 0)
        hours_absent = employee.get('hours_absent', 0)

        total_extra_hours = extra_hours + extra_hours_1_5

        salary_before = float(employee['monthly_salary'])
        num_days = monthrange(datetime.now().year, datetime.now().month)[1]
        salary_per_day = salary_before / num_days
        salary_per_hour = salary_per_day / 9

        equivalent_normal_hours = round(extra_hours * salary_per_hour, 2)
        equivalent_hours_1_5 = round(extra_hours_1_5 * salary_per_hour * 1.5, 2)
        total_equivalent_hours = equivalent_normal_hours + equivalent_hours_1_5
        equivalent_days = round(extra_days * salary_per_day, 2)
        equivalent_days_absent = round(days_absent * salary_per_day, 2)
        equivalent_hours_absent = round(hours_absent * salary_per_hour, 2)

        template_path = os.path.join("static/baladna salaries.pdf")
        if not os.path.exists(template_path):
            return "Template file not found."

        doc = fitz.open(template_path)
        page = doc[0]

        def insert_text(position, text, font_size=12, font_color=(0, 0, 0)):
            page.insert_text(position, text, fontsize=font_size, color=font_color)

        font_size = 12
        font_color = (0, 0, 0)

        insert_text((90, 263), datetime.now().strftime('%d/%m/%Y'), font_size, font_color)
        insert_text((370, 280), employee['name'], font_size, font_color)
        insert_text((380, 302), employee['id_number'], font_size, font_color)
        insert_text((255, 431), str(employee['monthly_salary']), font_size, font_color)
        insert_text((265, 479), str(total_extra_hours), font_size, font_color)
        insert_text((153, 479), f"{total_equivalent_hours:.2f}", font_size, font_color)
        insert_text((280, 527), str(extra_days), font_size, font_color)
        insert_text((160, 527), f"{equivalent_days:.2f}", font_size, font_color)
        insert_text((300, 551), str(days_absent), font_size, font_color)
        insert_text((178, 551), f"{equivalent_days_absent:.2f}", font_size, font_color)
        insert_text((273, 575), str(hours_absent), font_size, font_color)
        insert_text((161, 575), f"{equivalent_hours_absent:.2f}", font_size, font_color)
        insert_text((338, 599), str(employee.get('advanced_payment', 0)), font_size, font_color)
        insert_text((254, 648), str(employee.get('salary_after', 0)), font_size, font_color)

        pdf_bytes = io.BytesIO()
        doc.save(pdf_bytes)
        pdf_bytes.seek(0)
        doc.close()

        return send_file(pdf_bytes, as_attachment=False, download_name=f"{employee['name']}_details.pdf", mimetype='application/pdf')

    except Exception as e:
        print(f"Error generating PDF: {e}")
        return "An error occurred while generating the PDF."

@app.route('/upload_file/<int:employee_id>', methods=['POST'])
def upload_file(employee_id):
    if 'admin' not in session:
        return redirect(url_for('login'))

    employees = session.get('employees', [])
    employee = next((e for e in employees if e['id'] == employee_id), None)

    if not employee:
        flash("Employee not found.", "danger")
        return redirect(url_for('employee_history', employee_id=employee_id))

    if 'file' not in request.files or 'file_date' not in request.form:
        flash("Please upload a file and enter the date.", "danger")
        return redirect(url_for('employee_history', employee_id=employee_id))

    file = request.files['file']
    file_date = request.form['file_date']

    if file.filename == '':
        flash("No selected file", "danger")
        return redirect(url_for('employee_history', employee_id=employee_id))

    if file and allowed_file(file.filename):
        sanitized_name = employee['name'].replace(" ", "_")
        file_directory = os.path.join('baladna final', 'static', 'info_database', 'employees', sanitized_name)

        if not os.path.exists(file_directory):
            os.makedirs(file_directory)

        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        filename = secure_filename(f"{timestamp}_{file.filename}")
        file_path = os.path.join(file_directory, filename)

        try:
            file.save(file_path)
            file_date_path = os.path.join(file_directory, f"{filename}_date.txt")
            with open(file_date_path, 'w') as date_file:
                date_file.write(file_date)

            flash(f"File uploaded successfully with date: {file_date}!", "success")
        except Exception as e:
            flash(f"An error occurred while processing the file: {e}", "danger")
            print(f"Error: {e}")

        return redirect(url_for('employee_history', employee_id=employee_id))
    else:
        flash("Invalid file type. Please upload a PDF or image file.", "danger")
        return redirect(url_for('employee_history', employee_id=employee_id))

@app.route('/delete_file/<int:employee_id>/<filename>', methods=['POST'])
def delete_file(employee_id, filename):
    if 'admin' not in session:
        return redirect(url_for('login'))

    employees = session.get('employees', [])
    employee = next((e for e in employees if e['id'] == employee_id), None)

    if not employee:
        return "Employee not found."

    sanitized_name = employee['name'].replace(" ", "_")
    file_directory = os.path.join('baladna final', 'static', 'info_database', 'employees', sanitized_name)
    file_path = os.path.join(file_directory, filename)

    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            flash(f"File '{filename}' deleted successfully!", "success")
        else:
            flash(f"File '{filename}' not found.", "danger")
    except Exception as e:
        flash(f"An error occurred while deleting the file: {e}", "danger")

    return redirect(url_for('employee_history', employee_id=employee_id))

if __name__ == '__main__':
    app.run(debug=True)
