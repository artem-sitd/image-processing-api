FROM python:3.12.3

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED = 1

WORKDIR /app

RUN curl -sSL https://install.python-poetry.org | python3 -

ENV PATH="/root/.local/bin:$PATH"

COPY pyproject.toml poetry.lock ./

RUN poetry install --only main

ENV USE_DOCKER=1

COPY . .

CMD ["sh", "-c", "sleep 10 && poetry run alembic upgrade head && poetry run python main.py"]
