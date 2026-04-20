"""
FastAPI routes for web research functionality.
Provides endpoints for researching URLs and retrieving results.
"""

import logging
import asyncio
from uuid import UUID

from fastapi import APIRouter, Query, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.core.security import verify_token, extract_user_id_from_token
from app.models import WebContent, User
from app.services.web_researcher import WebResearcherService
from app.services.web_ingestion_bridge import WebIngestionBridge
from app.schemas import ResearchRequest, ResearchResponse, WebContentResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/research", tags=["Web Research"])


@router.post("/from-url", response_model=ResearchResponse)
async def research_from_url(
    request: ResearchRequest,
    token: str = Query(...),
    db_session: Session = Depends(get_db),
):
    """
    Research a single URL and ingest into knowledge base.
    Returns immediately with research results.
    """
    # Verify authentication
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        user_id = extract_user_id_from_token(payload)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    user = db_session.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        # Research the URL
        result = await WebResearcherService.research_url(
            url=request.url,
            user_id=user_id,
            extract_code=request.extract_code,
            validate_code=request.validate_code,
            custom_selector=request.custom_selector,
            db=db_session,
        )

        if not result["success"]:
            raise HTTPException(
                status_code=400,
                detail=f"Research failed: {result['error']}",
            )

        # Phase 7a: Trigger automatic ingestion (asynchronous)
        if result["web_content_id"]:
            logger.info(f"Triggering Phase 7a ingestion for web_content_id: {result['web_content_id']}")

            async def ingest_in_background():
                """Run ingestion in background without blocking response."""
                from app.database.connection import SessionLocal

                ingest_db = SessionLocal()
                try:
                    source, chunks, embeddings = await WebIngestionBridge.ingest_web_content_by_id(
                        db=ingest_db,
                        web_content_id=result["web_content_id"],
                        extract_entities=True,
                    )

                    if source:
                        logger.info(
                            f"Phase 7a ingestion completed: {len(chunks)} chunks, "
                            f"{len(embeddings)} embeddings for {request.url}"
                        )
                    else:
                        logger.warning(f"Phase 7a ingestion returned no source for {result['web_content_id']}")

                except Exception as e:
                    logger.error(f"Phase 7a ingestion failed: {str(e)}", exc_info=True)
                finally:
                    ingest_db.close()

            # Schedule background task (don't await, let it run independently)
            asyncio.create_task(ingest_in_background())

        return ResearchResponse(
            web_content_id=result["web_content_id"],
            url=result["url"],
            title=result["title"],
            status="complete",
            chunks_created=0,  # Will be updated by background ingestion
            codes_found=result["codes_found"],
            codes_validated=result["codes_validated"],
            knowledge_source_id=None,  # Will be set by background ingestion
            created_at=db_session.query(WebContent).filter(
                WebContent.id == result["web_content_id"]
            ).first().created_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Research submission failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Research failed: {str(e)}")


@router.get("/result/{web_content_id}", response_model=WebContentResponse)
def get_research_result(
    web_content_id: UUID,
    token: str = Query(...),
    db_session: Session = Depends(get_db),
):
    """
    Retrieve results of a completed research operation.
    """
    # Verify authentication
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        user_id = extract_user_id_from_token(payload)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    try:
        web_content = db_session.query(WebContent).filter(
            WebContent.id == web_content_id,
            WebContent.user_id == user_id,
        ).first()

        if not web_content:
            raise HTTPException(status_code=404, detail="Research result not found")

        return WebContentResponse(
            id=web_content.id,
            source_url=web_content.source_url,
            title=web_content.title,
            domain=web_content.domain,
            status="complete",
            codes_validated=web_content.metadata_.get("codes_validated", 0),
            metadata=web_content.metadata_,
            created_at=web_content.created_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve research result: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve result")


@router.get("/history")
def get_research_history(
    token: str = Query(...),
    limit: int = Query(50, ge=1, le=100),
    db_session: Session = Depends(get_db),
):
    """
    Get recent research history for authenticated user.
    """
    # Verify authentication
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        user_id = extract_user_id_from_token(payload)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    try:
        web_contents = db_session.query(WebContent).filter(
            WebContent.user_id == user_id
        ).order_by(WebContent.created_at.desc()).limit(limit).all()

        return [
            {
                "id": wc.id,
                "source_url": wc.source_url,
                "title": wc.title,
                "domain": wc.domain,
                "created_at": wc.created_at,
                "codes_found": wc.metadata_.get("codes_found", 0),
            }
            for wc in web_contents
        ]

    except Exception as e:
        logger.error(f"Failed to get research history: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve history")


@router.post("/validate-url")
def validate_url(
    request: ResearchRequest,
    token: str = Query(...),
):
    """
    Validate a URL before research without fetching it.
    Useful for checking domain whitelist/blacklist.
    """
    # Verify authentication
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        from app.services.web_researcher import WebContentExtractor

        is_valid, error = WebContentExtractor.validate_url(request.url)

        return {
            "url": request.url,
            "is_valid": is_valid,
            "error": error,
        }

    except Exception as e:
        logger.error(f"URL validation failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Validation failed")


@router.websocket("/ws/research")
async def websocket_research_stream(
    websocket: WebSocket,
    token: str = Query(...),
    db_session: Session = Depends(get_db),
):
    """
    WebSocket endpoint for real-time research streaming.
    Client sends URL, receives status updates and findings.
    """
    # Verify authentication
    payload = verify_token(token)
    if not payload:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        user_id = extract_user_id_from_token(payload)
    except ValueError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    logger.info(f"WebSocket research connection established for user {user_id}")

    try:
        # Receive research request from client
        data = await websocket.receive_json()
        url = data.get("url")
        extract_code = data.get("extract_code", True)
        validate_code = data.get("validate_code", True)

        if not url:
            await websocket.send_json({
                "type": "error",
                "content": "No URL provided",
            })
            await websocket.close(code=status.WS_1011_SERVER_ERROR)
            return

        # Send validation status
        await websocket.send_json({
            "type": "status",
            "content": "Validating URL...",
        })

        # Validate URL
        from app.services.web_researcher import WebContentExtractor

        is_valid, error = WebContentExtractor.validate_url(url)
        if not is_valid:
            await websocket.send_json({
                "type": "error",
                "content": f"URL validation failed: {error}",
            })
            await websocket.close(code=status.WS_1011_SERVER_ERROR)
            return

        # Send fetching status
        await websocket.send_json({
            "type": "status",
            "content": "Fetching content...",
        })

        # Research the URL
        result = await WebResearcherService.research_url(
            url=url,
            user_id=user_id,
            extract_code=extract_code,
            validate_code=validate_code,
            db=db_session,
        )

        # Send results
        if result["success"]:
            await websocket.send_json({
                "type": "result",
                "url": result["url"],
                "title": result["title"],
                "domain": result["domain"],
                "content_length": len(result["content"]),
                "codes_found": result["codes_found"],
                "codes_validated": result["codes_validated"],
            })

            # Send codes if found
            if result["codes"]:
                await websocket.send_json({
                    "type": "codes",
                    "codes": result["codes"],
                })

            # Send completion
            await websocket.send_json({
                "type": "complete",
                "status": "success",
                "web_content_id": str(result["web_content_id"]),
            })

            # Phase 7a: Trigger automatic ingestion (asynchronous)
            if result["web_content_id"]:
                logger.info(f"Triggering Phase 7a ingestion for web_content_id: {result['web_content_id']}")

                # Create a new session for the async ingestion task
                from app.database.connection import SessionLocal

                async def ingest_in_background():
                    """Run ingestion in background without blocking response."""
                    ingest_db = SessionLocal()
                    try:
                        source, chunks, embeddings = await WebIngestionBridge.ingest_web_content_by_id(
                            db=ingest_db,
                            web_content_id=result["web_content_id"],
                            extract_entities=True,
                        )

                        if source:
                            logger.info(
                                f"Phase 7a ingestion completed: {len(chunks)} chunks, "
                                f"{len(embeddings)} embeddings for {result['url']}"
                            )
                        else:
                            logger.warning(f"Phase 7a ingestion returned no source for {result['web_content_id']}")

                    except Exception as e:
                        logger.error(f"Phase 7a ingestion failed: {str(e)}", exc_info=True)
                    finally:
                        ingest_db.close()

                # Schedule background task (don't await, let it run independently)
                asyncio.create_task(ingest_in_background())
        else:
            await websocket.send_json({
                "type": "error",
                "content": result["error"],
            })

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for user {user_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}", exc_info=True)
        try:
            await websocket.send_json({
                "type": "error",
                "content": f"Server error: {str(e)}",
            })
        except Exception:
            pass
        finally:
            await websocket.close(code=status.WS_1011_SERVER_ERROR)
