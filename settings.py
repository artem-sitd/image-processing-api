import os
from pathlib import Path
from typing import ClassVar
from minio import Minio
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from fastapi import WebSocket
from app.models import Message

env_file = (
    Path(__file__).parent / ".env.docker"
    if os.getenv("USE_DOCKER")
    else Path(__file__).parent / ".env"
)


class DatabaseEnv(BaseSettings):
    model_config = SettingsConfigDict(
        extra="ignore", env_file=env_file, env_file_encoding="utf-8"
    )
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_DB: str


class DatabaseConnect(BaseSettings):
    db_env: ClassVar[DatabaseEnv] = DatabaseEnv()
    db_url: ClassVar[
        str
    ] = f"postgresql+asyncpg://{db_env.POSTGRES_USER}:{db_env.POSTGRES_PASSWORD}@{db_env.POSTGRES_HOST}/{db_env.POSTGRES_DB}"

    engine: ClassVar = create_async_engine(db_url)
    async_session: ClassVar = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )

    async def get_session(self) -> AsyncSession:
        async with self.async_session() as session:
            yield session


db_settings = DatabaseConnect()


class MinioENV(BaseSettings):
    model_config = SettingsConfigDict(
        extra="ignore", env_file=env_file, env_file_encoding="utf-8"
    )
    access_key: str
    secret_key: str
    endpoint: str


minio_env = MinioENV()

minio_client = Minio(
    endpoint=minio_env.endpoint,
    access_key=minio_env.access_key,
    secret_key=minio_env.secret_key,
    secure=False
)
if not minio_client.bucket_exists("images"):
    minio_client.make_bucket("images")


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str, project_id: int, image_id: int):
        # записываем в Бд каждое сообщение
        session = db_settings.get_session()
        new_message = Message(project_id=project_id, image_id=image_id, message=message)
        session.add(new_message)
        await session.commit()

        for connection in self.active_connections:
            await connection.send_text(message)


manager = ConnectionManager()
