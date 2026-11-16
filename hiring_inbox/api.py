"""Local FastAPI entry point for inbox imports, processing, and review."""

import os
import re
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path as FilePath
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, Path, Request, Response
from fastapi.concurrency import run_in_threadpool
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import sessionmaker

from hiring_inbox.classifier import Intent
from hiring_inbox.csv_io import MAX_CSV_BYTES, parse_import
from hiring_inbox.database import open_database
from hiring_inbox.provider import GroqProvider, StructuredProvider
from hiring_inbox.review_service import ReviewService, ServiceError, recover_interrupted_work


_ROOT = FilePath(__file__).resolve().parents[1]
_ID = Annotated[int, Path(gt=0, lt=2**63)]
_DRAFT_STATUS = Literal["pending_review", "approved", "rejected"]
_LOOPBACK_ORIGIN = re.compile(r"http://(?:localhost|127\.0\.0\.1|\[::1\]):([1-9][0-9]{0,4})")


class ReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)

    revision: int = Field(gt=0, lt=2**63)
    reason: str | None = Field(default=None, min_length=1, max_length=500)


class EditRequest(ReviewRequest):
    reply: str = Field(min_length=1, max_length=1200)


class ImportReceipt(BaseModel):
    batch_id: int
    message_count: int
    duplicate: bool


class BatchSummary(BaseModel):
    batch_id: int
    created_at: str
    message_count: int


class BatchList(BaseModel):
    batches: list[BatchSummary]


class BatchStatus(BaseModel):
    batch_id: int
    status: Literal["imported", "processing", "interrupted", "completed", "completed_with_errors"]
    created_at: str
    message_count: int
    processed: int
    processing_failures: int
    classified: int
    pending_review: int
    approved: int
    rejected: int
    manual_writing: int
    regenerating: int


class DraftSummary(BaseModel):
    id: int
    status: _DRAFT_STATUS
    revision: int
    approved_revision: int | None
    regenerating: bool
    requires_manual_writing: bool


class ReviewEventView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    action: Literal["edit", "approve", "reject", "regenerate"]
    from_revision: int
    to_revision: int
    from_status: _DRAFT_STATUS
    to_status: _DRAFT_STATUS
    reply_before: str | None
    reply_after: str | None
    safety_flags_before: list[str]
    generation_failure_before: str | None
    reason: str | None
    created_at: str


class DraftView(DraftSummary):
    message_id: int
    generated_reply: str | None
    edited_reply: str | None
    reply: str | None
    review_reason: str
    generation_failure: str | None
    generation_safety_flags: list[str]
    safety_flags: list[str]
    review_events: list[ReviewEventView]


class ClassificationView(BaseModel):
    primary_intent: Intent
    secondary_intents: list[Intent]
    short_summary: str
    needs_review: bool
    review_reason: str


class MessageView(BaseModel):
    id: int
    source_id: str
    candidate_name: str
    message_text: str
    classification: ClassificationView | None
    classification_failure: str | None
    candidate_instruction_detected: bool
    draft: DraftSummary | None


class IntentGroup(BaseModel):
    intent: Intent | Literal["unclassified"]
    messages: list[MessageView]


class BatchGroups(BaseModel):
    batch_id: int
    groups: list[IntentGroup]


def _service(request: Request) -> ReviewService:
    return request.app.state.review_service


_Service = Annotated[ReviewService, Depends(_service)]


def create_app(database_path: FilePath | None = None, provider: StructuredProvider | None = None) -> FastAPI:
    @contextmanager
    def processing_provider() -> Iterator[StructuredProvider]:
        if provider is not None:
            yield provider
            return
        try:
            groq = GroqProvider.from_environment(_ROOT / ".env", request_interval=8)
        except ValueError:
            raise ServiceError(503, "Groq configuration is invalid.") from None
        if groq is None:
            raise ServiceError(503, "Groq credentials are unavailable.")
        with groq.client:
            yield groq

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        path = database_path or FilePath(os.environ.get("INBOX_DB_PATH", _ROOT / "var" / "inbox.sqlite3"))
        engine = open_database(path)
        try:
            sessions = sessionmaker(engine, expire_on_commit=False)
            recover_interrupted_work(sessions)
            application.state.review_service = ReviewService(sessions, processing_provider)
            yield
        finally:
            engine.dispose()

    app = FastAPI(title="MUST Hiring Inbox", version="0.4.0", lifespan=lifespan)
    web_origin = os.environ.get("INBOX_WEB_ORIGIN")
    if web_origin:
        origin_match = _LOOPBACK_ORIGIN.fullmatch(web_origin)
        if origin_match is None or int(origin_match[1]) > 65535:
            raise ValueError("INBOX_WEB_ORIGIN must be an exact HTTP loopback origin with a port.")
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[web_origin],
            allow_methods=["GET", "POST", "PATCH"],
            allow_headers=["Content-Type"],
            expose_headers=["Content-Disposition"],
        )

    @app.exception_handler(ServiceError)
    async def handle_service_error(_request: Request, error: ServiceError) -> JSONResponse:
        return JSONResponse({"detail": error.detail}, status_code=error.status)

    @app.exception_handler(RequestValidationError)
    async def handle_request_error(_request: Request, error: RequestValidationError) -> JSONResponse:
        return JSONResponse({"detail": [{"loc": item["loc"], "type": item["type"]}
                                        for item in error.errors()]}, status_code=422)

    @app.post(
        "/batches", response_model=ImportReceipt, status_code=201,
        responses={200: {"model": ImportReceipt, "description": "Identical batch already imported"}},
        openapi_extra={"requestBody": {"required": True, "content": {"text/csv": {"schema": {"type": "string"}}}}},
    )
    async def import_batch(request: Request, response: Response, service: _Service) -> dict:
        media_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        if media_type != "text/csv":
            raise ServiceError(415, "Send a UTF-8 CSV body with Content-Type text/csv.")
        body = bytearray()
        async for block in request.stream():
            if len(body) + len(block) > MAX_CSV_BYTES:
                raise ServiceError(413, "CSV exceeds the 1 MiB upload limit.")
            body.extend(block)
        try:
            messages = parse_import(bytes(body))
        except ValueError as error:
            raise ServiceError(422, str(error)) from None
        result = await run_in_threadpool(service.import_batch, messages)
        if result["duplicate"]:
            response.status_code = 200
        return result

    @app.get("/batches", response_model=BatchList)
    def batches(service: _Service) -> dict:
        return {"batches": service.list_batches()}

    @app.post("/batches/{batch_id}/process", response_model=BatchStatus)
    def process_batch(batch_id: _ID, service: _Service) -> dict:
        return service.process_batch(batch_id)

    @app.get("/batches/{batch_id}/status", response_model=BatchStatus)
    def batch_status(batch_id: _ID, service: _Service) -> dict:
        return service.status(batch_id)

    @app.get("/batches/{batch_id}/groups", response_model=BatchGroups)
    def groups(batch_id: _ID, service: _Service) -> dict:
        return service.groups(batch_id)

    @app.get("/drafts/{draft_id}", response_model=DraftView)
    def draft_detail(draft_id: _ID, service: _Service) -> dict:
        return service.get_draft(draft_id)

    @app.patch("/drafts/{draft_id}", response_model=DraftView)
    def edit(draft_id: _ID, body: EditRequest, service: _Service) -> dict:
        return service.review(draft_id, body.revision, "edit", body.reason, body.reply)

    @app.post("/drafts/{draft_id}/approve", response_model=DraftView)
    def approve(draft_id: _ID, body: ReviewRequest, service: _Service) -> dict:
        return service.review(draft_id, body.revision, "approve", body.reason)

    @app.post("/drafts/{draft_id}/reject", response_model=DraftView)
    def reject(draft_id: _ID, body: ReviewRequest, service: _Service) -> dict:
        return service.review(draft_id, body.revision, "reject", body.reason)

    @app.post("/drafts/{draft_id}/regenerate", response_model=DraftView)
    def regenerate(draft_id: _ID, body: ReviewRequest, service: _Service) -> dict:
        return service.regenerate(draft_id, body.revision, body.reason)

    @app.get("/batches/{batch_id}/export", response_class=Response,
             responses={200: {"content": {"text/csv": {"schema": {"type": "string"}}}}})
    def export(batch_id: _ID, service: _Service) -> Response:
        return Response(service.export(batch_id), media_type="text/csv", headers={
            "Content-Disposition": f'attachment; filename="batch-{batch_id}-approved.csv"',
            "Cache-Control": "no-store",
        })

    return app


app = create_app()
