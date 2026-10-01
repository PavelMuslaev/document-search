from typing import Annotated

from elasticsearch import ApiError, AsyncElasticsearch, TransportError
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.schemas import DocumentResponse
from app.service import delete_document, search_documents

router = APIRouter(prefix="/documents", tags=["documents"])


def get_elastic(request: Request) -> AsyncElasticsearch:
    return request.app.state.elastic


@router.get("/search", response_model=list[DocumentResponse])
async def search(
    request: Request,
    q: Annotated[str, Query(min_length=1)],
    session: Annotated[AsyncSession, Depends(get_session)],
    elastic: Annotated[AsyncElasticsearch, Depends(get_elastic)],
) -> list[DocumentResponse]:
    try:
        documents = await search_documents(
            q, session, elastic, request.app.state.elasticsearch_index
        )
    except (ApiError, TransportError) as exc:
        raise HTTPException(status_code=503, detail="Search unavailable") from exc
    return [DocumentResponse.model_validate(document) for document in documents]


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(
    document_id: int,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    elastic: Annotated[AsyncElasticsearch, Depends(get_elastic)],
) -> None:
    try:
        deleted = await delete_document(
            document_id, session, elastic, request.app.state.elasticsearch_index
        )
    except (ApiError, TransportError) as exc:
        raise HTTPException(status_code=503, detail="Search index unavailable") from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")
