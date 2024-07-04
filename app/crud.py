import io

from fastapi import (APIRouter, BackgroundTasks, Depends, HTTPException,
                     Request, WebSocket, WebSocketDisconnect, status)
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Image, ImageState, Message
from settings import all_formats_image, db_settings, manager, minio_client

from .processing import process_and_update_image
from .schemas import UploadInputSchema

router = APIRouter()


# главный функциональный роут для приема картинки, создания копий всех размеров
@router.post("/upload_image")
async def create_upload_link(
        background_tasks: BackgroundTasks,
        input_value: UploadInputSchema = Depends(UploadInputSchema.as_form),
        session: AsyncSession = Depends(db_settings.get_session),
):
    try:
        project_id = input_value.project_id
        file = input_value.file
        original_data = await file.read()
    except Exception as e:
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"ошибка при прочтении картинки: {e}",
        )

    if not any(file.filename.upper().endswith(format) for format in all_formats_image):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="не подходящее расширение файла",
        )

    # загрузка оригинальной картинки в S3
    minio_client.put_object(
        "images", file.filename, io.BytesIO(original_data), len(original_data)
    )
    original_url = minio_client.presigned_get_object("images", file.filename)

    # создание записи в БД, со ссылкой на S3 minio с оригинальным размером
    new_image = Image(
        filename=file.filename,
        project_id=project_id,
        state=ImageState.UPLOADED,
        original_url=original_url,
    )

    session.add(new_image)
    await session.commit()

    # создание фоновой задачи по копированию картинок со всеми видами размеров
    point_index = file.filename.find(".")
    format_file = all_formats_image.get(file.filename.upper()[point_index + 1:])
    background_tasks.add_task(
        process_and_update_image,
        new_image,
        file.filename,
        original_data,
        format_file,
        session,
    )
    await session.commit()
    return {
        "original_image_link_s3": new_image.original_url,
        "params": {},
        "image_id": new_image.id,
    }


@router.websocket("/ws/{project_id}")
async def websocket_endpoint(
        websocket: WebSocket,
        project_id: int,
        session: AsyncSession = Depends(db_settings.get_session),
):
    await manager.connect(websocket, project_id)
    try:
        result = await session.execute(
            select(Message).filter_by(project_id=project_id).order_by(Message.timestamp)
        )
        messages = result.scalars().all()
        if not messages:
            await manager.send_personal_message(
                f"project_id = {project_id} do not have message", websocket
            )
        for message in messages:
            await manager.send_personal_message(message.message, websocket)

        while True:
            data = await websocket.receive_text()
            await manager.send_personal_message(f"You wrote: {data}", websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket, project_id)


# Маршрут для рендеринга HTML страницы
@router.get("/projects/{project_id}", response_class=HTMLResponse)
async def get(request: Request, project_id: int):
    with open("app/ws.html") as file:
        html_content = file.read()
    return HTMLResponse(content=html_content, status_code=200)
