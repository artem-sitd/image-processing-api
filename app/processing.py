import io

from PIL import Image as PilImage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from settings import manager, minio_client

from .models import Image, ImageState, Message


# здесь и происходит обрезка картинки, сохраняет в формат S3
def resize_image(image_data, size, format_file):
    with PilImage.open(io.BytesIO(image_data)) as img:
        img.thumbnail(size, PilImage.Resampling.LANCZOS)
        output = io.BytesIO()
        img.save(output, format=format_file)
        return output.getvalue()


# здесь происходит вызов функции, отвечающая напрямую за преобразование размеров картинок
# обрезанная картинки отправляется в S3 (ссылки сохраняется в словарь)
async def process_image(
    original_data, filename, project_id: int, image_id: int, format_file, session
):
    sizes = {
        "thumb": (150, 120),
        "big_thumb": (700, 700),
        "big_1920": (1920, 1080),
        "d2500": (2500, 2500),
    }

    version_urls = {}

    for version, size in sizes.items():
        resized_data = resize_image(original_data, size, format_file)
        version_filename = f"{version}_{filename}"
        minio_client.put_object(
            "images", version_filename, io.BytesIO(resized_data), len(resized_data)
        )
        version_urls[version] = minio_client.presigned_get_object(
            "images", version_filename
        )
        message_text = (
            f"Done resize to {size}, URL in S3 minio: {version_urls[version]}"
        )
        await save_and_broadcast_message(image_id, message_text, project_id, session)

    return version_urls


# здесь вызывается другая функция, где обрезается оригинальная картинка на все размеры и добавляются в S3
# также в postgres обновляются ссылки на картинки не оригинальных размеров из S3
async def process_and_update_image(
    image: Image,
    filename: str,
    original_data: bytes,
    format_file,
    session: AsyncSession,
):
    result = await session.execute(select(Image).where(Image.id == image.id))
    image = result.scalars().one()
    try:
        image.state = ImageState.PROCESSING
        await session.commit()

        version_urls = await process_image(
            original_data, filename, image.project_id, image.id, format_file, session
        )
        image.thumb_url = version_urls["thumb"]
        image.big_thumb_url = version_urls["big_thumb"]
        image.big_1920_url = version_urls["big_1920"]
        image.d2500_url = version_urls["d2500"]
        image.state = ImageState.DONE
        await session.commit()
        message_text = (
            f"Image {image.id} in project {image.project_id} processing done."
        )

        await save_and_broadcast_message(
            image.id, message_text, image.project_id, session
        )
    except Exception as e:
        image.state = ImageState.ERROR
        await session.commit()
        raise e


async def save_and_broadcast_message(
    image_id: int, message_text: str, project_id: int, session: AsyncSession
):
    new_message = Message(
        project_id=project_id, message=message_text, image_id=image_id
    )
    session.add(new_message)
    await session.commit()

    await manager.broadcast(message_text, project_id)
