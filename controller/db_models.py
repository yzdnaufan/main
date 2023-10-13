from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime, Enum
from sqlalchemy_utils import UUIDType
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

import uuid
import enum

from .db import Base

class User(Base):
    __tablename__ = "users_fs"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String)
    email = Column(String)
    phone = Column(String, unique=True, index=True)
    verified = Column(Boolean)
    biodata=Column(String)