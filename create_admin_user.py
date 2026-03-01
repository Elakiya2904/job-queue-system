"""Create admin user for testing."""
import os
import sys
from pathlib import Path

# Set up environment
os.environ["DATABASE_URL"] = "sqlite:///./data/job_queue.db"

# Add backend to path
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

# Import necessary modules
from app.core.security import hash_password
import sqlite3

def create_admin_user():
    """Create admin user in the database."""
    
    # Connect to database
    db_path = backend_dir / "data" / "job_queue.db"
    
    # Ensure data directory exists
    db_path.parent.mkdir(exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create users table if it doesn't exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            role VARCHAR(50) DEFAULT 'user',
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Check if admin user exists
    cursor.execute("SELECT id FROM users WHERE email = ?", ("admin@example.com",))
    if cursor.fetchone():
        print("[OK] Admin user already exists")
        conn.close()
        return True
    
    # Create admin user
    password_hash = hash_password("admin123")
    
    cursor.execute("""
        INSERT INTO users (email, password_hash, role, is_active)
        VALUES (?, ?, ?, ?)
    """, ("admin@example.com", password_hash, "admin", True))
    
    conn.commit()
    conn.close()
    
    print("[OK] Admin user created successfully!")
    print("   Email: admin@example.com")
    print("   Password: admin123")
    return True

if __name__ == "__main__":
    try:
        create_admin_user()
    except Exception as e:
        print(f"[ERROR] Failed to create admin user: {e}")
        sys.exit(1)