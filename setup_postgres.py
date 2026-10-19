"""
PostgreSQL Setup & Migration Utility for Smart Campus Electronics Rental
========================================================================
This script:
1. Verifies connectivity to the PostgreSQL server.
2. Checks if the target database ('campus_rental') exists, creating it if necessary.
3. Initializes all database tables via SQLAlchemy.
4. Optionally seeds realistic demo accounts, devices, and history into PostgreSQL.
"""

import os
import sys
import socket
from urllib.parse import urlparse

def check_postgres_port(host, port, timeout=2.0):
    """Tests raw TCP socket connectivity to PostgreSQL host:port."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        result = s.connect_ex((host, int(port)))
        s.close()
        return result == 0
    except Exception:
        return False


def setup_postgresql():
    print("=" * 70)
    print(" Smart Campus Electronics Rental - PostgreSQL Database Setup")
    print("=" * 70)

    # 1. Parse connection settings
    from config import Config
    raw_uri = Config.SQLALCHEMY_DATABASE_URI
    print(f"\n[INFO] Configured Database URI: {raw_uri}")

    # Extract connection credentials
    clean_uri = raw_uri.replace('+psycopg2', '').replace('+pg8000', '')
    parsed = urlparse(clean_uri)

    host = parsed.hostname or 'localhost'
    port = parsed.port or 5432
    user = parsed.username or 'postgres'
    password = parsed.password or 'postgres'
    dbname = parsed.path.lstrip('/') or 'campus_rental'

    print(f"  - Host     : {host}")
    print(f"  - Port     : {port}")
    print(f"  - User     : {user}")
    print(f"  - Database : {dbname}")

    # 2. Check port connectivity
    print(f"\n[1/4] Checking PostgreSQL server on {host}:{port}...")
    if not check_postgres_port(host, port):
        print(f"\n[ERROR] Could not connect to PostgreSQL server at {host}:{port}.")
        print("  Possible reasons:")
        print("    1. PostgreSQL service is stopped. (Start via Windows Services or 'net start postgresql-x64-XX')")
        print("    2. PostgreSQL is running on a different port or Docker container.")
        print("    3. If using a cloud database (e.g. Supabase, Neon), check your DATABASE_URL environment variable.")
        print("\nTip: To configure custom PostgreSQL credentials, set environment variables:")
        print("  $env:DATABASE_URL='postgresql://user:password@localhost:1234/campus_rental'")
        print("  OR set POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB")
        return False

    print("  [SUCCESS] PostgreSQL port is reachable!")

    # 3. Create database if it does not exist
    print(f"\n[2/4] Verifying database '{dbname}' exists on PostgreSQL...")
    try:
        import psycopg2
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

        # Connect to default 'postgres' database to check/create target database
        conn = psycopg2.connect(
            dbname='postgres',
            user=user,
            password=password,
            host=host,
            port=int(port)
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()

        cur.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s", (dbname,))
        exists = cur.fetchone()
        if not exists:
            print(f"  Creating database '{dbname}'...")
            cur.execute(f'CREATE DATABASE "{dbname}"')
            print(f"  [SUCCESS] Database '{dbname}' created successfully!")
        else:
            print(f"  [SUCCESS] Database '{dbname}' already exists.")

        cur.close()
        conn.close()
    except Exception as e:
        print(f"  [WARNING] Could not run automatic DB create: {e}")
        print("  Proceeding to connect directly to target database...")

    # 4. Initialize tables with SQLAlchemy
    print(f"\n[3/4] Creating all tables on PostgreSQL...")
    try:
        from app import create_app
        from app.models import db

        app = create_app()
        with app.app_context():
            db.create_all()
            print("  [SUCCESS] All tables created successfully on PostgreSQL!")

            # 5. Seed data
            print(f"\n[4/4] Seeding initial campus devices, users, and ML models...")
            from seed_data import seed_database
            seed_database()
            print("  [SUCCESS] Initial PostgreSQL database seeded with full catalog!")

        print("\n" + "=" * 70)
        print(" [COMPLETED] PostgreSQL database connectivity is fully operational!")
        print("=" * 70)
        return True

    except Exception as e:
        print(f"\n[ERROR] Failed to initialize tables: {e}")
        return False


if __name__ == '__main__':
    setup_postgresql()
