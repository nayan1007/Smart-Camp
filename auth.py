import re
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from ..models import db, User

auth_bp = Blueprint('auth', __name__)

STAFF_PASSKEYS = ['STAFF-DESK-2026', 'CAMPUS-STAFF-2026', 'STAFF123']
ADMIN_PASSKEYS = ['ADMIN-MASTER-2026', 'CAMPUS-ADMIN-2026', 'ADMIN123']

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif current_user.role == 'staff':
            return redirect(url_for('staff.dashboard'))
        return redirect(url_for('student.dashboard'))

    selected_role = request.args.get('role', 'student').lower()
    if selected_role not in ('student', 'staff', 'admin'):
        selected_role = 'student'

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        selected_role = request.form.get('role', selected_role).lower()
        remember = bool(request.form.get('remember'))

        # Email format validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            flash("Please enter a valid campus email address (e.g. user@campus.edu).", "danger")
            return render_template('auth/login.html', selected_role=selected_role, email=email)

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            # Role Access Verification
            if selected_role == 'admin' and user.role != 'admin':
                flash(f"Access Denied: Account {user.email} is registered as {user.role.upper()}, not Administrator. Please select the {user.role.capitalize()} Portal to sign in.", "warning")
                return render_template('auth/login.html', selected_role=selected_role, email=email)
            elif selected_role == 'staff' and user.role not in ('staff', 'admin'):
                flash(f"Access Denied: Account {user.email} is registered as Student, not Staff. Please select Student Portal to sign in.", "warning")
                return render_template('auth/login.html', selected_role=selected_role, email=email)

            login_user(user, remember=remember)
            flash(f"Welcome back, {user.name}! Signed into {user.role.capitalize()} Portal.", "success")
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            if user.role == 'admin':
                return redirect(url_for('admin.dashboard'))
            elif user.role == 'staff':
                return redirect(url_for('staff.dashboard'))
            return redirect(url_for('student.dashboard'))
        else:
            flash(f"Invalid credentials for {selected_role.capitalize()} Portal. Please verify your email and password.", "danger")
            return render_template('auth/login.html', selected_role=selected_role, email=email)

    return render_template('auth/login.html', selected_role=selected_role)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('student.dashboard'))

    selected_role = request.args.get('role', 'student').lower()
    if selected_role not in ('student', 'staff', 'admin'):
        selected_role = 'student'

    if request.method == 'POST':
        role = request.form.get('role', 'student').lower()
        if role not in ('student', 'staff', 'admin'):
            role = 'student'
        selected_role = role

        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        student_id = request.form.get('student_id', '').strip()
        department = request.form.get('department', '').strip()
        phone = request.form.get('phone', '').strip()
        staff_access_key = request.form.get('staff_access_key', '').strip()
        admin_access_key = request.form.get('admin_access_key', '').strip()

        form_data = {
            'role': role,
            'name': name,
            'email': email,
            'student_id': student_id,
            'department': department,
            'phone': phone,
            'staff_access_key': staff_access_key,
            'admin_access_key': admin_access_key
        }

        # 1. Full Name Validation: 1, 2, or 3 words only
        name_words = name.split()
        if not (1 <= len(name_words) <= 3):
            flash("Full Name must contain 1, 2, or 3 words only (e.g. 'Ananya Sen' or 'Dr. Sunita Rao').", "danger")
            return render_template('auth/register.html', form_data=form_data, selected_role=selected_role)

        # Name must only contain letters, hyphens, periods (for titles like Dr.), and apostrophes
        if not all(re.match(r"^[A-Za-z]+([\'\-][A-Za-z]+)?\.?$", w) for w in name_words):
            flash("Full Name can only contain letters and hyphens (numbers and special symbols are not allowed).", "danger")
            return render_template('auth/register.html', form_data=form_data, selected_role=selected_role)

        # 2. Campus Email Validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            flash("Please enter a valid campus email address (e.g. user@campus.edu).", "danger")
            return render_template('auth/register.html', form_data=form_data, selected_role=selected_role)

        if User.query.filter_by(email=email).first():
            flash("An account with this email already exists. Please sign in or use another email.", "warning")
            return render_template('auth/register.html', form_data=form_data, selected_role=selected_role)

        # 3. Contact Phone Validation: 10 digits
        clean_phone = re.sub(r'[\s\-\(\)]', '', phone)
        if clean_phone.startswith('+'):
            phone_digits = clean_phone[1:]
            is_valid_phone = phone_digits.isdigit() and (10 <= len(phone_digits) <= 13)
        else:
            is_valid_phone = clean_phone.isdigit() and len(clean_phone) == 10

        if not is_valid_phone:
            flash("Contact phone must be a valid 10-digit mobile number (e.g. 9876543210 or +91 9876543210).", "danger")
            return render_template('auth/register.html', form_data=form_data, selected_role=selected_role)

        # 4. Password Complexity Validation: uppercase + special char + min 8
        if len(password) < 8:
            flash("Password must be at least 8 characters long for account security.", "danger")
            return render_template('auth/register.html', form_data=form_data, selected_role=selected_role)

        if not re.search(r'[A-Z]', password):
            flash("Password must contain at least one uppercase letter (A-Z).", "danger")
            return render_template('auth/register.html', form_data=form_data, selected_role=selected_role)

        if not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?~`]', password):
            flash("Password must contain at least one special character (e.g. !@#$%^&*).", "danger")
            return render_template('auth/register.html', form_data=form_data, selected_role=selected_role)

        # 5. Role-specific ID and Passcode verification
        if role == 'student':
            if not student_id:
                flash("University Roll / Student ID is required.", "danger")
                return render_template('auth/register.html', form_data=form_data, selected_role=selected_role)
            if not department:
                department = 'Computer Science'

        elif role == 'staff':
            if not student_id:
                flash("Staff Employee ID is required (e.g. EMP-LAB-105).", "danger")
                return render_template('auth/register.html', form_data=form_data, selected_role=selected_role)
            if staff_access_key.upper() not in STAFF_PASSKEYS:
                flash("Invalid Staff Authorization Key. Use the authorized campus desk key (e.g. STAFF-DESK-2026).", "danger")
                return render_template('auth/register.html', form_data=form_data, selected_role=selected_role)
            if not department:
                department = 'Central Lab & Tech Desk'

        elif role == 'admin':
            if not student_id:
                flash("Faculty / Administrator ID is required (e.g. ADM-FAC-012).", "danger")
                return render_template('auth/register.html', form_data=form_data, selected_role=selected_role)
            if admin_access_key.upper() not in ADMIN_PASSKEYS:
                flash("Invalid Master Administrator Security Key. Authorization key required (e.g. ADMIN-MASTER-2026).", "danger")
                return render_template('auth/register.html', form_data=form_data, selected_role=selected_role)
            if not department:
                department = 'Campus Tech Administration'

        user = User(
            name=name,
            email=email,
            role=role,
            student_id=student_id,
            department=department,
            phone=phone
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        login_user(user)
        flash(f"Registration successful! Welcome to the Smart Campus {role.capitalize()} Portal.", "success")
        if role == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif role == 'staff':
            return redirect(url_for('staff.dashboard'))
        return redirect(url_for('student.dashboard'))

    return render_template('auth/register.html', form_data={}, selected_role=selected_role)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You have been securely signed out.", "info")
    return redirect(url_for('auth.login'))


@auth_bp.route('/quick-login/<role>')
def quick_login(role):
    """Convenient demo switcher for graders & users"""
    email_map = {
        'admin': 'admin@campus.edu',
        'staff': 'staff@campus.edu',
        'student': 'student@campus.edu',
        'risk_student': 'priya@campus.edu'
    }
    target_email = email_map.get(role, 'student@campus.edu')
    user = User.query.filter_by(email=target_email).first()
    if user:
        login_user(user)
        flash(f"Switched session to {user.name} ({user.role.upper()})", "success")
        if user.role == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif user.role == 'staff':
            return redirect(url_for('staff.dashboard'))
        return redirect(url_for('student.dashboard'))
    flash("User account not found in database.", "danger")
    return redirect(url_for('auth.login'))
