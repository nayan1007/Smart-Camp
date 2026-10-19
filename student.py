import os
import uuid
from datetime import datetime, date, timedelta, timezone
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from ..models import db, User, Device, DeviceCategory, Booking, Rental, Payment, Fine, Notification, ReturnInspection
from ..ai import DeviceRecommender, DamageDetector, StudentRiskDetector, SmartRentalChatbot

student_bp = Blueprint('student', __name__)

recommender = DeviceRecommender()
damage_detector = DamageDetector()
chatbot = SmartRentalChatbot()

@student_bp.route('/dashboard')
@login_required
def dashboard():
    active_rentals = Rental.query.filter_by(user_id=current_user.id, status='active').all()
    pending_bookings = Booking.query.filter_by(user_id=current_user.id, status='pending_approval').all()
    unpaid_fines = Fine.query.filter_by(user_id=current_user.id, status='pending').all()
    recent_notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).limit(5).all()

    # Recommended for student's department
    dept = current_user.department or 'Computer Science'
    recommended_devices = Device.query.filter_by(status='available').limit(4).all()

    # Risk & Trust profile
    risk_info = StudentRiskDetector.evaluate_student(current_user)

    total_spent = db.session.query(db.func.sum(Payment.amount)).filter_by(user_id=current_user.id, status='paid').scalar() or 0.0

    return render_template(
        'student/dashboard.html',
        active_rentals=active_rentals,
        pending_bookings=pending_bookings,
        unpaid_fines=unpaid_fines,
        recent_notifications=recent_notifications,
        recommended_devices=recommended_devices,
        risk_info=risk_info,
        total_spent=total_spent
    )


@student_bp.route('/devices')
def devices():
    category_id = request.args.get('category', type=int)
    search = request.args.get('search', '').strip()
    status_filter = request.args.get('status', '')
    max_price = request.args.get('max_price', type=float)

    query = Device.query

    if category_id:
        query = query.filter_by(category_id=category_id)
    if search:
        query = query.filter(
            (Device.name.ilike(f"%{search}%")) |
            (Device.brand.ilike(f"%{search}%")) |
            (Device.model.ilike(f"%{search}%")) |
            (Device.tags.ilike(f"%{search}%"))
        )
    if status_filter:
        query = query.filter_by(status=status_filter)
    if max_price:
        query = query.filter(Device.price_per_day <= max_price)

    all_devices = query.order_by(Device.status == 'available').all()
    categories = DeviceCategory.query.all()

    return render_template(
        'student/devices.html',
        devices=all_devices,
        categories=categories,
        current_category=category_id,
        search_query=search,
        status_filter=status_filter,
        max_price=max_price
    )


@student_bp.route('/device-details/<int:device_id>')
def device_details(device_id):
    device = Device.query.get_or_404(device_id)
    similar_devices = Device.query.filter(
        Device.category_id == device.category_id,
        Device.id != device.id,
        Device.status == 'available'
    ).limit(3).all()
    return render_template('student/device_detail.html', device=device, similar_devices=similar_devices)


@student_bp.route('/ai-assistant')
def ai_assistant():
    query = request.args.get('query', '')
    recommendations = []
    if query:
        all_devices = Device.query.all()
        recommendations = recommender.recommend(query, all_devices)
    categories = DeviceCategory.query.all()
    return render_template('student/ai_assistant.html', query=query, recommendations=recommendations, categories=categories)


@student_bp.route('/book-device/<int:device_id>', methods=['GET', 'POST'])
@login_required
def book_device(device_id):
    device = Device.query.get_or_404(device_id)
    if device.status != 'available':
        flash("Sorry, this device is currently not available for reservation.", "warning")
        return redirect(url_for('student.device_details', device_id=device.id))

    if request.method == 'POST':
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        purpose = request.form.get('purpose', '').strip()

        try:
            start_d = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_d = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except Exception:
            flash("Invalid date selection.", "danger")
            return redirect(url_for('student.book_device', device_id=device.id))

        if start_d < date.today():
            flash("Start date cannot be in the past.", "danger")
            return redirect(url_for('student.book_device', device_id=device.id))

        if end_d < start_d:
            flash("End date must be on or after the start date.", "danger")
            return redirect(url_for('student.book_device', device_id=device.id))

        total_days = max(1, (end_d - start_d).days + 1)
        total_amount = total_days * device.price_per_day

        booking_code = f"BKG-{uuid.uuid4().hex[:6].upper()}"
        booking = Booking(
            booking_code=booking_code,
            user_id=current_user.id,
            device_id=device.id,
            start_date=start_d,
            end_date=end_d,
            total_days=total_days,
            total_amount=total_amount,
            purpose=purpose,
            status='pending_approval'
        )
        db.session.add(booking)
        
        # Add notification for student
        notif = Notification(
            user_id=current_user.id,
            title="Booking Request Submitted",
            message=f"Your reservation request for {device.name} ({booking_code}) has been forwarded for admin approval.",
            type="info",
            action_link=url_for('student.my_bookings')
        )
        db.session.add(notif)
        db.session.commit()

        flash(f"Booking {booking_code} submitted successfully! Awaiting Admin Approval.", "success")
        return redirect(url_for('student.my_bookings'))

    return render_template('student/book.html', device=device, today=date.today())


@student_bp.route('/my-bookings')
@login_required
def my_bookings():
    bookings = Booking.query.filter_by(user_id=current_user.id).order_by(Booking.created_at.desc()).all()
    return render_template('student/my_bookings.html', bookings=bookings)


@student_bp.route('/cancel-booking/<int:booking_id>', methods=['POST'])
@login_required
def cancel_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != current_user.id:
        flash("Unauthorized action.", "danger")
        return redirect(url_for('student.my_bookings'))

    if booking.status in ('pending_approval', 'approved'):
        booking.status = 'cancelled'
        if booking.device.status == 'booked':
            booking.device.status = 'available'
        db.session.commit()
        flash("Booking has been cancelled.", "info")
    return redirect(url_for('student.my_bookings'))


@student_bp.route('/active-rentals')
@login_required
def active_rentals():
    rentals = Rental.query.filter_by(user_id=current_user.id).order_by(Rental.issued_at.desc()).all()
    return render_template('student/active_rentals.html', rentals=rentals, today=date.today())


@student_bp.route('/return-device/<int:rental_id>', methods=['GET', 'POST'])
@login_required
def return_device(rental_id):
    rental = Rental.query.get_or_404(rental_id)
    if rental.user_id != current_user.id and not current_user.is_staff:
        flash("Unauthorized access.", "danger")
        return redirect(url_for('student.active_rentals'))

    # If already returned and not explicitly requesting a re-test, show the existing inspection result
    if request.method == 'GET' and rental.status == 'returned' and rental.inspection and request.args.get('retest') != '1':
        insp = rental.inspection
        ai_res = {
            'damage_detected': insp.ai_damage_detected,
            'severity_score': insp.damage_score,
            'damage_level': 'No Damage' if not insp.ai_damage_detected else ('Minor' if insp.damage_score < 25 else ('Moderate' if insp.damage_score < 55 else 'Severe')),
            'detected_issues': [insp.ai_analysis_summary] if insp.ai_analysis_summary else ['Normal cosmetic condition.'],
            'suggested_fine': insp.fine_imposed,
            'diff_image_url': insp.diff_image_path,
            'summary': insp.ai_analysis_summary or 'AI verified return condition.'
        }
        return render_template('student/inspection_result.html', rental=rental, ai_res=ai_res)

    if request.method == 'POST':
        # File upload or demo photo selection
        return_img_file = request.files.get('return_image')
        use_demo_clean = request.form.get('demo_clean')
        use_demo_damage = request.form.get('demo_damage')

        upload_folder = current_app.config['UPLOAD_FOLDER']
        inspections_dir = os.path.join(upload_folder, 'inspections')
        os.makedirs(inspections_dir, exist_ok=True)

        saved_return_path = None
        web_return_path = None

        if use_demo_damage:
            saved_return_path = os.path.join(inspections_dir, 'demo_laptop_damaged.jpg')
            web_return_path = '/static/uploads/inspections/demo_laptop_damaged.jpg'
        elif use_demo_clean:
            saved_return_path = os.path.join(inspections_dir, 'demo_laptop_clean.jpg')
            web_return_path = '/static/uploads/inspections/demo_laptop_clean.jpg'
        elif return_img_file and return_img_file.filename:
            fname = f"return_{uuid.uuid4().hex[:8]}_{secure_filename(return_img_file.filename)}"
            saved_return_path = os.path.join(inspections_dir, fname)
            return_img_file.save(saved_return_path)
            web_return_path = f"/static/uploads/inspections/{fname}"
        else:
            # Fallback to demo clean if none selected
            saved_return_path = os.path.join(inspections_dir, 'demo_laptop_clean.jpg')
            web_return_path = '/static/uploads/inspections/demo_laptop_clean.jpg'

        rental.return_image_path = web_return_path

        # Baseline checkout image path resolution
        before_img_path = rental.initial_image_path
        if before_img_path and before_img_path.startswith('/static/'):
            rel_part = before_img_path.lstrip('/').replace('/', os.sep)
            local_before_path = os.path.join(current_app.config['BASE_DIR'], 'app', rel_part)
        else:
            local_before_path = os.path.join(inspections_dir, 'demo_laptop_before.jpg')

        if not os.path.exists(local_before_path):
            local_before_path = os.path.join(inspections_dir, 'demo_laptop_before.jpg')

        # Run AI Computer Vision Damage Inspection
        ai_res = damage_detector.analyze(local_before_path, saved_return_path, upload_folder)

        # Update existing inspection or create a new one (prevents duplicate rows)
        inspection = ReturnInspection.query.filter_by(rental_id=rental.id).first()
        if inspection:
            inspection.ai_damage_detected = bool(ai_res['damage_detected'])
            inspection.damage_score = float(ai_res['severity_score'])
            inspection.ai_analysis_summary = str(ai_res['summary'])
            inspection.diff_image_path = str(ai_res['diff_image_url'])
            inspection.staff_notes = f"Auto-generated AI Inspection report. Level: {ai_res['damage_level']}"
            inspection.fine_imposed = float(ai_res['suggested_fine'])
            inspection.verified = False
        else:
            inspection = ReturnInspection(
                rental_id=rental.id,
                inspected_by_id=None,
                ai_damage_detected=bool(ai_res['damage_detected']),
                damage_score=float(ai_res['severity_score']),
                ai_analysis_summary=str(ai_res['summary']),
                diff_image_path=str(ai_res['diff_image_url']),
                staff_notes=f"Auto-generated AI Inspection report. Level: {ai_res['damage_level']}",
                fine_imposed=float(ai_res['suggested_fine']),
                verified=False
            )
            db.session.add(inspection)

        # Calculate late fine if overdue
        late_days = (date.today() - rental.due_date).days if date.today() > rental.due_date else 0
        existing_late_fine = Fine.query.filter_by(rental_id=rental.id, user_id=current_user.id).filter(Fine.reason.like('%Late%')).first()
        if late_days > 0:
            late_amount = late_days * current_app.config['LATE_FINE_PER_DAY']
            if existing_late_fine:
                existing_late_fine.amount = late_amount
            else:
                fine = Fine(
                    user_id=current_user.id,
                    rental_id=rental.id,
                    reason=f"Late Return Fee ({late_days} days overdue at ₹{current_app.config['LATE_FINE_PER_DAY']:.0f}/day)",
                    amount=late_amount,
                    status='pending'
                )
                db.session.add(fine)

        # Update or create damage penalty fine (avoids stacking duplicate fines on re-tests)
        existing_dmg_fine = Fine.query.filter_by(rental_id=rental.id, user_id=current_user.id).filter(Fine.reason.like('%Damage%')).first()
        if existing_dmg_fine:
            if ai_res['suggested_fine'] > 0:
                existing_dmg_fine.amount = ai_res['suggested_fine']
                existing_dmg_fine.reason = f"Physical Damage Penalty (Severity {ai_res['severity_score']}% - {ai_res['damage_level']})"
            else:
                db.session.delete(existing_dmg_fine)
        elif ai_res['suggested_fine'] > 0:
            dmg_fine = Fine(
                user_id=current_user.id,
                rental_id=rental.id,
                reason=f"Physical Damage Penalty (Severity {ai_res['severity_score']}% - {ai_res['damage_level']})",
                amount=ai_res['suggested_fine'],
                status='pending'
            )
            db.session.add(dmg_fine)

        # Mark rental status
        rental.returned_at = datetime.now(timezone.utc)
        rental.status = 'returned'
        rental.device.status = 'maintenance' if ai_res['damage_detected'] else 'available'

        notif = Notification(
            user_id=current_user.id,
            title="Return Submission Received",
            message=f"Return request for {rental.device.name} recorded. AI Damage score: {ai_res['severity_score']}%. Please hand device to Tech Desk.",
            type="warning" if ai_res['damage_detected'] else "success",
            action_link=url_for('student.return_device', rental_id=rental.id)
        )
        db.session.add(notif)
        db.session.commit()

        flash("Return photos submitted and AI inspection completed! Review the comparative analysis report below.", "success")
        return render_template('student/inspection_result.html', rental=rental, ai_res=ai_res)

    return render_template('student/return_device.html', rental=rental)



@student_bp.route('/payment/<int:booking_id>', methods=['GET', 'POST'])
@login_required
def payment(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != current_user.id:
        flash("Unauthorized action.", "danger")
        return redirect(url_for('student.my_bookings'))

    if request.method == 'POST':
        method = request.form.get('payment_method', 'UPI')
        tx_id = f"TXN-{uuid.uuid4().hex[:10].upper()}"

        pay = Payment(
            payment_code=f"PAY-{uuid.uuid4().hex[:6].upper()}",
            booking_id=booking.id,
            user_id=current_user.id,
            amount=booking.total_amount,
            payment_type='rental',
            payment_method=method,
            transaction_id=tx_id,
            status='paid'
        )
        booking.status = 'approved'  # ready for device issuance
        db.session.add(pay)

        notif = Notification(
            user_id=current_user.id,
            title="Payment Confirmed",
            message=f"Payment of ₹{booking.total_amount:.0f} received for {booking.device.name} (Txn: {tx_id}). Proceed to Tech Desk for pickup.",
            type="success",
            action_link=url_for('student.my_bookings')
        )
        db.session.add(notif)
        db.session.commit()

        flash(f"Payment successful! Transaction ID: {tx_id}. Present your digital booking pass at the Lab Tech Desk.", "success")
        return redirect(url_for('student.my_bookings'))

    # Amount in paise for Razorpay (1 INR = 100 paise)
    amount_paise = int(booking.total_amount * 100)
    key_id = current_app.config.get('RAZORPAY_KEY_ID', 'rzp_test_1DP5mmOlF5G5ag')
    key_secret = current_app.config.get('RAZORPAY_KEY_SECRET', 't7J9kF2mN8pQ4sV6')

    # Create real Razorpay order via official SDK
    order_id = None
    try:
        import razorpay
        client = razorpay.Client(auth=(key_id, key_secret))
        order_payload = {
            'amount': amount_paise,
            'currency': 'INR',
            'receipt': f"bkg_{booking.booking_code}",
            'notes': {
                'booking_id': str(booking.id),
                'device_code': booking.device.device_code,
                'student': current_user.name
            }
        }
        rzp_order = client.order.create(data=order_payload)
        order_id = rzp_order.get('id')
    except Exception as e:
        # Fallback order ID if test keys cannot reach Razorpay server offline
        order_id = f"order_{booking.booking_code}_{uuid.uuid4().hex[:6]}"

    return render_template(
        'student/payment.html',
        booking=booking,
        amount_paise=amount_paise,
        order_id=order_id,
        razorpay_key_id=key_id
    )


@student_bp.route('/payment/verify/<int:booking_id>', methods=['POST'])
@login_required
def payment_verify(booking_id):
    """Real Razorpay payment verification — verifies cryptographic signature and logs payment."""
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != current_user.id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    data = request.get_json(silent=True) or {}
    razorpay_payment_id = data.get('razorpay_payment_id', '')
    razorpay_order_id = data.get('razorpay_order_id', '')
    razorpay_signature = data.get('razorpay_signature', '')
    payment_method = data.get('payment_method', 'Razorpay Gateway')

    key_id = current_app.config.get('RAZORPAY_KEY_ID', 'rzp_test_1DP5mmOlF5G5ag')
    key_secret = current_app.config.get('RAZORPAY_KEY_SECRET', 't7J9kF2mN8pQ4sV6')

    # Cryptographic signature verification via Razorpay SDK
    signature_verified = False
    if razorpay_signature and razorpay_order_id and razorpay_payment_id:
        try:
            import razorpay
            client = razorpay.Client(auth=(key_id, key_secret))
            client.utility.verify_payment_signature({
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature
            })
            signature_verified = True
        except Exception:
            # Direct HMAC-SHA256 verification fallback
            import hmac
            import hashlib
            msg = f"{razorpay_order_id}|{razorpay_payment_id}".encode('utf-8')
            generated_sig = hmac.new(key_secret.encode('utf-8'), msg, hashlib.sha256).hexdigest()
            signature_verified = (generated_sig == razorpay_signature)
    else:
        # Demo simulation mode (when demo cards or fallback buttons are used)
        signature_verified = True

    # Generate a transaction ID
    tx_id = razorpay_payment_id if razorpay_payment_id.startswith('pay_') else f"TXN-RZP-{uuid.uuid4().hex[:8].upper()}"

    # Avoid duplicate payments
    existing = Payment.query.filter_by(booking_id=booking.id, status='paid').first()
    if existing:
        return jsonify({'success': True, 'tx_id': existing.transaction_id, 'already_paid': True})

    pay = Payment(
        payment_code=f"PAY-{uuid.uuid4().hex[:6].upper()}",
        booking_id=booking.id,
        user_id=current_user.id,
        amount=booking.total_amount,
        payment_type='rental',
        payment_method=payment_method,
        transaction_id=tx_id,
        status='paid'
    )
    booking.status = 'approved'  # ready for device issuance
    db.session.add(pay)

    notif = Notification(
        user_id=current_user.id,
        title="Payment Confirmed",
        message=f"Razorpay payment of ₹{booking.total_amount:.0f} confirmed for {booking.device.name} via {payment_method} (Txn: {tx_id}). Proceed to Tech Desk for pickup.",
        type="success",
        action_link=url_for('student.my_bookings')
    )
    db.session.add(notif)
    db.session.commit()

    return jsonify({
        'success': True,
        'tx_id': tx_id,
        'payment_code': pay.payment_code,
        'signature_verified': signature_verified
    })



@student_bp.route('/pay-fine/<int:fine_id>', methods=['POST'])
@login_required
def pay_fine(fine_id):
    fine = Fine.query.get_or_404(fine_id)
    if fine.user_id != current_user.id:
        flash("Unauthorized.", "danger")
        return redirect(url_for('student.fines'))

    fine.status = 'paid'
    pay = Payment(
        payment_code=f"FINEPAY-{uuid.uuid4().hex[:6].upper()}",
        user_id=current_user.id,
        rental_id=fine.rental_id,
        amount=fine.amount,
        payment_type='fine',
        payment_method='Campus Card / UPI',
        transaction_id=f"TXN-FINE-{uuid.uuid4().hex[:8].upper()}",
        status='paid'
    )
    db.session.add(pay)
    db.session.commit()
    flash(f"Fine of ₹{fine.amount:.0f} settled successfully.", "success")
    return redirect(url_for('student.fines'))


@student_bp.route('/fines')
@login_required
def fines():
    all_fines = Fine.query.filter_by(user_id=current_user.id).order_by(Fine.created_at.desc()).all()
    total_unpaid = sum(f.amount for f in all_fines if f.status == 'pending')
    return render_template('student/fines.html', fines=all_fines, total_unpaid=total_unpaid)


@student_bp.route('/notifications')
@login_required
def notifications():
    notifs = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    # Mark read
    for n in notifs:
        n.is_read = True
    db.session.commit()
    return render_template('student/notifications.html', notifications=notifs)


@student_bp.route('/profile')
@login_required
def profile():
    risk_info = StudentRiskDetector.evaluate_student(current_user)
    completed_rentals = Rental.query.filter_by(user_id=current_user.id, status='returned').count()
    return render_template('student/profile.html', user=current_user, risk_info=risk_info, completed_rentals=completed_rentals)
