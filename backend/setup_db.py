"""
Database setup and migration test script.

This script can be used to:
1. Test database connectivity
2. Create all tables
3. Verify migration status
"""

import os
import sys
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import text
from app.db.base import engine, Base
from app.models import Task, TaskAttempt, Worker, DeadLetterEntry


def test_connection():
    """Test database connection."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✅ Database connection successful")
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


def create_tables():
    """Create all tables using SQLAlchemy."""
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ All tables created successfully")
        return True
    except Exception as e:
        print(f"❌ Table creation failed: {e}")
        return False


def list_tables():
    """List all tables in the database."""
    try:
        with engine.connect() as conn:
            dialect_name = engine.dialect.name.lower()
            
            if dialect_name == "sqlite":
                # SQLite: use sqlite_master
                result = conn.execute(text("""
                    SELECT name as table_name 
                    FROM sqlite_master 
                    WHERE type='table' AND name NOT LIKE 'sqlite_%'
                    ORDER BY name
                """))
            else:
                # PostgreSQL and other databases: use information_schema
                result = conn.execute(text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                    ORDER BY table_name
                """))
            
            tables = [row[0] for row in result]
            
            if tables:
                print("✅ Tables found:")
                for table in tables:
                    print(f"   - {table}")
            else:
                print("ℹ️  No tables found in database")
            
            return tables
    except Exception as e:
        print(f"❌ Failed to list tables: {e}")
        return []


def verify_models():
    """Verify that all models are properly imported and configured."""
    models = [Task, TaskAttempt, Worker, DeadLetterEntry]
    print("✅ Model verification:")
    
    for model in models:
        table_name = model.__tablename__
        columns = len(model.__table__.columns)
        indexes = len(model.__table__.indexes)
        constraints = len([c for c in model.__table__.constraints if hasattr(c, 'name')])
        
        print(f"   - {model.__name__}: table='{table_name}', columns={columns}, indexes={indexes}, constraints={constraints}")
    
    return True


if __name__ == "__main__":
    print("🔧 Database Setup Test")
    print("=" * 50)
    
    # Test connection
    if not test_connection():
        print("\n❌ Cannot proceed without database connection")
        sys.exit(1)
    
    print()
    
    # Verify models
    verify_models()
    print()
    
    # List existing tables
    existing_tables = list_tables()
    print()
    
    # Check if we need to create tables
    expected_tables = {'tasks', 'task_attempts', 'workers', 'dead_letter_queue'}
    missing_tables = expected_tables - set(existing_tables)
    
    if missing_tables:
        print(f"ℹ️  Missing tables: {missing_tables}")
        print("💡 You can create them by running:")
        print("   - Using Alembic: alembic upgrade head")
        print("   - Using SQLAlchemy: python setup_db.py --create-tables")
        
        if '--create-tables' in sys.argv:
            print("\n🔧 Creating tables with SQLAlchemy...")
            create_tables()
            print("\n📊 Updated table list:")
            list_tables()
    else:
        print("✅ All expected tables are present")
    
    print("\n🎉 Database setup verification complete!")