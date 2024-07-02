from fastapi import APIRouter, UploadFile, Depends, BackgroundTasks, WebSocket, WebSocketDisconnect
from app.models import Image, ImageState, Message
from settings import db_settings, minio_client, manager
import io
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from .processing import process_and_update_image

router = APIRouter()


# главный функциональный роут для приема картинки, создания копий всех размеров
@router.post("/upload_image")
async def create_upload_link(file: UploadFile, project_id: int, background_tasks: BackgroundTasks,
                             session: AsyncSession = Depends(db_settings.get_session)):
    original_data = await file.read()

    # загрузка оригинальной картинки в S3
    minio_client.put_object("images", file.filename, io.BytesIO(original_data), len(original_data))
    original_url = minio_client.presigned_get_object("images", file.filename)

    # создание записи в БД, со ссылкой на S3 minio с оригинальным размером
    new_image = Image(filename=file.filename, project_id=project_id, state=ImageState.UPLOADED,
                      original_url=original_url)
    session.add(new_image)
    await session.commit()

    # создание фоновой задачи по копированию картинок со всеми видами размеров
    background_tasks.add_task(process_and_update_image, session, new_image, file.filename, original_data)

    return {"original_image_link_s3": new_image.original_url, "params": {}, "image_id": new_image.id}


@router.get("/projects/{project_id}/images")
async def get_images(project_id: int, session: AsyncSession = Depends(db_settings.get_session)):
    """Показывает все ссылки из S3 minio на картинки из проекта"""
    result = await session.execute(select(Image).filter_by(project_id=project_id))
    images = result.scalars().all()
    return {"images": [image for image in images]}


@router.websocket("/ws/{project_id}")
async def websocket_endpoint(websocket: WebSocket, project_id: int,
                             session: AsyncSession = Depends(db_settings.get_session)):
    """Здесь будут все сообщения по конкретному проекту"""
    await manager.connect(websocket)
    try:
        result = await session.execute(select(Message).filter_by(project_id=project_id).order_by(Message.timestamp))
        messages = result.scalars().all()
        for message in messages:
            await websocket.send_text(message.message)

        while True:
            data = await websocket.receive_text()
            await manager.send_personal_message(f"You wrote: {data}", websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@router.get("/")
async def get_index():
    return {"message": "все работает"}
