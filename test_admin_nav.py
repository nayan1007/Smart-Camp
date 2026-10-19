from app import create_app
from app.models import db, Booking, User, Device

app = create_app()
with app.app_context():
    client = app.test_client()
    # Login as admin
    res_login = client.post('/login', data={'email': 'admin@campus.edu', 'password': 'admin123', 'role': 'admin'}, follow_redirects=True)
    assert res_login.status_code == 200

    resp = client.get('/admin/dashboard')
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')
    assert '/admin/approvals#booking-' in html or '/admin/bookings#booking-' in html, "Laptop name link missing in recent bookings"
    print("[PASS] Laptop name link verified in Admin Recent Bookings!")

    resp_appr = client.get('/admin/approvals')
    assert resp_appr.status_code == 200
    html_appr = resp_appr.data.decode('utf-8')
    assert 'id="booking-' in html_appr, "Booking anchor id missing in approvals queue"
    print("[PASS] Booking anchor id verified in Approvals Queue cards!")

    print("\nALL ADMIN BOOKING NAVIGATION TESTS PASSED SUCCESSFULLY!")
