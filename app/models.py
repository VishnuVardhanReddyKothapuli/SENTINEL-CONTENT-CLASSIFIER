"""
Database Models
- User: stores login/signup info + Google OAuth users
- ClassificationResult: stores every classification done by a user
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), nullable=True)
    hashed_password = Column(String(255), nullable=True)   # null for Google OAuth users
    google_id = Column(String(255), nullable=True, unique=True)  # for Google sign-in
    avatar_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # one user can have many classification results
    results = relationship("ClassificationResult", back_populates="user")


class ClassificationResult(Base):
    __tablename__ = "classification_results"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # what was classified
    media_type = Column(String(50))        # "image", "video", "youtube"
    original_filename = Column(String(255), nullable=True)
    media_url = Column(String(1000), nullable=True)   # YouTube URL if applicable

    # classification output
    label = Column(String(100))           # "safe", "suggestive", "nsfw"
    confidence_score = Column(Float)      # 0.0 to 1.0
    is_safe = Column(Boolean)
    was_blurred = Column(Boolean, default=False)
    blurred_file_path = Column(String(500), nullable=True)

    # detailed breakdown stored as JSON string
    category_scores = Column(Text, nullable=True)   # e.g. {"nude":0.02,"suggestive":0.1}

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="results")
