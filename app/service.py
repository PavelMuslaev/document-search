from elasticsearch import AsyncElasticsearch, NotFoundError
from elasticsearch.helpers import async_scan
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Document


async def search_documents(
    query: str, session: AsyncSession, elastic: AsyncElasticsearch, index: str
) -> list[Document]:
    # Date is only in PostgreSQL: collect every matching id before sorting.
    ids = [
        int(hit["_id"])
        async for hit in async_scan(
            elastic,
            index=index,
            query={"query": {"match": {"text": query}}, "_source": False},
            size=500,
        )
    ]
    if not ids:
        return []

    statement = (
        select(Document)
        .where(Document.id.in_(ids))
        .order_by(Document.created_date.desc(), Document.id.desc())
        .limit(20)
    )
    result = await session.execute(statement)
    return list(result.scalars().all())


async def delete_document(
    document_id: int, session: AsyncSession, elastic: AsyncElasticsearch, index: str
) -> bool:
    document = await session.get(Document, document_id)
    if document is None:
        return False

    await session.delete(document)
    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise

    try:
        await elastic.delete(index=index, id=str(document_id), refresh="wait_for")
    except NotFoundError:
        pass
    return True
