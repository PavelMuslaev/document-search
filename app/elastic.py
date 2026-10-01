from elasticsearch import AsyncElasticsearch


async def ensure_index(client: AsyncElasticsearch, index: str) -> None:
    if await client.indices.exists(index=index):
        return

    await client.indices.create(
        index=index,
        mappings={
            "properties": {
                "id": {"type": "long"},
                "text": {"type": "text"},
            }
        },
    )
