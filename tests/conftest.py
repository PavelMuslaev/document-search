from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient

from app.db import get_session
from app.main import app


class FakeSession:
    def __init__(self):
        self.documents = [
            SimpleNamespace(
                id=number,
                text=f"Python post {number}",
                rubrics=["VK-example"],
                created_date=datetime(2019, 1, 1) + timedelta(days=number),
            )
            for number in range(1, 26)
        ]
        self.committed = False
        self.query_sql = ""

    async def execute(self, statement):
        self.query_sql = str(statement)
        ids = next(
            value
            for value in statement.compile().params.values()
            if isinstance(value, list)
        )
        documents = [document for document in self.documents if document.id in ids]
        documents.sort(
            key=lambda document: (document.created_date, document.id), reverse=True
        )
        return SimpleNamespace(
            scalars=lambda: SimpleNamespace(all=lambda: documents[:20])
        )

    async def get(self, model, document_id):
        return next((doc for doc in self.documents if doc.id == document_id), None)

    async def delete(self, document):
        self.documents.remove(document)

    async def commit(self):
        self.committed = True


class FakeElastic:
    def __init__(self):
        self.deleted = []

    async def delete(self, **kwargs):
        self.deleted.append(kwargs)


@pytest.fixture
async def client(monkeypatch):
    session = FakeSession()
    elastic = FakeElastic()
    app.state.elastic = elastic
    app.state.elasticsearch_index = "documents"
    hits = list(range(1, 26))

    async def fake_scan(*args, **kwargs):
        for document_id in hits:
            yield {"_id": str(document_id)}

    monkeypatch.setattr("app.service.async_scan", fake_scan)

    async def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as api:
        yield api, session, elastic, hits
    app.dependency_overrides.clear()
