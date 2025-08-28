from sqlalchemy.orm import DeclarativeBase
from pydantic import BaseModel
from datetime import datetime

class Base(DeclarativeBase):
    __abstract__ = True
    pass