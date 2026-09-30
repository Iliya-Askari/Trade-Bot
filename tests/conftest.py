import os
import tempfile
import pytest
from app.config.settings import settings

# Override the database URL *before* any other modules import SessionLocal
db_fd, db_path = tempfile.mkstemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"

# Re-initialize the test database settings
settings.DATABASE_URL = os.environ["DATABASE_URL"]

from app.database.session import Base, engine, SessionLocal

@pytest.fixture(autouse=True)
def setup_test_db():
    # Create all tables in the temporary database
    Base.metadata.create_all(bind=engine)

    yield

    # Drop all tables after the test
    Base.metadata.drop_all(bind=engine)

    # Optional: Close all sessions
    SessionLocal.remove() if hasattr(SessionLocal, 'remove') else None

@pytest.fixture(scope="session", autouse=True)
def cleanup_temp_db():
    yield
    os.close(db_fd)
    os.remove(db_path)
