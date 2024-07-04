import enum
from datetime import datetime, timezone

from sqlalchemy import (Column, DateTime, Enum, ForeignKey, Integer, String,
                        UniqueConstraint)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


# типы состояния картинок
class ImageState(enum.Enum):
    INIT = "init"
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    DONE = "done"
    ERROR = "error"


class Image(Base):
    __tablename__ = "images"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, index=True)
    project_id = Column(Integer, index=True)
    state = Column(Enum(ImageState), default=ImageState.INIT)
    original_url = Column(String, nullable=True)
    thumb_url = Column(String, nullable=True)
    big_thumb_url = Column(String, nullable=True)
    big_1920_url = Column(String, nullable=True)
    d2500_url = Column(String, nullable=True)

    # условие уникальных полей filename и project_id
    __table_args__ = (
        UniqueConstraint("filename", "project_id", name="_filename_project_id"),
    )


class Message(Base):
    __tablename__ = "message"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, index=True, nullable=False)
    image_id = Column(Integer, ForeignKey("images.id"), nullable=False)
    message = Column(String, nullable=False)
    timestamp = Column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
