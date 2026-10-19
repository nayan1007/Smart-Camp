import os
import uuid
from datetime import datetime, date, timezone
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, jsonify
from flask_login import login_required, current_user
from ..models import db, User, Device, Booking, Rental, ReturnInspection, MaintenanceLog, Fine, Notification
from ..ai import DamageDetector

staff_bp = Blueprint('staff', __name__, url_prefix='/staff')

damage_detector = DamageDetector()

def staff_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_staff:
            flash("Staff or administrator access required.", "danger")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


@staff_bp.route('/dashboard')
@login_required
@staff_required
def dashboard():
    approved_bookings = Booking.query.filter_by(status='approved').all()
    active_rentals = Rental.query.filter_by(status='active').all()
    pending_inspections = ReturnInspection.query.filter_by(verified=False).all()
    in_maintenance = Device.query.filter_by(status='maintenance').all()
    overdue_rentals = [r for r in active_rentals if r.due_date < date.today()]

    return render_template(
        'staff/dashboard.html',
        approved_bookings=approved_bookings,
        active_rentals=active_rentals,
        pending_inspections=pending_inspections,
        in_maintenance=in_maintenance,
        overdue_rentals=overdue_rentals,
        today=date.today()
    )


@staff_bp.route('/scanner')
@login_required
@staff_required
def scanner():
    return render_template('staff/qr_scanner.html')


@staff_bp.route('/issue-device', methods=['GET', 'POST'])
@login_required
@staff_required
def issue_device():
    device_code = request.args.get('code', '')
    booking_id = request.args.get('booking_id', type=int)

    device = None
    target_booking = None

    if device_code:
        device = Device.query.filter_by(device_code=device_code.upper()).first()
        if device:
            # Find approved booking for this device
            target_booking = Booking.query.filter_by(device_id=device.id, status='approved').order_by(Booking.created_at.desc()).first()

    if booking_id:
        target_booking = Booking.query.get(booking_id)
        if target_booking:
            device = target_booking.device

    if request.method == 'POST':
        b_id = request.form.get('booking_id', type=int)
        condition_notes = request.form.get('condition_notes', 'Pristine condition verified at checkout')

        b = Booking.query.get_or_404(b_id)
        dev = b.device

        # Check if already rented
        existing_rental = Rental.query.filter_by(booking_id=b.id).first()
        if existing_rental:
            flash(f"Device already issued under Rental {existing_rental.rental_code}.", "warning")
            return redirect(url_for('staff.dashboard'))

        # Handle before-image upload
        before_image_path = '/static/uploads/inspections/demo_laptop_before.jpg'
        before_img = request.files.get('before_image')
        if before_img and before_img.filename:
            ext = before_img.filename.rsplit('.', 1)[-1].lower()
            if ext in {'jpg', 'jpeg', 'png', 'webp'}:
                fname = f"before_{uuid.uuid4().hex[:8]}.{ext}"
                save_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'inspections')
                os.makedirs(save_dir, exist_ok=True)
                before_img.save(os.path.join(save_dir, fname))
                before_image_path = f"/static/uploads/inspections/{fname}"

        rental_code = f"RNT-{uuid.uuid4().hex[:6].upper()}"
        rental = Rental(
            rental_code=rental_code,
            booking_id=b.id,
            user_id=b.user_id,
            device_id=dev.id,
            issued_by_id=current_user.id,
            issued_at=datetime.now(timezone.utc),
            due_date=b.end_date,
            initial_condition_notes=condition_notes,
            initial_image_path=before_image_path,
            status='active'
        )
        b.status = 'active'
        dev.status = 'rented'

        db.session.add(rental)

        # Notify student
        notif = Notification(
            user_id=b.user_id,
            title="Device Checked Out & Active",
            message=f"{dev.name} ({dev.device_code}) has been handed over to you. Due date: {b.end_date.strftime('%d %b %Y')}.",
            type="success",
            action_link=url_for('student.active_rentals')
        )
        db.session.add(notif)
        db.session.commit()

        flash(f"Device {dev.device_code} successfully issued to {b.user.name} under Rental {rental_code}!", "success")
        return redirect(url_for('staff.dashboard'))

    approved_list = Booking.query.filter_by(status='approved').all()
    return render_template('staff/issue_device.html', device=device, booking=target_booking, approved_list=approved_list, prefill_code=device_code)


@staff_bp.route('/receive-device', methods=['GET', 'POST'])
@login_required
@staff_required
def receive_device():
    device_code = request.args.get('code', '')
    active_rental = None
    device = None

    if device_code:
        device = Device.query.filter_by(device_code=device_code.upper()).first()
        if device:
            active_rental = Rental.query.filter_by(device_id=device.id, status='active').first()

    if request.method == 'POST':
        rental_id = request.form.get('rental_id', type=int)
        staff_condition = request.form.get('staff_condition', 'Good')
        staff_notes = request.form.get('staff_notes', 'Physical hardware verified by desk staff.')

        rental = Rental.query.get_or_404(rental_id)
        dev = rental.device

        rental.returned_at = datetime.now(timezone.utc)
        rental.received_by_id = current_user.id
        rental.status = 'returned'
        dev.status = 'available' if staff_condition in ('Excellent', 'Good') else 'maintenance'

        if rental.booking:
            rental.booking.status = 'completed'

        # Check for existing inspection or create one
        if not rental.inspection:
            insp = ReturnInspection(
                rental_id=rental.id,
                inspected_by_id=current_user.id,
                ai_damage_detected=False,
                damage_score=0.0,
                ai_analysis_summary="Manual desk intake verification completed.",
                staff_notes=staff_notes,
                fine_imposed=0.0,
                verified=True
            )
            db.session.add(insp)
        else:
            rental.inspection.inspected_by_id = current_user.id
            rental.inspection.verified = True
            rental.inspection.staff_notes = staff_notes

        notif = Notification(
            user_id=rental.user_id,
            title="Rental Returned & Closed",
            message=f"{dev.name} successfully checked back into Tech Desk inventory. Thank you for using Campus Electronics Rental!",
            type="success",
            action_link=url_for('student.dashboard')
        )
        db.session.add(notif)
        db.session.commit()

        flash(f"Device {dev.device_code} returned and closed successfully!", "success")
        return redirect(url_for('staff.dashboard'))

    active_rentals = Rental.query.filter_by(status='active').all()
    return render_template('staff/receive_device.html', device=device, rental=active_rental, active_rentals=active_rentals, prefill_code=device_code)


@staff_bp.route('/inspection')
@login_required
@staff_required
def inspection():
    inspections = ReturnInspection.query.order_by(ReturnInspection.created_at.desc()).all()
    return render_template('staff/inspection.html', inspections=inspections)


@staff_bp.route('/inspection/<int:inspection_id>', methods=['GET', 'POST'])
@login_required
@staff_required
def inspection_detail(inspection_id):
    insp = ReturnInspection.query.get_or_404(inspection_id)

    if request.method == 'POST':
        action = request.form.get('action')  # 'approve_fine', 'waive_fine', 'pass_clean'
        notes = request.form.get('staff_notes', '')
        damage_desc = request.form.get('damage_description', '').strip()

        insp.staff_notes = notes
        insp.damage_description = damage_desc or insp.damage_description
        insp.inspected_by_id = current_user.id
        insp.verified = True

        if action == 'approve_fine':
            custom_fine = request.form.get('custom_fine', type=float) or insp.fine_imposed
            insp.fine_imposed = custom_fine
            insp.rental.device.status = 'maintenance'
            # Check or create fine record
            fine = Fine.query.filter_by(rental_id=insp.rental_id, reason=f"Physical Damage Penalty (Severity {insp.damage_score:.1f}%)").first()
            if not fine and custom_fine > 0:
                fine = Fine(
                    user_id=insp.rental.user_id,
                    rental_id=insp.rental.id,
                    reason=f"Physical Damage Penalty (Severity {insp.damage_score:.1f}%)",
                    amount=custom_fine,
                    status='pending'
                )
                db.session.add(fine)

            # Log maintenance
            m = MaintenanceLog(
                device_id=insp.rental.device_id,
                issue_description=f"AI Defect verification: {notes or insp.ai_analysis_summary}",
                cost=custom_fine,
                status='reported'
            )
            db.session.add(m)

        elif action == 'waive_fine':
            insp.fine_imposed = 0.0
            insp.rental.device.status = 'available'
            # Mark existing pending fines waived
            for f in insp.rental.fines:
                if 'Damage' in f.reason:
                    f.status = 'waived'

        elif action == 'pass_clean':
            insp.fine_imposed = 0.0
            insp.rental.device.status = 'available'

        db.session.commit()
        flash("Return inspection decision saved successfully.", "success")
        return redirect(url_for('staff.inspection'))

    return render_template('staff/inspection_detail.html', inspection=insp)


@staff_bp.route('/maintenance', methods=['GET', 'POST'])
@login_required
@staff_required
def maintenance():
    if request.method == 'POST':
        device_id = request.form.get('device_id', type=int)
        desc = request.form.get('description', '').strip()
        cost = request.form.get('cost', type=float) or 0.0

        dev = Device.query.get_or_404(device_id)
        dev.status = 'maintenance'

        log = MaintenanceLog(
            device_id=dev.id,
            issue_description=desc,
            cost=cost,
            status='reported'
        )
        db.session.add(log)
        db.session.commit()
        flash(f"Maintenance reported for {dev.device_code}.", "warning")
        return redirect(url_for('staff.maintenance'))

    logs = MaintenanceLog.query.order_by(MaintenanceLog.reported_at.desc()).all()
    devices = Device.query.all()
    return render_template('staff/maintenance.html', logs=logs, devices=devices)


@staff_bp.route('/maintenance/resolve/<int:log_id>', methods=['POST'])
@login_required
@staff_required
def resolve_maintenance(log_id):
    log = MaintenanceLog.query.get_or_404(log_id)
    log.status = 'repaired'
    log.completed_at = datetime.now(timezone.utc)
    log.device.status = 'available'
    log.device.condition = 'Good'
    db.session.commit()
    flash(f"Device {log.device.device_code} marked as repaired and returned to active inventory!", "success")
    return redirect(url_for('staff.maintenance'))
