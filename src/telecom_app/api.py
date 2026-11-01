"""Same-origin identity API and React shell; no model or Engine calls at startup."""

import json
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from pymongo import MongoClient
from starlette.concurrency import run_in_threadpool

from compatibility.demo_auth.auth import AccessDenied, UserExists
from compatibility.demo_auth.sessions import (
    SESSION_SECONDS,
    PasswordRejected,
    ProfileConflict,
    RateLimited,
)

from .avatar import AvatarRevision, AvatarUpload, normalize_avatar
from .config import Settings
from .contracts import LoginRequest, PrincipalView, RegistrationRequest
from .curation import CurationService, Upload
from .curation_runtime import configure as configure_curation
from .database import connect, user_store, verify_connection
from .identity import IdentityService, identity_service, public_principal
from .ingestion import IngestionConflict
from .journey import (
    ChatInput,
    ConversationInput,
    EngineAPI,
    EngineUnavailable,
    ExecutionInput,
    JourneyConflict,
    JourneyService,
    ReviewInput,
)
from .knowledge_publication import PublicationConflict
from .profile import PasswordInput, ProfileInput, ProfileView
from .security import Boundary
from .voice import AudioInput, VoiceService

COOKIE = "telecom_session"


def create_app(
    settings: Settings,
    identity: IdentityService | None = None,
    journey: JourneyService | None = None,
    voice: VoiceService | None = None,
    curation: CurationService | None = None,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        client = None
        knowledge_clients: list[MongoClient[dict[str, Any]]] = []
        try:
            if identity is None:
                client = connect(settings)
                await run_in_threadpool(verify_connection, client)
                app.state.identity = identity_service(user_store(client))
            else:
                app.state.identity = identity
            app.state.journey = journey or (
                JourneyService(app.state.identity, EngineAPI(),
                               localized_turns=settings.journey_locale_enabled)
                if settings.journey_enabled
                else None
            )
            app.state.voice = voice or (
                VoiceService() if os.environ.get("OPENAI_API_KEY") else None
            )
            app.state.curation = curation
            if curation is None and os.environ.get("APP_KNOWLEDGE_ENABLED", "false") == "true":
                app.state.curation, knowledge_clients = configure_curation(app.state.identity)
            yield
        except Exception:
            raise RuntimeError("Identity service unavailable; details suppressed") from None
        finally:
            if client is not None:
                client.close()
            for knowledge_client in knowledge_clients:
                knowledge_client.close()

    app = FastAPI(
        title="Telecom demo foundation",
        version="1.0.0",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.add_middleware(Boundary, origin=settings.origin)

    def service() -> IdentityService:
        result: IdentityService = app.state.identity
        return result

    def token(request: Request) -> str:
        return request.cookies.get(COOKIE, "")

    @app.exception_handler(AccessDenied)
    async def denied(request: Request, error: AccessDenied) -> JSONResponse:
        forbidden = str(error) in (
            "Administrator required",
            "Execution belongs to another scope",
            "Document owner required",
            "Document access denied",
        )
        return JSONResponse(
            {"error": str(error) if forbidden else "Login required"},
            status_code=403 if forbidden else 401,
        )

    @app.exception_handler(JourneyConflict)
    @app.exception_handler(PublicationConflict)
    @app.exception_handler(IngestionConflict)
    async def conflict(request: Request, error: JourneyConflict) -> JSONResponse:
        return JSONResponse(
            {"error": "Execution changed; refresh its status before retrying"}, status_code=409
        )

    @app.exception_handler(EngineUnavailable)
    async def unavailable(request: Request, error: EngineUnavailable) -> JSONResponse:
        return JSONResponse(
            {"error": "Engine unavailable; check execution status before retrying"}, status_code=503
        )

    @app.exception_handler(UserExists)
    async def duplicate(request: Request, error: UserExists) -> JSONResponse:
        return JSONResponse({"error": "Email already registered"}, status_code=409)

    @app.exception_handler(RateLimited)
    async def limited(request: Request, error: RateLimited) -> JSONResponse:
        if request.url.path == "/api/profile/password":
            return JSONResponse({"error": "Too many password attempts; try later"},
                                status_code=429, headers={"Retry-After": "900"})
        return JSONResponse(
            {"error": "Too many login attempts; try again next minute"},
            status_code=429,
            headers={"Retry-After": "60"},
        )

    @app.exception_handler(RequestValidationError)
    @app.exception_handler(ValueError)
    async def invalid(request: Request, error: Exception) -> JSONResponse:
        # FastAPI's default validation response may echo input (including passwords).
        return JSONResponse({"error": "Invalid request"}, status_code=400)

    @app.get("/healthz")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "telecom-api", "contract_version": "1"}

    @app.exception_handler(ProfileConflict)
    async def profile_conflict(request: Request, error: ProfileConflict) -> JSONResponse:
        return JSONResponse({"error": "Profile changed; reload before saving"}, status_code=409)

    @app.exception_handler(PasswordRejected)
    async def password_rejected(request: Request, error: PasswordRejected) -> JSONResponse:
        return JSONResponse({"error": "Check current password"}, status_code=400)

    @app.post("/api/profile/password")
    def change_password(
        request: Request, response: Response, body: PasswordInput,
    ) -> dict[str, str]:
        service().change_password(
            token(request), current_password=body.current_password.get_secret_value(),
            new_password=body.new_password.get_secret_value(),
        )
        response.delete_cookie(COOKIE, path="/", httponly=True, samesite="strict")
        return {"status": "password_changed", "reauthenticate": "required"}

    @app.get("/api/profile/avatar")
    def avatar(request: Request) -> Response:
        content = service().avatar(token(request))
        return Response(
            content=content, media_type="image/jpeg", status_code=200 if content else 404,
        )

    @app.post("/api/profile/avatar", response_model=ProfileView)
    def save_avatar(request: Request, body: AvatarUpload) -> ProfileView:
        service().principal(token(request))
        content = normalize_avatar(body)
        return ProfileView.model_validate(service().save_avatar(
            token(request), content=content, expected_revision=body.expected_revision,
        ))

    @app.post("/api/profile/avatar/remove", response_model=ProfileView)
    def remove_avatar(request: Request, body: AvatarRevision) -> ProfileView:
        return ProfileView.model_validate(service().save_avatar(
            token(request), content=None, expected_revision=body.expected_revision,
        ))

    @app.get("/api/profile", response_model=ProfileView)
    def profile(request: Request) -> ProfileView:
        return ProfileView.model_validate(service().profile(token(request)))

    @app.post("/api/profile", response_model=ProfileView)
    def save_profile(request: Request, body: ProfileInput) -> ProfileView:
        return ProfileView.model_validate(service().save_profile(
            token(request), values=body.model_dump(exclude={"expected_revision"}),
            expected_revision=body.expected_revision,
        ))

    @app.get("/api/me", response_model=PrincipalView)
    def me(request: Request) -> PrincipalView:
        return public_principal(service().principal(token(request)))

    @app.post("/api/login", response_model=PrincipalView)
    def login(data: LoginRequest, request: Request, response: Response) -> PrincipalView:
        peer = request.client.host if request.client else "unknown"
        new_token, principal = service().login(data.email, data.password.get_secret_value(), peer)
        if token(request):
            try:
                service().logout(token(request))
            except AccessDenied:
                pass
        # HTTP cookie is permitted only for this strictly loopback-only demo.
        response.set_cookie(
            COOKIE, new_token, max_age=SESSION_SECONDS, httponly=True, samesite="strict", path="/"
        )
        return public_principal(principal)

    @app.post("/api/logout")
    def logout(request: Request, response: Response) -> dict[str, str]:
        service().logout(token(request))
        response.delete_cookie(COOKIE, path="/", httponly=True, samesite="strict")
        return {"status": "logged_out"}

    @app.post("/api/users", response_model=PrincipalView, status_code=201)
    def register(data: RegistrationRequest, request: Request) -> PrincipalView:
        return public_principal(
            service().register(
                token(request),
                email=data.email,
                password=data.password.get_secret_value(),
                role=data.role.value,
            )
        )

    def journey_service(request: Request) -> JourneyService:
        service().principal(token(request))
        result: JourneyService | None = app.state.journey
        if result is None:
            raise EngineUnavailable("Journey is not configured")
        return result

    @app.get("/api/capabilities")
    def capabilities(request: Request) -> dict[str, bool]:
        service().principal(token(request))
        enabled = app.state.journey is not None
        return {
            "journey": enabled,
            "voice": enabled and app.state.voice is not None,
            "knowledge": app.state.curation is not None,
        }

    def knowledge(request: Request) -> CurationService:
        service().principal(token(request))
        current: CurationService | None = app.state.curation
        if current is None:
            raise EngineUnavailable("Knowledge is not configured")
        return current

    @app.post("/api/knowledge/upload")
    def upload_pdf(data: Upload, request: Request) -> dict[str, str]:
        return knowledge(request).upload(token(request), data)

    @app.post("/api/knowledge/process-next")
    def process_pdf(request: Request) -> dict[str, str]:
        return knowledge(request).process_next(token(request))

    @app.get("/api/knowledge/documents")
    def published_documents(request: Request) -> list[dict[str, str]]:
        return knowledge(request).documents(token(request))

    @app.get("/api/knowledge/source/{version_key}")
    def source_pdf(version_key: str, request: Request) -> Response:
        return Response(
            knowledge(request).source(token(request), version_key),
            media_type="application/pdf",
            headers={"Content-Disposition": 'attachment; filename="procedure.pdf"'},
        )

    @app.get("/api/knowledge/preview/{job_id}")
    def preview_pdf(job_id: str, request: Request) -> Response:
        return Response(
            knowledge(request).preview(token(request), job_id),
            media_type="application/pdf",
            headers={"Content-Disposition": 'attachment; filename="source.pdf"'},
        )

    @app.get("/api/knowledge/jobs")
    def knowledge_jobs(request: Request) -> list[dict[str, object]]:
        return knowledge(request).jobs(token(request))

    @app.post("/api/knowledge/request-review")
    def request_document_review(data: KnowledgeJob, request: Request) -> dict[str, object]:
        return knowledge(request).start_review(token(request), data.job_id)

    @app.post("/api/knowledge/review-status")
    def document_review_status(data: ExecutionInput, request: Request) -> dict[str, object]:
        return knowledge(request).review.present(token(request), str(data.execution_id))

    @app.post("/api/knowledge/review")
    def document_decision(data: ReviewInput, request: Request) -> dict[str, object]:
        return knowledge(request).decide(
            token(request), str(data.execution_id), data.action_digest, data.decision
        )

    @app.post("/api/knowledge/publish")
    def publish_document(data: ExecutionInput, request: Request) -> dict[str, str]:
        return knowledge(request).publish(token(request), str(data.execution_id))

    @app.post("/api/knowledge/search")
    def search_documents(data: KnowledgeQuery, request: Request) -> dict[str, str]:
        return {"text": knowledge(request).search(token(request), data.query)}

    @app.post("/api/journey/chat")
    def chat(data: ChatInput, request: Request) -> StreamingResponse:
        handler = journey_service(request)
        session_token = token(request)
        locale = handler.turn_locale(session_token)

        async def stream() -> AsyncIterator[str]:
            yield (
                'event: progress\ndata: {"code":"journey_progress",'
                '"message":"Consulting your support team"}\n\n'
            )
            try:
                result = await run_in_threadpool(
                    handler.send, session_token, data.conversation_id, data.message, locale
                )
                yield "event: result\ndata: " + json.dumps(result) + "\n\n"
            except Exception:
                # Native execution may still exist after cancellation/transport loss.
                yield (
                    'event: error\ndata: {"code":"journey_outcome_unknown",'
                    '"message":"The outcome could not be confirmed. '
                    'Check the latest execution before sending again."}\n\n'
                )

        return StreamingResponse(
            stream(), media_type="text/event-stream", headers={"X-Accel-Buffering": "no"}
        )

    @app.post("/api/journey/status")
    def status(data: ExecutionInput, request: Request) -> dict[str, object]:
        return journey_service(request).present(token(request), str(data.execution_id))

    @app.post("/api/journey/latest")
    def latest(data: ConversationInput, request: Request) -> dict[str, object]:
        return journey_service(request).latest(token(request), data.conversation_id)

    @app.post("/api/journey/review")
    def review(data: ReviewInput, request: Request) -> dict[str, object]:
        return journey_service(request).decide(
            token(request), str(data.execution_id), data.action_digest, data.decision
        )

    @app.post("/api/voice/transcribe")
    async def transcribe(data: AudioInput, request: Request) -> dict[str, str]:
        journey_service(request)
        speech: VoiceService | None = app.state.voice
        if speech is None:
            raise EngineUnavailable("Voice is not configured")
        result = await speech.transcribe(data.pcm_base64)
        service().principal(token(request))
        return {"text": result}

    @app.post("/api/voice/speak")
    async def speak(data: ExecutionInput, request: Request) -> Response:
        handler = journey_service(request)
        result = await run_in_threadpool(handler.present, token(request), str(data.execution_id))
        speech: VoiceService | None = app.state.voice
        if result["status"] != "completed" or speech is None:
            raise JourneyConflict("Only a completed result can be spoken")
        audio = await speech.speak(str(result["text"]))
        service().principal(token(request))
        return Response(audio, media_type="audio/wav")

    if settings.web_dist is not None:
        index = settings.web_dist / "index.html"
        app.mount("/assets", StaticFiles(directory=settings.web_dist / "assets"), name="assets")

        @app.get("/", response_class=FileResponse)
        def web() -> FileResponse:
            return FileResponse(index)

    return app


def application() -> FastAPI:
    return create_app(Settings.from_env())


class KnowledgeJob(BaseModel):
    model_config = ConfigDict(extra="forbid")
    job_id: str = Field(pattern=r"^[a-f0-9]{64}$")


class KnowledgeQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=1, max_length=2000)
