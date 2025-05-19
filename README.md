# 🖼️ Image Processing API

REST API для загрузки изображений, их масштабирования до различных размеров и хранения в S3-совместимом хранилище MinIO. Построен с использованием FastAPI, PostgreSQL и Alembic, с управлением зависимостями через Poetry.

---

## 🚀 Возможности

- 📤 Загрузка изображений через API
- 🔄 Масштабирование изображений до различных размеров
- ☁️ Хранение изображений в MinIO (S3-совместимое хранилище)
- 🗃️ Хранение метаданных в PostgreSQL
- 🐳 Развёртывание с использованием Docker Compose
- 🧪 Миграции базы данных с использованием Alembic

---

## 🧰 Технологии

- Python 3.10+
- FastAPI
- PostgreSQL
- MinIO (S3)
- Alembic
- Poetry
- Docker & Docker Compose

---

## ⚙️ Установка и запуск

1. **Клонируйте репозиторий:**

   ```bash
   git clone https://github.com/artem-sitd/image-processing-api.git
   cd image-processing-api
   ```

2. **Настройте переменные окружения:**

   Переименуйте файл `.env.docker.template` в `.env.docker`:

   ```bash
   cp .env.docker.template .env.docker
   ```

   Отредактируйте файл `.env.docker`, указав необходимые значения:

   - `POSTGRES_USER` — имя пользователя PostgreSQL
   - `POSTGRES_PASSWORD` — пароль пользователя PostgreSQL
   - `POSTGRES_DB` — имя базы данных
   - `MINIO_ROOT_USER` — имя пользователя MinIO
   - `MINIO_ROOT_PASSWORD` — пароль пользователя MinIO

3. **Запустите приложение с помощью Docker Compose:**

   ```bash
   docker-compose up --build
   ```

   Приложение будет доступно по адресу `http://localhost:8000`.

---

## 📁 Структура проекта

```
├── alembic/               # Миграции базы данных
├── app/                   # Основная логика приложения
├── .env.docker.template   # Шаблон переменных окружения
├── docker-compose.yaml    # Конфигурация Docker Compose
├── main.py                # Точка входа в приложение
├── pyproject.toml         # Зависимости Poetry
├── settings.py            # Настройки приложения
└── README.md              # Документация проекта
```

---

## 📄 Лицензия

Проект распространяется под лицензией MIT. Подробнее см. файл `LICENSE`.
