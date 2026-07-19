"""Query APIs — dense search (3.3) + grounded answer (3.4)."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import AuthContext, require_content_auth
from app.core.config import Settings, get_settings
from app.models.query import (
    AnswerCitation,
    AnswerResponseBody,
    AnswerRetrievalMeta,
    SearchHit,
    SearchRequest,
    SearchResponseBody,
)
from app.services.answer_graph import run_grounded_answer
from app.services.search import (
    SearchServiceError,
    SearchValidationError,
    dense_search,
)

logger = logging.getLogger("erp.api.query")

router = APIRouter(prefix="/query", tags=["query"])


@router.post(
    "/search",
    response_model=SearchResponseBody,
    summary="Dense search over published (active) chunks",
    responses={
        400: {"description": "Invalid query / top_k"},
        401: {"description": "Unauthorized"},
        503: {"description": "Vector Search or embedding unavailable"},
    },
)
async def search_chunks(
    body: SearchRequest,
    auth: Annotated[AuthContext, Depends(require_content_auth)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> SearchResponseBody:
    """
    Embed the query and retrieve top-k neighbors from Vertex Vector Search.

    Always filters ``active=true`` (published-only). Optional ``collection`` filter.
    """
    try:
        result = dense_search(
            settings=settings,
            query=body.query,
            top_k=body.top_k,
            collection=body.collection,
        )
    except SearchValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message
        ) from exc
    except SearchServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=exc.message
        ) from exc

    logger.info(
        "search_ok auth_mode=%s results=%s top_k=%s",
        auth.auth_mode,
        len(result.results),
        result.top_k,
    )
    return SearchResponseBody(
        query=result.query,
        top_k=result.top_k,
        results=[
            SearchHit(
                text=r.text,
                score=r.score,
                document_id=r.document_id,
                version_id=r.version_id,
                chunk_index=r.chunk_index,
                title=r.title,
                filename=r.filename,
                collection=r.collection,
                datapoint_id=r.datapoint_id,
                char_count=r.char_count,
            )
            for r in result.results
        ],
    )


@router.post(
    "/answer",
    response_model=AnswerResponseBody,
    summary="Grounded answer (retrieve → evidence check → Gemini)",
    responses={
        400: {"description": "Invalid query / top_k"},
        401: {"description": "Unauthorized"},
        503: {"description": "Retrieval or generation unavailable"},
    },
)
async def answer_query(
    body: SearchRequest,
    auth: Annotated[AuthContext, Depends(require_content_auth)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AnswerResponseBody:
    """
    LangGraph pipeline: dense retrieve (active-only) → evidence check → generate.

    Refuses when no usable published evidence. Citations come from retrieval hits.
    """
    try:
        result = run_grounded_answer(
            settings=settings,
            query=body.query,
            top_k=body.top_k,
            collection=body.collection,
        )
    except SearchValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message
        ) from exc
    except SearchServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=exc.message
        ) from exc

    logger.info(
        "answer_ok auth_mode=%s refused=%s citations=%s",
        auth.auth_mode,
        result.refused,
        len(result.citations),
    )
    return AnswerResponseBody(
        query=result.query,
        answer=result.answer,
        refused=result.refused,
        refusal_reason=result.refusal_reason,
        citations=[
            AnswerCitation(
                document_id=c.document_id,
                version_id=c.version_id,
                chunk_index=c.chunk_index,
                title=c.title,
                filename=c.filename,
                snippet=c.snippet,
                score=c.score,
            )
            for c in result.citations
        ],
        retrieval=AnswerRetrievalMeta(
            top_k=result.top_k,
            hit_count=result.hit_count,
        ),
    )
