import os
import qrcode
from PIL import Image, ImageDraw, ImageFont

def generate_device_qr(device, upload_dir):
    """
    Generates a branded QR Code for a campus electronic device.
    Encodes JSON or direct verification URL.
    """
    qr_dir = os.path.join(upload_dir, 'qrcodes')
    os.makedirs(qr_dir, exist_ok=True)
    
    file_name = f"qr_{device.device_code}.png"
    file_path = os.path.join(qr_dir, file_name)
    
    # Payload for staff scanner
    qr_payload = f"CAMPUS_DEVICE:{device.device_code}:{device.serial_number}"
    
    # Create QR
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=3,
    )
    qr.add_data(qr_payload)
    qr.make(fit=True)
    
    qr_img = qr.make_image(fill_color="#1e293b", back_color="#ffffff").convert('RGB')
    
    # Add a branded badge frame
    w, h = qr_img.size
    badge_h = h + 70
    badge = Image.new('RGB', (w, badge_h), color='#ffffff')
    
    # Paste QR in center
    badge.paste(qr_img, (0, 10))
    
    draw = ImageDraw.Draw(badge)
    
    # Draw simple label text
    # Draw top/bottom border
    draw.line([(0, 0), (w, 0)], fill="#3b82f6", width=6)
    draw.line([(0, badge_h - 1), (w, badge_h - 1)], fill="#cbd5e1", width=2)
    
    # Draw text: Device Code and Name
    code_text = f"{device.device_code} • {device.brand}"
    serial_text = f"S/N: {device.serial_number}"
    
    # Simple centered text
    draw.text((w // 2, h + 15), code_text, fill="#0f172a", anchor="mm")
    draw.text((w // 2, h + 38), serial_text, fill="#64748b", anchor="mm")
    draw.text((w // 2, h + 55), "CAMPUS ELECTRONICS RENTAL", fill="#2563eb", anchor="mm")
    
    badge.save(file_path, "PNG")
    return f"/static/uploads/qrcodes/{file_name}"
