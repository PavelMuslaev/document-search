import argparse
import ast
import asyncio
import csv
from datetime import datetime
from pathlib import Path

from elasticsearch import AsyncElasticsearch
from elasticsearch.helpers import async_bulk

from app.config import get_settings
from app.db import engine, session_maker
from app.elastic import ensure_index
from app.models import Document


def read_batches(path: Path, batch_size: int = 500):
    with path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if not reader.fieldnames or not {"text", "created_date", "rubrics"}.issubset(
            reader.fieldnames
        ):
            raise ValueError("CSV must contain text, created_date and rubrics")

        batch = []
        for row in reader:
            rubrics = ast.literal_eval(row["rubrics"])
            if not isinstance(rubrics, list) or not all(
                isinstance(rubric, str) for rubric in rubrics
            ):
                raise ValueError("rubrics must be a list of strings")
            batch.append(
                Document(
                    text=row["text"],
                    created_date=datetime.fromisoformat(row["created_date"]),
                    rubrics=rubrics,
                )
            )
            if len(batch) >= batch_size:
                yield batch
                batch = []
        if batch:
            yield batch


async def import_documents(path: Path) -> None:
    settings = get_settings()
    elastic = AsyncElasticsearch(settings.elasticsearch_url)
    total = 0
    try:
        await ensure_index(elastic, settings.elasticsearch_index)
        for batch in read_batches(path):
            async with session_maker() as session:
                session.add_all(batch)
                try:
                    await session.flush()
                    await session.commit()
                except Exception:
                    await session.rollback()
                    raise

            actions = (
                {
                    "_index": settings.elasticsearch_index,
                    "_id": str(document.id),
                    "_source": {"id": document.id, "text": document.text},
                }
                for document in batch
            )
            await async_bulk(elastic.options(refresh="wait_for"), actions)
            total += len(batch)
            print(f"Imported {total} documents")
    finally:
        await elastic.close()
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import CSV documents")
    parser.add_argument("path", type=Path)
    arguments = parser.parse_args()
    asyncio.run(import_documents(arguments.path))
