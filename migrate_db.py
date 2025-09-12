#!/usr/bin/env python3

import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

# Database connection
DATABASE_URL = os.getenv('DATABASE_URL', 'mysql+pymysql://root:UqxygMcqERznUoFOKtutbJQBZxuKNbru@mainline.proxy.rlwy.net:31375/railway')
engine = create_engine(DATABASE_URL)

def migrate_database():
    print("🔄 Starting database migration...")

    try:
        with engine.connect() as conn:
            # Add location columns to email_tracking table
            print("Adding location columns to email_tracking table...")

            try:
                conn.execute(text("ALTER TABLE email_tracking ADD COLUMN last_latitude FLOAT NULL"))
                print("✅ Added last_latitude column")
            except Exception as e:
                if "Duplicate column name" in str(e):
                    print("⚠️  last_latitude column already exists")
                else:
                    print(f"❌ Error adding last_latitude: {e}")

            try:
                conn.execute(text("ALTER TABLE email_tracking ADD COLUMN last_longitude FLOAT NULL"))
                print("✅ Added last_longitude column")
            except Exception as e:
                if "Duplicate column name" in str(e):
                    print("⚠️  last_longitude column already exists")
                else:
                    print(f"❌ Error adding last_longitude: {e}")

            try:
                conn.execute(text("ALTER TABLE email_tracking ADD COLUMN last_location VARCHAR(255) NULL"))
                print("✅ Added last_location column")
            except Exception as e:
                if "Duplicate column name" in str(e):
                    print("⚠️  last_location column already exists")
                else:
                    print(f"❌ Error adding last_location: {e}")

            # Create open_events table if it doesn't exist
            print("Creating open_events table...")
            try:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS open_events (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        tracking_id VARCHAR(64) NOT NULL,
                        open_time DATETIME NOT NULL,
                        ip_address VARCHAR(100) NULL,
                        port VARCHAR(10) NULL,
                        latitude FLOAT NULL,
                        longitude FLOAT NULL,
                        location VARCHAR(255) NULL,
                        user_agent TEXT NULL,
                        INDEX idx_tracking_id (tracking_id),
                        INDEX idx_open_time (open_time)
                    )
                """))
                print("✅ Created open_events table")
            except Exception as e:
                print(f"❌ Error creating open_events table: {e}")

            conn.commit()

        print("✅ Database migration completed successfully!")

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

    return True

if __name__ == "__main__":
    migrate_database()