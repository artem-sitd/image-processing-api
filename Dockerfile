FROM python:3.12

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED = 1

WORKDIR /memes_app

COPY requirements.txt requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

ENV USE_DOCKER=1

COPY . .

CMD ["sh", "-c", "sleep 10 && alembic upgrade head && python3 main.py"]
