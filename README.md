# ДОКУМЕНТАЦИЮ И КОНТЕЙНИРИЗАЦИЮ РЕАЛИЗОВАЛ С ПОМОЩЬЮ ChatGPT (ВСЁ ОСТАЛЬНОЕ РУЧКАМИ :))

# Document Search

Небольшой сервис поиска по CSV-публикациям. PostgreSQL хранит полный документ,
Elasticsearch индексирует только `id` и `text`. API отдаёт полные данные и
удаляет документ по ID.

## Стек и файлы

Python 3.13, FastAPI, SQLAlchemy Async + asyncpg, PostgreSQL, Elasticsearch 8,
Alembic, uv, Docker Compose, pytest, Ruff.

```text
app/                       API, настройки, модель, поиск и удаление
scripts/import_documents.py  импорт CSV партиями по 500 строк
alembic/                   начальная миграция documents
tests/                     7 тестов основных HTTP-сценариев
data/posts.csv             исходный CSV (1500 документов)
docs.json                  экспорт FastAPI OpenAPI
PROJECT_GUIDE.pdf          руководство по проекту
```

## Быстрый запуск

Нужны Docker и Docker Compose. Из корня проекта:

```bash
cp .env.example .env
docker compose up --build -d
docker compose exec api python -m scripts.import_documents data/posts.csv
curl 'http://localhost:8000/documents/search?q=конкурс'
curl -i -X DELETE 'http://localhost:8000/documents/1'
```

API при запуске самостоятельно вызывает `alembic upgrade head`, поэтому
отдельная команда для первой миграции не требуется. Чтобы применить миграцию
вручную: `docker compose exec api alembic upgrade head`. Swagger доступен по
адресу <http://localhost:8000/docs>, OpenAPI — по `/openapi.json`.

Для чистого повторного импорта удалите данные вместе с томами командой
`docker compose down -v`, затем поднимите проект снова. Повторный импорт в
неочищенную базу добавляет новые записи: CSV не содержит стабильного ID.

## Локальный запуск

Установите Python 3.13 и uv. Поднимите контейнеры с базами:

```bash
docker compose up -d postgres elasticsearch
cp .env.example .env
uv sync --frozen
uv run alembic upgrade head
uv run python -m scripts.import_documents data/posts.csv
uv run uvicorn app.main:app --reload
```

Параметры подключения в `.env`: `POSTGRES_DSN`, `ELASTICSEARCH_URL`,
`ELASTICSEARCH_INDEX`. В Docker Compose они задаются для API через переменные
окружения: имена хостов `postgres` и `elasticsearch`, в отличие от локального
`localhost`.

## API

`GET /documents/search?q=текст`: Elasticsearch находит совпадения `match` по
полю `text`; сервис получает все совпавшие ID; PostgreSQL возвращает максимум
20 документов, сортируя по `created_date DESC, id DESC`. При пустой выдаче
возвращается `[]`. Пустой `q` даёт 422. Ответ содержит `id`, `rubrics`, `text`,
`created_date`. Даты CSV не содержат часового пояса и сохраняются как есть.

`DELETE /documents/{document_id}`: после коммита удаления из PostgreSQL запись
удаляется из Elasticsearch с `refresh=wait_for`. Успех — 204, неизвестный ID —
404. При ошибке Elasticsearch API возвращает 503; данные PostgreSQL уже могут
быть удалены. Оставшаяся запись индекса не попадёт в результаты поиска,
поскольку полные документы выбираются из PostgreSQL. Сервис не содержит
автоматического восстановления индекса.

## Сортировка и ограничения

По исходному условию `created_date` отсутствует в Elasticsearch. Сортировать
лишь первые 20 найденных им документов неверно: так можно потерять более
свежие совпадения. Здесь `async_scan` выгружает **все** совпавшие ID, затем
PostgreSQL выполняет `ORDER BY ... LIMIT 20`. Для 1500 документов это просто
и даёт точный результат, но при большом числе совпадений список ID потребляет
память приложения, а `IN (...)` и scroll создают нагрузку. Индекс может слегка
отставать от базы, импорт партиями не атомарен между системами; повторный
импорт создаёт дубли. Анализатор Elasticsearch — стандартный, без специальной
морфологии русского языка.

Практичнее для крупного production-индекса добавить `created_date` в документ
Elasticsearch и выполнять `match + sort(created_date DESC) + size 20` там;
после этого PostgreSQL выбирает полные строки по полученным ID, а сервис
сохраняет их порядок. Это изменение исходной структуры индекса, поэтому в
тестовом проекте оно не сделано.

## Проверки

```bash
uv run pytest
uv run pytest --cov=app --cov=scripts --cov-report=term-missing
uv run ruff check .
uv run ruff format --check .
uv run python -c 'from app.main import app; import json; open("docs.json", "w", encoding="utf-8").write(json.dumps(app.openapi(), ensure_ascii=False, indent=2))'
```

Семь тестов проверяют основные HTTP-сценарии и запрос сортировки. Используются
подставные зависимости PostgreSQL и Elasticsearch: тесты **не являются**
интеграционной проверкой реальных контейнеров. При измерении вместе с
импортёром покрытие составило 55%.
