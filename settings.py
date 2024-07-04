import os
from pathlib import Path
from typing import ClassVar, List

from fastapi import WebSocket
from minio import Minio
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                    create_async_engine)

all_formats_image = {"JPEG": "JPEG", "PNG": "PNG", "TIFF": "TIFF", "SVG": "SVG"}
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
    db_url: ClassVar[str] = (
        f"postgresql+asyncpg://{db_env.POSTGRES_USER}:{db_env.POSTGRES_PASSWORD}@{db_env.POSTGRES_HOST}/{db_env.POSTGRES_DB}"
    )

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
    secure=False,
)
if not minio_client.bucket_exists("images"):
    minio_client.make_bucket("images")


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, project_id: int):
        await websocket.accept()
        if project_id not in self.active_connections:
            self.active_connections[project_id] = []
        self.active_connections[project_id].append(websocket)

    def disconnect(self, websocket: WebSocket, project_id: int):
        self.active_connections[project_id].remove(websocket)
        if not self.active_connections[project_id]:
            del self.active_connections[project_id]

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str, project_id: int):
        if project_id in self.active_connections:
            for connection in self.active_connections[project_id]:
                await connection.send_text(message)


manager = ConnectionManager()
