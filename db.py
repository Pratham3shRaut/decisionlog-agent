import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")

# Neon URL might start with postgresql:// or postgres://
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Initialize engine
# pool_pre_ping checks the connection health before using it
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class LoggedDecision(Base):
    __tablename__ = "logged_decisions"

    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(String(50), index=True, nullable=False)
    thread_ts = Column(String(50), index=True, nullable=False)
    summary = Column(Text, nullable=False)
    rationale = Column(Text, nullable=True)
    decision_maker = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

def init_db():
    """Create database tables if they do not exist."""
    Base.metadata.create_all(bind=engine)

def get_db():
    """Dependency helper to get a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
