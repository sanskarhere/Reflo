"""SQLAlchemy engine/session setup. DATABASE_URL is sqlite locally, Postgres on Render."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import DATABASE_URL

# Render (like Heroku before it) hands out connection strings starting with
# "postgres://", which SQLAlchemy 2.0 no longer accepts — it needs
# "postgresql://". Converting here rather than relying on the platform to
# get this right avoids a very common, very confusing first-deploy crash.
_db_url = DATABASE_URL
if _db_url.startswith("postgres://"):
    _db_url = _db_url.replace("postgres://", "postgresql://", 1)

connect_args = {"check_same_thread": False} if _db_url.startswith("sqlite") else {}
engine = create_engine(_db_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
