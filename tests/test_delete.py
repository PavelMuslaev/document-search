import pytest


@pytest.mark.asyncio
async def test_delete_existing_document(client):
    api, session, elastic, _ = client
    response = await api.delete("/documents/1")

    assert response.status_code == 204
    assert response.content == b""
    assert session.committed
    assert await session.get(None, 1) is None
    assert elastic.deleted[0]["id"] == "1"


@pytest.mark.asyncio
async def test_delete_unknown_document(client):
    api, session, elastic, _ = client
    response = await api.delete("/documents/999")

    assert response.status_code == 404
    assert not session.committed
    assert elastic.deleted == []
