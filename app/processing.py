import io
from sqlalchemy.ext.asyncio import AsyncSession
from .models import Image, ImageState, Message
from settings import minio_client, manager
from PIL import Image as PilImage


# здесь и происходит обрезка картинки, сохраняет в формат S3
def resize_image(image_data, size):
    with PilImage.open(io.BytesIO(image_data)) as img:
        img.thumbnail(size, PilImage.Resampling.LANCZOS)
        output = io.BytesIO()
        img.save(output, format="JPEG")
        return output.getvalue()


# здесь происходит вызов функции, отвечающая напрямую за преобразование размеров картинок
# обрезанная картинки отправляется в S3 (ссылки сохраняется в словарь)
def process_image(original_data, filename):
    sizes = {
        "thumb": (150, 120),
        "big_thumb": (700, 700),
        "big_1920": (1920, 1080),
        "d2500": (2500, 2500),
    }

    version_urls = {}

    for version, size in sizes.items():
        manager.broadcast(f"Try resize to {size}")
        resized_data = resize_image(original_data, size)
        version_filename = f"{filename}_{version}.jpg"
        minio_client.put_object("images", version_filename, io.BytesIO(resized_data), len(resized_data))
        version_urls[version] = minio_client.presigned_get_object("images", version_filename)
        manager.broadcast(f"Done resize to {size}, URL in S3 minio: {version_urls[version]}")
    return version_urls


# здесь вызывается другая функция, где обрезается оригинальная картинка на все размеры и добавляются в S3
# также в postgres обновляются ссылки на картинки не оригинальных размеров из S3
async def process_and_update_image(session: AsyncSession, image: Image, filename: str, original_data: bytes):
    try:
        # Обновляем состояние изображения на "PROCESSING"
        image.state = ImageState.PROCESSING
        await session.commit()
        # Процессинг изображения
        version_urls = process_image(original_data, filename)

        # Обновление ссылок в базе данных и состояние на "DONE"
        image.thumb_url = version_urls["thumb"]
        image.big_thumb_url = version_urls["big_thumb"]
        image.big_1920_url = version_urls["big_1920"]
        image.d2500_url = version_urls["d2500"]
        image.state = ImageState.DONE
        await session.commit()

        message_text = f"Image {image.id} processing done."
        new_message = Message(project_id=image.project_id, image_id=image.id, message=message_text)
        session.add(new_message)
        await session.commit()

        await manager.broadcast(message_text)
    except Exception as e:
        # если что-то пошло не так - меняем состояние картинки на ERROR
        image.state = ImageState.ERROR
        raise e
