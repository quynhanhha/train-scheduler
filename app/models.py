"""
SQLAlchemy ORM models for the train scheduler application.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db import Base


# Placeholder for future models
# Example:
# class Train(Base):
#     __tablename__ = "trains"
#     
#     id = Column(Integer, primary_key=True, index=True)
#     train_number = Column(String, unique=True, index=True)
#     name = Column(String)

