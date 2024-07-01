from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, Integer, String, Enum, UniqueConstraint

Base = DeclarativeBase()


# типы состояния картинок
class ImageState(Enum):
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
