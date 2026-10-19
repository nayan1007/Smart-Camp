import os
import json
import uuid
from datetime import datetime, date, timezone
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, jsonify
from flask_login import login_required, current_user
from ..models import db, User, Device, DeviceCategory, Booking, Rental, Payment, Fine, Notification, ReturnInspection, MaintenanceLog, AIDemandPrediction
from ..ai import DemandPredictor, StudentRiskDetector
from ..utils.qr_generator import generate_device_qr
from ..services.notification_service import send_multi_channel_notification

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

demand_predictor = DemandPredictor()

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash("Administrator privileges required.", "danger")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    total_devices = Device.query.count()
    available_devices = Device.query.filter_by(status='available').count()
    active_rentals_count = Rental.query.filter_by(status='active').count()
    pending_approvals = Booking.query.filter_by(status='pending_approval').count()
    total_revenue = db.session.query(db.func.sum(Payment.amount)).filter_by(status='paid').scalar() or 0.0

    recent_bookings = Booking.query.order_by(Booking.created_at.desc()).limit(6).all()
    recent_damages = ReturnInspection.query.filter_by(ai_damage_detected=True).order_by(ReturnInspection.created_at.desc()).limit(4).all()

    # High risk student count
    students = User.query.filter_by(role='student').all()
    flagged_students = [s for s in students if StudentRiskDetector.evaluate_student(s)['flagged']]

    # AI Quick Demand prediction
    predictions = demand_predictor.predict_next_month()

    return render_template(
        'admin/dashboard.html',
        total_devices=total_devices,
        available_devices=available_devices,
        active_rentals_count=active_rentals_count,
        pending_approvals=pending_approvals,
        total_revenue=total_revenue,
        recent_bookings=recent_bookings,
        recent_damages=recent_damages,
        flagged_count=len(flagged_students),
        predictions=predictions[:3]
    )


@admin_bp.route('/devices')
@login_required
@admin_required
def devices():
    category_id = request.args.get('category', type=int)
    status_filter = request.args.get('status', '')
    query = Device.query

    if category_id:
        query = query.filter_by(category_id=category_id)
    if status_filter:
        query = query.filter_by(status=status_filter)

    all_devices = query.order_by(Device.id.desc()).all()
    categories = DeviceCategory.query.all()
    return render_template('admin/devices.html', devices=all_devices, categories=categories, current_cat=category_id, current_status=status_filter)


@admin_bp.route('/add-device', methods=['GET', 'POST'])
@login_required
@admin_required
def add_device():
    categories = DeviceCategory.query.all()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        category_id = request.form.get('category_id', type=int)
        brand = request.form.get('brand', '').strip()
        model = request.form.get('model', '').strip()
        serial = request.form.get('serial_number', '').strip()
        price = request.form.get('price_per_day', type=float) or 150.0
        deposit = request.form.get('deposit_amount', type=float)
        if deposit is None or deposit < 0:
            deposit = round(price * 3, 2)  # Default: 3x daily rent
        is_non_electronic = request.form.get('is_non_electronic') == '1'
        condition = request.form.get('condition', 'Excellent')
        location = request.form.get('location', 'Tech Desk Room 101')
        tags = request.form.get('tags', '').strip()

        # Spec inputs (only for electronic items)
        specs_dict = {}
        if not is_non_electronic:
            ram = request.form.get('ram', '')
            cpu = request.form.get('cpu', '')
            gpu = request.form.get('gpu', '')
            storage = request.form.get('storage', '')
            if ram: specs_dict['RAM'] = f"{ram} GB" if 'GB' not in ram.upper() else ram
            if cpu: specs_dict['CPU'] = cpu
            if gpu: specs_dict['GPU'] = gpu
            if storage: specs_dict['Storage'] = storage
        else:
            # Non-electronic extra fields
            unit = request.form.get('unit', '')
            size = request.form.get('size', '')
            material = request.form.get('material', '')
            if unit: specs_dict['Unit'] = unit
            if size: specs_dict['Size'] = size
            if material: specs_dict['Material'] = material

        # Auto-generate device code
        cat = DeviceCategory.query.get(category_id)
        cat_prefix = cat.name[:3].upper() if cat else 'DEV'
        code = f"{cat_prefix}-{uuid.uuid4().hex[:4].upper()}"

        # Handle product image upload
        image_url = '/static/uploads/devices/default.jpg'
        img_file = request.files.get('product_image')
        if img_file and img_file.filename:
            ext = img_file.filename.rsplit('.', 1)[-1].lower()
            if ext in {'jpg', 'jpeg', 'png', 'webp', 'gif'}:
                fname = f"{code.lower()}.{ext}"
                save_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'devices')
                os.makedirs(save_dir, exist_ok=True)
                img_file.save(os.path.join(save_dir, fname))
                image_url = f"/static/uploads/devices/{fname}"

        device = Device(
            device_code=code,
            name=name,
            category_id=category_id,
            brand=brand,
            model=model,
            serial_number=serial,
            price_per_day=price,
            deposit_amount=deposit,
            is_non_electronic=is_non_electronic,
            condition=condition,
            location=location,
            tags=tags,
            specs=specs_dict,
            status='available',
            image_url=image_url
        )
        db.session.add(device)
        db.session.flush()

        # Generate QR code
        upload_folder = current_app.config['UPLOAD_FOLDER']
        qr_web_path = generate_device_qr(device, upload_folder)
        device.qr_code_path = qr_web_path

        db.session.commit()
        flash(f"{'Item' if is_non_electronic else 'Device'} {device.name} ({device.device_code}) registered with QR code badge!", "success")
        return redirect(url_for('admin.devices'))

    return render_template('admin/add_device.html', categories=categories)


@admin_bp.route('/edit-device/<int:device_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_device(device_id):
    device = Device.query.get_or_404(device_id)
    categories = DeviceCategory.query.all()

    if request.method == 'POST':
        device.name = request.form.get('name', device.name).strip()
        device.brand = request.form.get('brand', device.brand).strip()
        device.model = request.form.get('model', device.model).strip()
        device.price_per_day = request.form.get('price_per_day', type=float) or device.price_per_day
        device.status = request.form.get('status', device.status)
        device.condition = request.form.get('condition', device.condition)
        device.location = request.form.get('location', device.location).strip()
        device.tags = request.form.get('tags', device.tags).strip()

        db.session.commit()
        flash(f"Device {device.device_code} details updated.", "success")
        return redirect(url_for('admin.devices'))

    return render_template('admin/edit_device.html', device=device, categories=categories)


@admin_bp.route('/delete-device/<int:device_id>', methods=['POST'])
@login_required
@admin_required
def delete_device(device_id):
    device = Device.query.get_or_404(device_id)
    # Check if active rentals exist
    if device.rentals.filter_by(status='active').first():
        flash("Cannot delete a device that is currently rented.", "danger")
        return redirect(url_for('admin.devices'))
    
    db.session.delete(device)
    db.session.commit()
    flash(f"Device {device.device_code} removed from inventory.", "info")
    return redirect(url_for('admin.devices'))


@admin_bp.route('/bookings')
@login_required
@admin_required
def bookings():
    status_filter = request.args.get('status', '')
    query = Booking.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    all_bookings = query.order_by(Booking.created_at.desc()).all()
    return render_template('admin/bookings.html', bookings=all_bookings, current_status=status_filter)


@admin_bp.route('/approvals')
@login_required
@admin_required
def approvals():
    pending_bookings = Booking.query.filter_by(status='pending_approval').order_by(Booking.created_at.desc()).all()
    
    # Attach AI risk evaluations
    booking_items = []
    for b in pending_bookings:
        risk_data = StudentRiskDetector.evaluate_student(b.user)
        booking_items.append({
            'booking': b,
            'risk': risk_data
        })

    return render_template('admin/approvals.html', booking_items=booking_items)


@admin_bp.route('/approve-booking/<int:booking_id>', methods=['POST'])
@login_required
@admin_required
def approve_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    notes = request.form.get('notes', 'Approved by administrator.')
    booking.status = 'approved'
    booking.admin_notes = notes

    db.session.commit()

    # Trigger Multi-Channel Notifications (In-App, Email, SMS, WhatsApp) to that particular student
    send_multi_channel_notification(
        user_id=booking.user_id,
        event='booking_approved',
        booking_code=booking.booking_code,
        device_name=booking.device.name,
        action_link=url_for('student.payment', booking_id=booking.id)
    )

    flash(f"Booking {booking.booking_code} approved.", "success")
    return redirect(url_for('admin.approvals'))


@admin_bp.route('/reject-booking/<int:booking_id>', methods=['POST'])
@login_required
@admin_required
def reject_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    reason = request.form.get('reason', 'Equipment reserved for departmental examination priority.')
    booking.status = 'rejected'
    booking.admin_notes = reason
    db.session.commit()

    # Trigger Multi-Channel Notifications (In-App, Email, SMS, WhatsApp)
    send_multi_channel_notification(
        user_id=booking.user_id,
        event='booking_rejected',
        booking_code=booking.booking_code,
        device_name=booking.device.name,
        reason=reason,
        action_link=url_for('student.my_bookings')
    )

    flash(f"Booking {booking.booking_code} rejected.", "info")
    return redirect(url_for('admin.approvals'))


@admin_bp.route('/returns')
@login_required
@admin_required
def returns():
    all_rentals = Rental.query.filter(Rental.status.in_(['returned', 'overdue'])).order_by(Rental.issued_at.desc()).all()
    return render_template('admin/returns.html', rentals=all_rentals)


@admin_bp.route('/damage-reports')
@login_required
@admin_required
def damage_reports():
    reports = ReturnInspection.query.filter_by(ai_damage_detected=True).order_by(ReturnInspection.created_at.desc()).all()
    return render_template('admin/damage_reports.html', reports=reports)


@admin_bp.route('/students')
@login_required
@admin_required
def students():
    student_users = User.query.filter_by(role='student').all()
    evaluations = []
    for s in student_users:
        evaluations.append(StudentRiskDetector.evaluate_student(s))

    # Sort high risk first
    evaluations.sort(key=lambda x: x['risk_score'], reverse=True)
    return render_template('admin/students.html', evaluations=evaluations)


@admin_bp.route('/payments')
@login_required
@admin_required
def payments():
    all_payments = Payment.query.order_by(Payment.created_at.desc()).all()
    total_rev = sum(p.amount for p in all_payments if p.status == 'paid')
    return render_template('admin/payments.html', payments=all_payments, total_rev=total_rev)


@admin_bp.route('/analytics')
@login_required
@admin_required
def analytics():
    # Category rental distributions
    categories = DeviceCategory.query.all()
    cat_labels = [c.name for c in categories]
    cat_counts = [db.session.query(Rental).join(Device).filter(Device.category_id == c.id).count() for c in categories]

    # Department breakdown
    depts = ['Computer Science', 'Mechanical Eng', 'Electrical & Electronics', 'Media & Design']
    dept_counts = [db.session.query(Rental).join(User, Rental.user_id == User.id).filter(User.department == d).count() for d in depts]

    chart_trends = demand_predictor.get_chart_data()

    return render_template(
        'admin/analytics.html',
        cat_labels=cat_labels,
        cat_counts=cat_counts,
        dept_labels=depts,
        dept_counts=dept_counts,
        chart_trends=chart_trends
    )


@admin_bp.route('/ai-predictions')
@login_required
@admin_required
def ai_predictions():
    # Fine tune with live DB records
    all_rentals = Rental.query.all()
    demand_predictor.train_with_db_data(all_rentals)

    predictions = demand_predictor.predict_next_month()
    chart_trends = demand_predictor.get_chart_data()

    return render_template(
        'admin/ai_predictions.html',
        predictions=predictions,
        chart_trends=chart_trends,
        next_month_name=predictions[0]['forecast_month'] if predictions else 'Next Month'
    )
