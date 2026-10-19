import os
from flask import Blueprint, request, jsonify, current_app
from flask_login import current_user
from ..models import db, Device, DeviceCategory, User, Rental, Booking
from ..ai import DeviceRecommender, SmartRentalChatbot, DamageDetector, DemandPredictor, StudentRiskDetector

api_bp = Blueprint('api', __name__, url_prefix='/api')

recommender = DeviceRecommender()
chatbot = SmartRentalChatbot()
damage_detector = DamageDetector()
demand_predictor = DemandPredictor()

@api_bp.route('/chat', methods=['POST'])
def chat():
    """
    Intelligent chatbot endpoint.
    Handles natural language queries about device availability, prices, campus policies,
    and returns conversational responses with interactive booking cards.
    """
    data = request.get_json() or {}
    message = data.get('message', '').strip()
    if not message:
        return jsonify({'error': 'Message cannot be empty'}), 400

    models_dict = {
        'Device': Device,
        'DeviceCategory': DeviceCategory,
        'User': User
    }
    result = chatbot.process_message(message, db.session, models_dict)
    return jsonify(result)


@api_bp.route('/recommend', methods=['POST'])
def recommend():
    """
    AI Device Recommendation endpoint.
    Evaluates student requirement text against hardware specs, pricing, and availability.
    """
    data = request.get_json() or {}
    query_text = data.get('query', '').strip()
    top_k = data.get('top_k', 4)

    if not query_text:
        return jsonify({'recommendations': []})

    all_devices = Device.query.all()
    results = recommender.recommend(query_text, all_devices, top_k=top_k)

    serialized = []
    for item in results:
        dev = item['device']
        serialized.append({
            'device_id': dev.id,
            'device_code': dev.device_code,
            'name': dev.name,
            'brand': dev.brand,
            'model': dev.model,
            'category': dev.category_rel.name if dev.category_rel else '',
            'price_per_day': dev.price_per_day,
            'status': dev.status,
            'specs': dev.specs,
            'match_score': item['match_score'],
            'reasons': item['reasons'],
            'rental_days': item['rental_days'],
            'estimated_total': item['estimated_total'],
            'image_url': dev.image_url or '/static/uploads/devices/default.jpg',
            'location': dev.location
        })

    return jsonify({'recommendations': serialized})


@api_bp.route('/scan-qr', methods=['POST'])
def scan_qr():
    """
    Decodes QR payload scanned via camera or typed into tech desk scanner.
    Example payload: 'CAMPUS_DEVICE:LAP-102:SN109283' or direct code 'LAP-102'
    """
    data = request.get_json() or {}
    qr_text = data.get('qr_code', '').strip()

    if not qr_text:
        return jsonify({'found': False, 'error': 'Empty QR text'}), 400

    # Parse payload
    device_code = qr_text
    if 'CAMPUS_DEVICE:' in qr_text:
        parts = qr_text.split(':')
        if len(parts) >= 2:
            device_code = parts[1]

    device = Device.query.filter_by(device_code=device_code.upper()).first()
    if not device:
        # Try finding by serial number
        device = Device.query.filter_by(serial_number=qr_text).first()

    if not device:
        return jsonify({'found': False, 'message': f"Device '{device_code}' not recognized in campus system."})

    # Check active rental
    active_rental = Rental.query.filter_by(device_id=device.id, status='active').first()
    pending_booking = Booking.query.filter_by(device_id=device.id, status='approved').first()

    rental_info = None
    if active_rental:
        rental_info = {
            'rental_id': active_rental.id,
            'rental_code': active_rental.rental_code,
            'student_name': active_rental.user.name,
            'student_id': active_rental.user.student_id or 'N/A',
            'department': active_rental.user.department or 'General',
            'due_date': active_rental.due_date.strftime('%Y-%m-%d'),
            'status': active_rental.status
        }

    booking_info = None
    if pending_booking:
        booking_info = {
            'booking_id': pending_booking.id,
            'booking_code': pending_booking.booking_code,
            'student_name': pending_booking.user.name,
            'start_date': pending_booking.start_date.strftime('%Y-%m-%d'),
            'end_date': pending_booking.end_date.strftime('%Y-%m-%d'),
            'purpose': pending_booking.purpose
        }

    return jsonify({
        'found': True,
        'device': {
            'id': device.id,
            'code': device.device_code,
            'name': device.name,
            'category': device.category_rel.name if device.category_rel else '',
            'brand': device.brand,
            'model': device.model,
            'serial_number': device.serial_number,
            'status': device.status,
            'condition': device.condition,
            'location': device.location,
            'price_per_day': device.price_per_day,
            'image_url': device.image_url,
            'qr_code_url': device.qr_code_path
        },
        'active_rental': rental_info,
        'pending_booking': booking_info
    })


@api_bp.route('/predict-demand', methods=['GET'])
def get_prediction():
    """
    Returns next month's predicted demand for all equipment categories.
    """
    all_rentals = Rental.query.all()
    demand_predictor.train_with_db_data(all_rentals)
    preds = demand_predictor.predict_next_month()
    return jsonify({'predictions': preds})
