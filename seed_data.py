import os
import random
from datetime import datetime, date, timedelta, timezone
from config import Config
from app import create_app
from app.models import (
    db, User, DeviceCategory, Device, Booking, Rental,
    Payment, Fine, Notification, ReturnInspection, MaintenanceLog
)
from app.utils.qr_generator import generate_device_qr

def seed_database():
    app = create_app()
    with app.app_context():
        # Re-create tables
        db.drop_all()
        db.create_all()
        print("[OK] Database tables initialized.")

        upload_folder = app.config['UPLOAD_FOLDER']

        # 1. Device Categories
        categories_data = [
            ('Laptops', 'laptop', 'High-performance laptops for AI, programming, design, and general study'),
            ('Tablets', 'tablet', 'iPads and Android tablets with stylus for digital notes and sketching'),
            ('Projectors', 'projector', 'HD & 4K laser projectors for seminar, thesis, and classroom presentations'),
            ('Cameras', 'camera', 'DSLR & Mirrorless 4K cameras for campus media, fests, and research documentation'),
            ('Lab Equipment', 'cpu', 'Oscilloscopes, IoT embedded kits, microcontrollers, and multimeters'),
            ('Accessories', 'headphones', 'Noise-canceling headphones, USB-C fast chargers, and display adapters')
        ]
        cat_objs = {}
        for name, icon, desc in categories_data:
            cat = DeviceCategory(name=name, icon=icon, description=desc)
            db.session.add(cat)
            cat_objs[name] = cat
        db.session.commit()
        print("[OK] Categories seeded.")

        # 2. Users
        users_data = [
            {
                'name': 'Dr. Sunita Rao',
                'email': 'admin@campus.edu',
                'password': 'admin123',
                'role': 'admin',
                'student_id': 'EMP-ADM-001',
                'department': 'Campus IT & Infrastructure',
                'phone': '+91 98765 43210'
            },
            {
                'name': 'Prof. Rajesh Kumar',
                'email': 'staff@campus.edu',
                'password': 'staff123',
                'role': 'staff',
                'student_id': 'EMP-LAB-104',
                'department': 'Central Lab & Tech Desk',
                'phone': '+91 98765 12345'
            },
            {
                'name': 'Aarav Sharma',
                'email': 'student@campus.edu',
                'password': 'student123',
                'role': 'student',
                'student_id': 'STU-2024-041',
                'department': 'Computer Science',
                'phone': '+91 98111 22233'
            },
            {
                'name': 'Priya Patel',
                'email': 'priya@campus.edu',
                'password': 'student123',
                'role': 'student',
                'student_id': 'STU-2023-119',
                'department': 'Mechanical Eng',
                'phone': '+91 98222 33344'
            },
            {
                'name': 'Rohit Verma',
                'email': 'rohit@campus.edu',
                'password': 'student123',
                'role': 'student',
                'student_id': 'STU-2024-098',
                'department': 'Electrical & Electronics',
                'phone': '+91 98333 44455'
            }
        ]
        user_objs = {}
        for u in users_data:
            user = User(
                name=u['name'],
                email=u['email'],
                role=u['role'],
                student_id=u['student_id'],
                department=u['department'],
                phone=u['phone']
            )
            user.set_password(u['password'])
            db.session.add(user)
            user_objs[u['email']] = user
        db.session.commit()
        print("[OK] Users seeded.")

        # 3. Devices
        devices_data = [
            # Laptops
            {
                'code': 'LAP-101',
                'name': 'Dell XPS 15 (RTX 3050)',
                'cat': 'Laptops',
                'brand': 'Dell',
                'model': 'XPS 15 9520',
                'serial': 'SN-DELL-95201',
                'price': 400.0,
                'status': 'available',
                'condition': 'Excellent',
                'location': 'Tech Desk Room 101',
                'tags': 'python, ml, machine-learning, deep-learning, cuda, nvidia, engineering',
                'specs': {'RAM': '16 GB DDR5', 'CPU': 'Intel Core i7-12700H (14-Core)', 'GPU': 'NVIDIA RTX 3050 4GB', 'Storage': '512 GB NVMe SSD', 'Display': '15.6" OLED 3.5K'},
                'image': '/static/uploads/devices/laptop_dell.jpg'
            },
            {
                'code': 'LAP-102',
                'name': 'Apple MacBook Pro 16" M2',
                'cat': 'Laptops',
                'brand': 'Apple',
                'model': 'MacBook Pro 16 M2',
                'serial': 'SN-APPL-M2P01',
                'price': 550.0,
                'status': 'available',
                'condition': 'Excellent',
                'location': 'Tech Desk Room 101',
                'tags': 'ios, macos, swift, python, video-editing, premiere, figma, design',
                'specs': {'RAM': '16 GB Unified Memory', 'CPU': 'Apple M2 Pro (12-Core)', 'GPU': '19-Core Neural GPU', 'Storage': '512 GB SSD', 'Display': '16.2" Liquid Retina XDR'},
                'image': '/static/uploads/devices/laptop_macbook.jpg'
            },
            {
                'code': 'LAP-103',
                'name': 'Lenovo ThinkPad P14s Workstation',
                'cat': 'Laptops',
                'brand': 'Lenovo',
                'model': 'ThinkPad P14s Gen 4',
                'serial': 'SN-THNK-P14S2',
                'price': 450.0,
                'status': 'available',
                'condition': 'Good',
                'location': 'Hardware Lab Room 204',
                'tags': 'cad, solidworks, engineering, matlab, python, data-science, durable',
                'specs': {'RAM': '32 GB LPDDR5', 'CPU': 'AMD Ryzen 7 PRO 7840U', 'GPU': 'Radeon 780M Graphics', 'Storage': '1 TB Gen4 SSD', 'Display': '14.0" WUXGA Low Power'},
                'image': '/static/uploads/devices/laptop_thinkpad.jpg'
            },
            {
                'code': 'LAP-104',
                'name': 'ASUS ROG Zephyrus G14 (RTX 4060)',
                'cat': 'Laptops',
                'brand': 'ASUS',
                'model': 'Zephyrus G14',
                'serial': 'SN-ASUS-G1493',
                'price': 600.0,
                'status': 'available',
                'condition': 'Excellent',
                'location': 'Tech Desk Room 101',
                'tags': 'gaming, ai, rendering, 3d, blender, unity, unreal, heavy-compute',
                'specs': {'RAM': '16 GB DDR5', 'CPU': 'AMD Ryzen 9 7940HS', 'GPU': 'NVIDIA RTX 4060 8GB', 'Storage': '1 TB NVMe SSD', 'Display': '14.0" ROG Nebula QHD+ 165Hz'},
                'image': '/static/uploads/devices/laptop_gaming.jpg'
            },
            {
                'code': 'LAP-105',
                'name': 'HP Pavilion 14 Lightweight Laptop',
                'cat': 'Laptops',
                'brand': 'HP',
                'model': 'Pavilion 14-dv',
                'serial': 'SN-HPPA-14008',
                'price': 250.0,
                'status': 'available',
                'condition': 'Good',
                'location': 'Central Library Tech Corner',
                'tags': 'study, coding, web-dev, java, c++, budget, office, assignment',
                'specs': {'RAM': '8 GB DDR4', 'CPU': 'Intel Core i5-1235U', 'GPU': 'Intel Iris Xe', 'Storage': '512 GB SSD', 'Display': '14.0" FHD IPS'},
                'image': '/static/uploads/devices/laptop_hp.jpg'
            },
            {
                'code': 'LAP-106',
                'name': 'Acer Aspire 5 Budget Student Laptop',
                'cat': 'Laptops',
                'brand': 'Acer',
                'model': 'Aspire 5 A515',
                'serial': 'SN-ACER-51544',
                'price': 200.0,
                'status': 'available',
                'condition': 'Good',
                'location': 'Central Library Tech Corner',
                'tags': 'budget, inexpensive, notes, assignment, basic-python, browse',
                'specs': {'RAM': '8 GB DDR4', 'CPU': 'Intel Core i3-1215U', 'GPU': 'Intel UHD', 'Storage': '256 GB SSD', 'Display': '15.6" Full HD'},
                'image': '/static/uploads/devices/laptop_acer.jpg'
            },

            # Tablets
            {
                'code': 'TAB-201',
                'name': 'Apple iPad Pro 12.9" + Apple Pencil 2',
                'cat': 'Tablets',
                'brand': 'Apple',
                'model': 'iPad Pro 12.9 6th Gen',
                'serial': 'SN-APPL-TAB90',
                'price': 350.0,
                'status': 'available',
                'condition': 'Excellent',
                'location': 'Media Studio Room 305',
                'tags': 'digital-art, notes, procreate, drawing, stylus, study, paperless',
                'specs': {'RAM': '8 GB Unified', 'Chip': 'Apple M2 Chip', 'Storage': '128 GB', 'Stylus': 'Apple Pencil 2 Included', 'Display': '12.9" Liquid Retina XDR 120Hz'},
                'image': '/static/uploads/devices/tablet_ipad.jpg'
            },
            {
                'code': 'TAB-202',
                'name': 'Samsung Galaxy Tab S9 Ultra + S-Pen',
                'cat': 'Tablets',
                'brand': 'Samsung',
                'model': 'Galaxy Tab S9 Ultra',
                'serial': 'SN-SAMS-TAB88',
                'price': 320.0,
                'status': 'available',
                'condition': 'Excellent',
                'location': 'Tech Desk Room 101',
                'tags': 'android, notes, multitasking, samsung-dex, s-pen, pdf, large-screen',
                'specs': {'RAM': '12 GB RAM', 'Chip': 'Snapdragon 8 Gen 2', 'Storage': '256 GB', 'Display': '14.6" Dynamic AMOLED 2X', 'Stylus': 'S-Pen Included'},
                'image': '/static/uploads/devices/tablet_galaxy.jpg'
            },

            # Projectors
            {
                'code': 'PRJ-301',
                'name': 'Epson 4K 4000-Lumen Laser Projector',
                'cat': 'Projectors',
                'brand': 'Epson',
                'model': 'EB-L210SW Laser',
                'serial': 'SN-EPSN-PRJ12',
                'price': 400.0,
                'status': 'available',
                'condition': 'Excellent',
                'location': 'Audio-Visual Center Room 104',
                'tags': 'presentation, seminar, thesis, 4k, high-lumen, classroom, auditorium',
                'specs': {'Resolution': '4K UHD Enhanced', 'Brightness': '4000 ANSI Lumens', 'Light Source': 'Laser Diode (20,000h)', 'Connectivity': 'HDMI, Miracast, Wi-Fi', 'Throw': 'Short Throw'},
                'image': '/static/uploads/devices/projector_epson.jpg'
            },
            {
                'code': 'PRJ-302',
                'name': 'BenQ Wireless Conference Projector',
                'cat': 'Projectors',
                'brand': 'BenQ',
                'model': 'EH600 Smart Projector',
                'serial': 'SN-BENQ-PRJ99',
                'price': 300.0,
                'status': 'available',
                'condition': 'Good',
                'location': 'Audio-Visual Center Room 104',
                'tags': 'presentation, slides, meeting, wireless, usb-direct, lightweight',
                'specs': {'Resolution': '1080p Full HD', 'Brightness': '3500 ANSI Lumens', 'Wireless': 'Direct AirPlay & Chromecast', 'Ports': 'Dual HDMI, USB'},
                'image': '/static/uploads/devices/projector_benq.jpg'
            },

            # Cameras
            {
                'code': 'CAM-401',
                'name': 'Sony Alpha A7 IV Mirrorless 4K Camera',
                'cat': 'Cameras',
                'brand': 'Sony',
                'model': 'ILCE-7M4',
                'serial': 'SN-SONY-CAM04',
                'price': 650.0,
                'status': 'available',
                'condition': 'Excellent',
                'location': 'Media Studio Room 305',
                'tags': 'photography, 4k-video, fest, event, cinematic, full-frame, dslr, documentary',
                'specs': {'Sensor': '33 MP Full-Frame Exmor R CMOS', 'Video': '4K 60p 10-bit 4:2:2', 'Autofocus': '759 Phase-Detect Points Real-Time Eye AF', 'Lens': 'FE 28-70mm f/3.5-5.6 OSS'},
                'image': '/static/uploads/devices/camera_sony.jpg'
            },
            {
                'code': 'CAM-402',
                'name': 'Canon EOS R6 Mark II Professional Body',
                'cat': 'Cameras',
                'brand': 'Canon',
                'model': 'EOS R6 Mark II',
                'serial': 'SN-CANN-CAM82',
                'price': 700.0,
                'status': 'available',
                'condition': 'Excellent',
                'location': 'Media Studio Room 305',
                'tags': 'photography, sports, fast-motion, campus-fest, 4k60, canon',
                'specs': {'Sensor': '24.2 MP Full-Frame CMOS', 'Burst': '40 fps Electronic Shutter', 'Video': '6K Oversampled 4K 60p', 'Lens': 'RF 24-105mm f/4L IS USM'},
                'image': '/static/uploads/devices/camera_canon.jpg'
            },

            # Lab Equipment
            {
                'code': 'LAB-501',
                'name': 'Rigol DS1054Z 100MHz 4-CH Digital Oscilloscope',
                'cat': 'Lab Equipment',
                'brand': 'Rigol',
                'model': 'DS1054Z',
                'serial': 'SN-RGOL-OSC11',
                'price': 250.0,
                'status': 'available',
                'condition': 'Excellent',
                'location': 'Hardware Lab Room 204',
                'tags': 'oscilloscope, signal, electronics, circuits, waveforms, hardware, capstone',
                'specs': {'Channels': '4 Analog Channels', 'Bandwidth': '100 MHz (Upgraded)', 'Sample Rate': '1 GSa/s', 'Memory Depth': '24 Mpts', 'Display': '7" WVGA Color'},
                'image': '/static/uploads/devices/lab_oscilloscope.jpg'
            },
            {
                'code': 'LAB-502',
                'name': 'Raspberry Pi 4 Model B (8GB) IoT Kit',
                'cat': 'Lab Equipment',
                'brand': 'Raspberry Pi',
                'model': 'Model B 8GB',
                'serial': 'SN-RPI4-LAB45',
                'price': 120.0,
                'status': 'available',
                'condition': 'Good',
                'location': 'Hardware Lab Room 204',
                'tags': 'iot, embedded, linux, python, gpio, robotics, automation, sensors',
                'specs': {'RAM': '8 GB LPDDR4', 'CPU': 'Quad-Core Cortex-A72 1.5GHz', 'Kit Includes': 'Breadboard, 30+ Sensors, Camera Module v2, 64GB MicroSD, Power Supply'},
                'image': '/static/uploads/devices/lab_raspberry.jpg'
            },
            {
                'code': 'LAB-503',
                'name': 'Arduino Ultimate Robotics Development Kit',
                'cat': 'Lab Equipment',
                'brand': 'Arduino',
                'model': 'Mega 2560 R3 + Shield',
                'serial': 'SN-ARDU-KIT77',
                'price': 100.0,
                'status': 'available',
                'condition': 'Good',
                'location': 'Hardware Lab Room 204',
                'tags': 'arduino, robotics, motors, servo, sensors, c++, hardware-prototyping',
                'specs': {'Microcontroller': 'ATmega2560', 'IO': '54 Digital Pins, 16 Analog Inputs', 'Kit Includes': 'L298N Motor Driver, Ultrasonic, Gyroscope, Chassis, Servos'},
                'image': '/static/uploads/devices/lab_arduino.jpg'
            },

            # Accessories
            {
                'code': 'ACC-601',
                'name': 'Bose QuietComfort 45 ANC Headphones',
                'cat': 'Accessories',
                'brand': 'Bose',
                'model': 'QC45 Noise Cancelling',
                'serial': 'SN-BOSE-QC451',
                'price': 150.0,
                'status': 'available',
                'condition': 'Excellent',
                'location': 'Tech Desk Room 101',
                'tags': 'headphones, noise-cancelling, study, library, audio, focus, anc',
                'specs': {'Noise Cancelling': 'Acoustic Noise Cancelling Technology', 'Battery': '24 Hours Playback', 'Charging': 'USB-C Quick Charge (15 min = 3 hrs)'},
                'image': '/static/uploads/devices/audio_bose.jpg'
            },
            {
                'code': 'ACC-602',
                'name': 'Anker 140W USB-C 4-Port GaN Charger Hub',
                'cat': 'Accessories',
                'brand': 'Anker',
                'model': '747 Charger (GaNPrime)',
                'serial': 'SN-ANKR-140W9',
                'price': 60.0,
                'status': 'available',
                'condition': 'Excellent',
                'location': 'Tech Desk Room 101',
                'tags': 'charger, usb-c, gan, fast-charging, power-delivery, macbook, laptop',
                'specs': {'Total Output': '140 Watts Max', 'Ports': '3x USB-C + 1x USB-A', 'Technology': 'GaNPrime & ActiveShield 2.0'},
                'image': '/static/uploads/devices/charger_usbc.jpg'
            }
        ]

        dev_objs = {}
        for d in devices_data:
            dev = Device(
                device_code=d['code'],
                name=d['name'],
                category_id=cat_objs[d['cat']].id,
                brand=d['brand'],
                model=d['model'],
                serial_number=d['serial'],
                price_per_day=d['price'],
                status=d['status'],
                condition=d['condition'],
                location=d['location'],
                tags=d['tags'],
                specs=d['specs'],
                image_url=d['image']
            )
            db.session.add(dev)
            dev_objs[d['code']] = dev
        db.session.commit()

        # Generate QR code badges for all devices
        for dev in dev_objs.values():
            qr_path = generate_device_qr(dev, upload_folder)
            dev.qr_code_path = qr_path
        db.session.commit()
        print("[OK] 17 Devices created with branded QR code badges.")

        # 4. Realistic Historical Rental Records (for Demand Prediction & Analytics)
        print("Generating historical campus rental logs for ML training...")
        random.seed(42)
        aarav = user_objs['student@campus.edu']
        priya = user_objs['priya@campus.edu']
        rohit = user_objs['rohit@campus.edu']
        admin_user = user_objs['admin@campus.edu']
        staff_user = user_objs['staff@campus.edu']

        # Historical monthly distribution (past 8 months)
        today = date.today()
        all_dev_list = list(dev_objs.values())

        for i in range(1, 42):
            dev = random.choice(all_dev_list)
            # Pick a month in the past (1 to 8 months ago)
            days_ago = random.randint(15, 240)
            issued_dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
            dur = random.randint(2, 10)
            due_dt = issued_dt.date() + timedelta(days=dur)
            returned_dt = issued_dt + timedelta(days=dur + random.choice([0, 0, 0, 1, 2]))

            student = random.choice([aarav, rohit, priya])
            bkg_code = f"BKG-HIST-{1000 + i}"
            b = Booking(
                booking_code=bkg_code,
                user_id=student.id,
                device_id=dev.id,
                start_date=issued_dt.date(),
                end_date=due_dt,
                total_days=dur,
                total_amount=dev.price_per_day * dur,
                purpose="Academic Term Project & Lab Work",
                status='completed',
                created_at=issued_dt - timedelta(days=1)
            )
            db.session.add(b)
            db.session.flush()

            r = Rental(
                rental_code=f"RNT-HIST-{1000 + i}",
                booking_id=b.id,
                user_id=student.id,
                device_id=dev.id,
                issued_by_id=staff_user.id,
                issued_at=issued_dt,
                due_date=due_dt,
                returned_at=returned_dt,
                received_by_id=staff_user.id,
                status='returned'
            )
            db.session.add(r)
            db.session.flush()

            p = Payment(
                payment_code=f"PAY-HIST-{1000 + i}",
                booking_id=b.id,
                user_id=student.id,
                amount=b.total_amount,
                payment_type='rental',
                payment_method=random.choice(['UPI', 'Campus Card', 'Credit Card']),
                transaction_id=f"TXN-HIST-{random.randint(100000, 999999)}",
                status='paid',
                created_at=issued_dt
            )
            db.session.add(p)

        # 5. Seed Specific Scenarios for Demo:
        # Scenario A: Student Aarav has an Active Rental of Dell XPS ready to test return & AI damage inspection
        active_dev = dev_objs['LAP-101']
        active_dev.status = 'rented'
        bkg_active = Booking(
            booking_code='BKG-ACT-001',
            user_id=aarav.id,
            device_id=active_dev.id,
            start_date=today - timedelta(days=2),
            end_date=today + timedelta(days=5),
            total_days=7,
            total_amount=active_dev.price_per_day * 7,
            purpose="Machine Learning Capstone Model Training in PyTorch",
            status='active'
        )
        db.session.add(bkg_active)
        db.session.flush()

        rnt_active = Rental(
            rental_code='RNT-ACT-001',
            booking_id=bkg_active.id,
            user_id=aarav.id,
            device_id=active_dev.id,
            issued_by_id=staff_user.id,
            issued_at=datetime.now(timezone.utc) - timedelta(days=2),
            due_date=today + timedelta(days=5),
            initial_condition_notes='Pristine body and screen verified',
            initial_image_path='/static/uploads/inspections/demo_laptop_before.jpg',
            status='active'
        )
        db.session.add(rnt_active)

        pay_active = Payment(
            payment_code='PAY-ACT-001',
            booking_id=bkg_active.id,
            user_id=aarav.id,
            amount=bkg_active.total_amount,
            payment_type='rental',
            payment_method='UPI',
            transaction_id='TXN-UPI-99281920',
            status='paid'
        )
        db.session.add(pay_active)

        # Scenario B: Student Aarav has a Pending Booking ready for Admin Approval
        pending_dev = dev_objs['CAM-401']
        bkg_pending = Booking(
            booking_code='BKG-NEW-774',
            user_id=aarav.id,
            device_id=pending_dev.id,
            start_date=today + timedelta(days=2),
            end_date=today + timedelta(days=4),
            total_days=2,
            total_amount=pending_dev.price_per_day * 2,
            purpose="Annual Tech Symposium Keynote & Workshop Photography",
            status='pending_approval'
        )
        db.session.add(bkg_pending)

        # Scenario C: Priya Patel - Risk Profile Setup (Late returns + damage record + unpaid fine)
        # 1 overdue rental
        overdue_dev = dev_objs['TAB-201']
        overdue_dev.status = 'rented'
        bkg_priya = Booking(
            booking_code='BKG-RISK-01',
            user_id=priya.id,
            device_id=overdue_dev.id,
            start_date=today - timedelta(days=12),
            end_date=today - timedelta(days=4), # 4 days overdue!
            total_days=8,
            total_amount=overdue_dev.price_per_day * 8,
            purpose="CAD & 3D Drafting Seminar",
            status='active'
        )
        db.session.add(bkg_priya)
        db.session.flush()

        rnt_priya = Rental(
            rental_code='RNT-RISK-01',
            booking_id=bkg_priya.id,
            user_id=priya.id,
            device_id=overdue_dev.id,
            issued_by_id=staff_user.id,
            issued_at=datetime.now(timezone.utc) - timedelta(days=12),
            due_date=today - timedelta(days=4),
            status='overdue'
        )
        db.session.add(rnt_priya)

        # Pending fine for Priya
        late_fine = Fine(
            user_id=priya.id,
            rental_id=rnt_priya.id,
            reason="Late Return Fee (4 days overdue at ₹50/day)",
            amount=200.0,
            status='pending'
        )
        db.session.add(late_fine)

        # Past damaged rental for Priya
        dmg_dev = dev_objs['LAP-103']
        bkg_priya_past = Booking(
            booking_code='BKG-RISK-02',
            user_id=priya.id,
            device_id=dmg_dev.id,
            start_date=today - timedelta(days=35),
            end_date=today - timedelta(days=28),
            total_days=7,
            total_amount=dmg_dev.price_per_day * 7,
            purpose="SolidWorks Simulation",
            status='completed'
        )
        db.session.add(bkg_priya_past)
        db.session.flush()

        rnt_priya_past = Rental(
            rental_code='RNT-RISK-02',
            booking_id=bkg_priya_past.id,
            user_id=priya.id,
            device_id=dmg_dev.id,
            issued_by_id=staff_user.id,
            issued_at=datetime.now(timezone.utc) - timedelta(days=35),
            due_date=today - timedelta(days=28),
            returned_at=datetime.now(timezone.utc) - timedelta(days=25), # 3 days late
            status='returned'
        )
        db.session.add(rnt_priya_past)
        db.session.flush()

        insp_priya = ReturnInspection(
            rental_id=rnt_priya_past.id,
            inspected_by_id=staff_user.id,
            ai_damage_detected=True,
            damage_score=38.5,
            ai_analysis_summary="Prominent chassis crack and screen corner blemish detected by AI Computer Vision.",
            diff_image_path='/static/uploads/inspections/demo_laptop_damaged.jpg',
            staff_notes="Corner impact verified. Casing replacement needed.",
            fine_imposed=1200.0,
            verified=True
        )
        db.session.add(insp_priya)

        unpaid_dmg_fine = Fine(
            user_id=priya.id,
            rental_id=rnt_priya_past.id,
            reason="Physical Damage Penalty (Severity 38.5% - Moderate)",
            amount=1200.0,
            status='pending'
        )
        db.session.add(unpaid_dmg_fine)

        # Active Rental Notifications for Aarav
        rental_aarav = Notification(
            user_id=aarav.id,
            title="Device Checked Out & Active",
            message=f"Dell XPS 15 (LAP-101) is currently issued to you. Due date: {(today + timedelta(days=5)).strftime('%d %b %Y')}. Tap below to view your digital pass or submit AI return.",
            type="success",
            action_link="/active-rentals"
        )
        db.session.add(rental_aarav)

        booking_aarav = Notification(
            user_id=aarav.id,
            title="Reservation Confirmed",
            message="Your reservation for Dell XPS 15 (BKG-DEMO-01) was approved and rental pass issued.",
            type="info",
            action_link="/my-bookings"
        )
        db.session.add(booking_aarav)

        # Overdue & Inspection Notifications for Priya
        overdue_priya = Notification(
            user_id=priya.id,
            title="Overdue Loan Notice: LAP-104",
            message="Lenovo Legion 5 Pro (LAP-104) is 4 days overdue. Daily late fee of ₹50 applies. Please return to Tech Desk Room 101 immediately.",
            type="danger",
            action_link="/active-rentals"
        )
        db.session.add(overdue_priya)

        inspection_priya = Notification(
            user_id=priya.id,
            title="AI Damage Inspection Report Generated",
            message="Inspection for LAP-103 detected 38.5% severity corner damage. Penalty: ₹1,200. Tap below to review the comparative analysis.",
            type="warning",
            action_link=f"/return-device/{rnt_priya_past.id}"
        )
        db.session.add(inspection_priya)

        db.session.commit()
        print("[OK] Realistic demo scenarios seeded successfully!")
        print("\nDemo Accounts:")
        print("  - Student (Good Standing) : student@campus.edu  / student123")
        print("  - Student (Risk Profile)  : priya@campus.edu    / student123")
        print("  - Staff / Lab Manager     : staff@campus.edu    / staff123")
        print("  - Admin                   : admin@campus.edu    / admin123")

if __name__ == '__main__':
    seed_database()
