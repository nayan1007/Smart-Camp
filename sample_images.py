import os
from PIL import Image, ImageDraw, ImageFont

def ensure_sample_assets(upload_dir):
    """
    Creates realistic sample device photos and before/after damage demo images
    using Pillow so that the application has complete visual assets out of the box.
    """
    dev_dir = os.path.join(upload_dir, 'devices')
    insp_dir = os.path.join(upload_dir, 'inspections')
    os.makedirs(dev_dir, exist_ok=True)
    os.makedirs(insp_dir, exist_ok=True)

    # 1. Device category graphics
    device_types = [
        ('laptop_macbook.jpg', 'MacBook Pro 16" M2', '#0f172a', '#3b82f6', 'Laptop'),
        ('laptop_dell.jpg', 'Dell XPS 15 (RTX 3050)', '#1e293b', '#2563eb', 'Laptop'),
        ('laptop_thinkpad.jpg', 'Lenovo ThinkPad P14s', '#111827', '#ef4444', 'Laptop'),
        ('laptop_gaming.jpg', 'ASUS ROG Zephyrus G14', '#090d16', '#8b5cf6', 'Laptop'),
        ('laptop_hp.jpg', 'HP Pavilion 14 Lightweight Laptop', '#0f172a', '#0ea5e9', 'Laptop'),
        ('laptop_acer.jpg', 'Acer Aspire 5 Student Laptop', '#1e293b', '#10b981', 'Laptop'),
        ('tablet_ipad.jpg', 'Apple iPad Pro 12.9" + Pencil', '#1e1b4b', '#6366f1', 'Tablet'),
        ('tablet_galaxy.jpg', 'Samsung Galaxy Tab S9 Ultra', '#022c22', '#10b981', 'Tablet'),
        ('camera_sony.jpg', 'Sony Alpha A7 IV Mirrorless', '#1c1917', '#f97316', 'Camera'),
        ('camera_canon.jpg', 'Canon EOS R6 Mark II', '#18181b', '#dc2626', 'Camera'),
        ('projector_epson.jpg', 'Epson 4K 4000-Lumen Projector', '#0c4a6e', '#0284c7', 'Projector'),
        ('projector_benq.jpg', 'BenQ Conference Laser Projector', '#134e4a', '#14b8a6', 'Projector'),
        ('lab_oscilloscope.jpg', 'Rigol 100MHz Digital Oscilloscope', '#2e1065', '#a855f7', 'Lab Equipment'),
        ('lab_raspberry.jpg', 'Raspberry Pi 4 IoT Lab Kit', '#4c0519', '#e11d48', 'Lab Equipment'),
        ('lab_arduino.jpg', 'Arduino Ultimate Robotics Kit', '#042f2e', '#0d9488', 'Lab Equipment'),
        ('audio_bose.jpg', 'Bose QuietComfort 45 ANC', '#172554', '#3b82f6', 'Accessories'),
        ('charger_usbc.jpg', 'Anker 140W USB-C GaN Charger Hub', '#1e293b', '#64748b', 'Accessories'),
        ('default.jpg', 'Campus Smart Equipment', '#1e293b', '#3b82f6', 'Device')
    ]

    for filename, title, bg_color, accent_color, cat_name in device_types:
        fpath = os.path.join(dev_dir, filename)
        if not os.path.exists(fpath):
            img = Image.new('RGB', (600, 400), color=bg_color)
            draw = ImageDraw.Draw(img)

            # Draw accent design lines
            draw.rectangle([(20, 20), (580, 380)], outline=accent_color, width=2)
            draw.rectangle([(20, 20), (580, 50)], fill=accent_color)
            
            draw.text((30, 26), f"CAMPUS TECH INVENTORY • {cat_name.upper()}", fill="#ffffff")
            
            # Central graphic box
            draw.rectangle([(80, 90), (520, 310)], fill="#0f172a", outline="#334155", width=2)
            draw.text((300, 180), title, fill="#f8fafc", anchor="mm")
            draw.text((300, 220), f"[ {cat_name} Verified Hardware ]", fill="#94a3b8", anchor="mm")
            
            # Bottom status
            draw.text((300, 345), "SMART CAMPUS ELECTRONICS RENTAL", fill="#64748b", anchor="mm")
            img.save(fpath, "JPEG", quality=90)

    # 2. Before & After Demo Images for AI Damage Detection Showcase
    before_demo = os.path.join(insp_dir, 'demo_laptop_before.jpg')
    after_demo_damaged = os.path.join(insp_dir, 'demo_laptop_damaged.jpg')
    after_demo_clean = os.path.join(insp_dir, 'demo_laptop_clean.jpg')

    # Baseline Pristine Image
    if not os.path.exists(before_demo):
        img_b = Image.new('RGB', (640, 480), color="#1e293b")
        draw_b = ImageDraw.Draw(img_b)
        # Draw pristine laptop body & screen
        draw_b.rectangle([(60, 40), (580, 380)], fill="#0f172a", outline="#94a3b8", width=4) # screen bezel
        draw_b.rectangle([(90, 70), (550, 350)], fill="#1e3a8a") # blue screen display
        draw_b.text((320, 210), "PRISTINE SCREEN DISPLAY", fill="#ffffff", anchor="mm")
        draw_b.rectangle([(40, 380), (600, 440)], fill="#334155", outline="#475569", width=2) # keyboard deck
        img_b.save(before_demo, "JPEG", quality=92)

    # Damaged Image (with prominent simulated cracks & corner dent)
    if not os.path.exists(after_demo_damaged):
        img_d = Image.new('RGB', (640, 480), color="#1e293b")
        draw_d = ImageDraw.Draw(img_d)
        draw_d.rectangle([(60, 40), (580, 380)], fill="#0f172a", outline="#94a3b8", width=4)
        draw_d.rectangle([(90, 70), (550, 350)], fill="#1e3a8a")
        draw_d.text((320, 210), "PRISTINE SCREEN DISPLAY", fill="#ffffff", anchor="mm")
        draw_d.rectangle([(40, 380), (600, 440)], fill="#334155", outline="#475569", width=2)

        # Draw simulated spiderweb crack lines on screen
        crack_color = "#ffffff"
        draw_d.line([(240, 140), (330, 230)], fill=crack_color, width=4)
        draw_d.line([(330, 230), (410, 190)], fill=crack_color, width=3)
        draw_d.line([(330, 230), (360, 310)], fill=crack_color, width=4)
        draw_d.line([(330, 230), (270, 270)], fill=crack_color, width=3)
        draw_d.line([(270, 270), (210, 330)], fill=crack_color, width=3)

        # Draw deep scratch on bottom right chassis
        draw_d.line([(480, 400), (550, 425)], fill="#ef4444", width=5)
        draw_d.rectangle([(540, 395), (585, 435)], fill="#7f1d1d") # dent patch

        img_d.save(after_demo_damaged, "JPEG", quality=92)

    # Clean Return Image
    if not os.path.exists(after_demo_clean):
        img_c = Image.new('RGB', (640, 480), color="#1e293b")
        draw_c = ImageDraw.Draw(img_c)
        draw_c.rectangle([(60, 40), (580, 380)], fill="#0f172a", outline="#94a3b8", width=4)
        draw_c.rectangle([(90, 70), (550, 350)], fill="#1e3a8a")
        draw_c.text((320, 210), "PRISTINE SCREEN DISPLAY", fill="#ffffff", anchor="mm")
        draw_c.rectangle([(40, 380), (600, 440)], fill="#334155", outline="#475569", width=2)
        img_c.save(after_demo_clean, "JPEG", quality=92)
