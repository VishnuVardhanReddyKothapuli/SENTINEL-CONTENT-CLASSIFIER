"""
Database Configuration
Uses SQLAlchemy with MySQL backend
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
import os
from urllib.parse import quote_plus
from dotenv import load_dotenv

load_dotenv()

# Build MySQL connection URL from env variables
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "Vishnu@123")
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_DB = os.getenv("MYSQL_DB", "nsfw_classifier")

DATABASE_URL = f"mysql+pymysql://{quote_plus(MYSQL_USER)}:{quote_plus(MYSQL_PASSWORD)}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,      # reconnect if connection dropped
    pool_recycle=3600,       # recycle connections after 1 hour
    echo=False               # set True to see SQL logs in dev
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency to get a DB session per request"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
