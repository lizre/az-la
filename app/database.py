import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Read the database connection string from the environment.
# In Azure this is set as an environment variable on the Container App.
# Locally you can create a .env file with this variable (see .env.example).
# The format is: postgresql://username:password@hostname/database_name?sslmode=require
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/learningdb"  # fallback for local dev
)

# The engine is the core SQLAlchemy object that knows how to talk to the database.
# It manages a pool of connections so the app doesn't open a new connection on every request.
engine = create_engine(DATABASE_URL)

# SessionLocal is a factory for creating database sessions.
# A session is like a conversation with the database — you open one, do some reads/writes,
# then close it. autocommit=False means changes are only saved when you explicitly call commit().
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base is the parent class that all database models inherit from.
# SQLAlchemy uses it to track which classes represent tables.
Base = declarative_base()


def get_db():
    """
    A FastAPI dependency that provides a database session for the duration of a request.

    FastAPI calls this function automatically whenever an endpoint declares
    `db: Session = Depends(get_db)` as a parameter. It opens a session at the
    start of the request and closes it when the request finishes — even if an
    error occurred. The `try/finally` guarantees the session is always closed.
    """
    db = SessionLocal()
    try:
        yield db       # hand the session to the endpoint function
    finally:
        db.close()     # always runs, whether the request succeeded or failed
