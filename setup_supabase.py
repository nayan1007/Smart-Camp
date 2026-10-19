"""
Supabase PostgreSQL Database Configuration & Migration Utility
---------------------------------------------------------------
This script helps you connect, configure, create tables, and seed
data into your Supabase PostgreSQL cloud database.

Usage:
    python setup_supabase.py "<SUPABASE_DATABASE_URL>"
    or
    python setup_supabase.py
    (reads SUPABASE_DATABASE_URL from .env or prompts for input)
"""

import sys
import os
import re
import urllib.parse
from dotenv import load_dotenv

# Force reload of .env
load_dotenv(override=True)

def normalize_supabase_url(url: str) -> str:
    """Ensures psycopg2 driver and sslmode=require are configured properly."""
    url = url.strip().strip("'\"")
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif url.startswith("postgresql://") and "+psycopg2" not in url:
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
    
    # Supabase strictly requires SSL
    if "sslmode" not in url:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}sslmode=require"
    return url

def update_env_file(supabase_url: str):
    """Updates or adds SUPABASE_DATABASE_URL in .env file."""
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    lines = []
    found = False

    # Store standard postgresql:// format in .env for portability
    portable_url = supabase_url.replace("postgresql+psycopg2://", "postgresql://")

    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("SUPABASE_DATABASE_URL=") or line.startswith("DATABASE_URL="):
                    if not found and line.startswith("SUPABASE_DATABASE_URL="):
                        lines.append(f"SUPABASE_DATABASE_URL={portable_url}\n")
                        found = True
                    elif line.startswith("DATABASE_URL="):
                        lines.append(f"# {line.strip()}\n")
                    else:
                        lines.append(line)
                else:
                    lines.append(line)

    if not found:
        lines.insert(0, f"SUPABASE_DATABASE_URL={portable_url}\n")

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    print(f"[OK] Saved SUPABASE_DATABASE_URL to {env_path}")

def run_setup(connection_url: str):
    normalized_url = normalize_supabase_url(connection_url)
    os.environ["SUPABASE_DATABASE_URL"] = normalized_url
    os.environ["DATABASE_URL"] = normalized_url

    print("=" * 70)
    print(" [*] SMART CAMPUS RENTAL - SUPABASE DATABASE MIGRATION & SETUP")
    print("=" * 70)

    # Mask password for display
    safe_display = re.sub(r":([^:@]+)@", r":********@", normalized_url)
    print(f"Target Database URI: {safe_display}\n")

    # Step 1: Test raw connection
    print("1. Testing connection to Supabase...")
    try:
        import psycopg2
        # Convert dialect for psycopg2.connect
        raw_conn_str = normalized_url.replace("postgresql+psycopg2://", "postgresql://")
        conn = psycopg2.connect(raw_conn_str)
        cur = conn.cursor()
        cur.execute("SELECT version();")
        ver = cur.fetchone()[0]
        print(f"   [SUCCESS] Connected to PostgreSQL version: {ver[:50]}...")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"   [ERROR] Could not connect to Supabase: {e}")
        print("\nTroubleshooting tips:")
        print(" - Verify your password in the connection string.")
        print(" - If using Supabase Pooler, make sure the project reference and password are correct.")
        print(" - Ensure your network allows outbound connections to Supabase port 5432 or 6543.")
        return False

    # Step 2: Initialize Flask app and create all tables
    print("\n2. Creating schema and database tables on Supabase...")
    try:
        from app import create_app
        from app.models import db, User, DeviceCategory, Device, Booking, Rental, ReturnInspection, Payment, Fine, Notification, MaintenanceLog, AIDemandPrediction, ChatMessage
        
        # Override config URI
        app = create_app()
        app.config["SQLALCHEMY_DATABASE_URI"] = normalized_url
        
        with app.app_context():
            db.create_all()
            print("   [SUCCESS] All tables created successfully!")

            # Step 3: Run seed verification
            print("\n3. Seeding categories, electronic & non-electronic devices, and users...")
            from verify_and_seed import new_categories, sample_non_electronics

            # Add categories
            for cat_name, icon, desc in new_categories:
                if not DeviceCategory.query.filter_by(name=cat_name).first():
                    db.session.add(DeviceCategory(name=cat_name, icon=icon, description=desc))
                    print(f"   + Added category: {cat_name}")

            # Check if users exist, otherwise run seed_data
            if User.query.count() == 0:
                print("   -> Supabase is fresh! Seeding base users and inventory...")
                from seed_data import seed_database
                seed_database()
            else:
                print(f"   -> Found {User.query.count()} existing users.")

            # Seed non-electronic items if missing
            sports_cat = DeviceCategory.query.filter_by(name="Sports Equipment").first()
            lab_cat = DeviceCategory.query.filter_by(name="Lab Stationery & Tools").first()
            book_cat = DeviceCategory.query.filter_by(name="Library Books & Courseware").first()
            furniture_cat = DeviceCategory.query.filter_by(name="Campus Furniture & Gear").first()

            cat_map = {
                "SPT-101": sports_cat.id if sports_cat else 1,
                "LAB-201": lab_cat.id if lab_cat else 1,
                "BOK-301": book_cat.id if book_cat else 1,
                "FUR-401": furniture_cat.id if furniture_cat else 1,
            }

            for item in sample_non_electronics:
                if not Device.query.filter_by(device_code=item["code"]).first():
                    dev = Device(
                        device_code=item["code"],
                        name=item["name"],
                        category_id=cat_map.get(item["code"], 1),
                        brand=item["brand"],
                        model=item["model"],
                        serial_number=item["serial"],
                        price_per_day=item["price_per_day"],
                        deposit_amount=item["deposit_amount"],
                        is_non_electronic=item["is_non_electronic"],
                        status=item["status"],
                        condition=item["condition"],
                        location=item["location"],
                        specs=item["specs"],
                        tags=item["tags"],
                        image_url=item["image_url"]
                    )
                    db.session.add(dev)
                    print(f"   + Added non-electronic item: {item['name']}")

            # Calibrate deposit amounts
            for d in Device.query.all():
                if not d.deposit_amount or d.deposit_amount <= 0:
                    d.deposit_amount = round(max(300.0, d.price_per_day * 3.0), 2)

            db.session.commit()
            print("   [SUCCESS] Seed data and deposit amounts verified!")

            # Final summary
            print("\n" + "=" * 70)
            print(" [SUCCESS] SUPABASE MIGRATION COMPLETE & READY!")
            print("=" * 70)
            print(f" - Total Users in Supabase:    {User.query.count()}")
            print(f" - Total Categories:          {DeviceCategory.query.count()}")
            print(f" - Total Devices/Gear:        {Device.query.count()}")
            print(f" - Total Active Rentals:      {Rental.query.count()}")
            print("=" * 70)

        # Save to .env
        update_env_file(normalized_url)
        return True

    except Exception as e:
        print(f"   [ERROR] Failed during table creation or seeding: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    url_arg = None
    if len(sys.argv) > 1:
        url_arg = sys.argv[1].strip()

    if not url_arg:
        url_arg = os.environ.get("SUPABASE_DATABASE_URL") or os.environ.get("DATABASE_URL")

    # If user provided the https:// API URL instead of postgresql://
    if url_arg and url_arg.startswith(('http://', 'https://')):
        match = re.search(r'https?://([^.]+)\.supabase\.co', url_arg)
        project_ref = match.group(1) if match else "lhrunhquwxedaqrfvnhs"
        supa_pass = os.environ.get("SUPABASE_DB_PASSWORD") or os.environ.get("SUPABASE_PASSWORD")
        if not supa_pass:
            print(f"\n[Detected Supabase Project]: {project_ref}")
            print(f"To connect to PostgreSQL, please enter your Supabase Database Password.")
            print("(The password you set when creating the Supabase project)")
            try:
                supa_pass = input("Enter Supabase Database Password: ").strip()
            except EOFError:
                supa_pass = ""
        
        if supa_pass:
            encoded_pass = urllib.parse.quote_plus(supa_pass)
            url_arg = f"postgresql://postgres:{encoded_pass}@db.{project_ref}.supabase.co:5432/postgres?sslmode=require"
        else:
            url_arg = None

    if not url_arg:
        print("=" * 70)
        print("  SUPABASE DATABASE CONFIGURATION")
        print("=" * 70)
        print("Enter your Supabase connection string.")
        print("How to get it:")
        print("  1. Go to https://supabase.com/dashboard")
        print("  2. Select your project -> Project Settings -> Database")
        print("  3. Under 'Connection string' -> choose 'URI' (Direct or Session Pooler)")
        print("  4. Example format:")
        print("     postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres")
        print("     or (Pooler):")
        print("     postgresql://postgres.[PROJECT-REF]:[YOUR-PASSWORD]@aws-0-[REGION].pooler.supabase.com:5432/postgres")
        print("=" * 70)
        try:
            url_arg = input("\nPaste your Supabase URI: ").strip()
        except EOFError:
            url_arg = ""

    if not url_arg:
        print("\n[!] No Supabase URL provided. Exiting.")
        sys.exit(1)

    success = run_setup(url_arg)
    sys.exit(0 if success else 1)
