import pytest


@pytest.mark.asyncio
async def test_search_responds_with_documents(client):
    api, _, _, _ = client
    response = await api.get("/documents/search", params={"q": "python"})

    assert response.status_code == 200
    assert set(response.json()[0]) == {"id", "text", "rubrics", "created_date"}


@pytest.mark.asyncio
async def test_search_returns_at_most_twenty(client):
    api, _, _, _ = client
    response = await api.get("/documents/search", params={"q": "python"})

    assert len(response.json()) == 20


@pytest.mark.asyncio
async def test_search_orders_by_date(client):
    api, session, _, _ = client
    response = await api.get("/documents/search", params={"q": "python"})

    assert [document["id"] for document in response.json()] == list(range(25, 5, -1))
    assert "ORDER BY documents.created_date DESC" in session.query_sql
    assert "LIMIT" in session.query_sql


@pytest.mark.asyncio
async def test_search_without_matches_returns_empty_list(client):
    api, _, _, hits = client
    hits.clear()
    response = await api.get("/documents/search", params={"q": "not-found"})

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_empty_query_is_rejected(client):
    api, _, _, _ = client
    response = await api.get("/documents/search", params={"q": ""})

    assert response.status_code == 422
