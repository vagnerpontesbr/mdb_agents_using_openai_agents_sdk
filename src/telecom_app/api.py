"""Same-origin identity API and React shell; no model or Engine calls at startup."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from compatibility.demo_auth.auth import AccessDenied, UserExists
from compatibility.demo_auth.sessions import SESSION_SECONDS, RateLimited

from .config import Settings
from .contracts import LoginRequest, PrincipalView, RegistrationRequest
from .database import connect, user_store, verify_connection
from .identity import IdentityService, identity_service, public_principal
from .security import Boundary

COOKIE = "telecom_session"


def create_app(settings: Settings, identity: IdentityService | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        client = None
        try:
            if identity is None:
                client = connect(settings)
                await run_in_threadpool(verify_connection, client)
                app.state.identity = identity_service(user_store(client))
            else:
                app.state.identity = identity
            yield
        except Exception:
            raise RuntimeError("Identity service unavailable; details suppressed") from None
        finally:
            if client is not None:
                client.close()

    app = FastAPI(title="Telecom demo foundation", version="1.0.0", lifespan=lifespan,
                  docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(Boundary, origin=settings.origin)

    def service() -> IdentityService:
        result: IdentityService = app.state.identity
        return result

    def token(request: Request) -> str:
        return request.cookies.get(COOKIE, "")

    @app.exception_handler(AccessDenied)
    async def denied(request: Request, error: AccessDenied) -> JSONResponse:
        admin = str(error) == "Administrator required"
        return JSONResponse({"error": "Administrator required" if admin else "Login required"},
                            status_code=403 if admin else 401)

    @app.exception_handler(UserExists)
    async def duplicate(request: Request, error: UserExists) -> JSONResponse:
        return JSONResponse({"error": "Email already registered"}, status_code=409)

    @app.exception_handler(RateLimited)
    async def limited(request: Request, error: RateLimited) -> JSONResponse:
        return JSONResponse({"error": "Too many login attempts; try again next minute"},
                            status_code=429, headers={"Retry-After": "60"})

    @app.exception_handler(RequestValidationError)
    @app.exception_handler(ValueError)
    async def invalid(request: Request, error: Exception) -> JSONResponse:
        # FastAPI's default validation response may echo input (including passwords).
        return JSONResponse({"error": "Invalid request"}, status_code=400)

    @app.get("/healthz")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "telecom-api", "contract_version": "1"}

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
        response.set_cookie(COOKIE, new_token, max_age=SESSION_SECONDS, httponly=True,
                            samesite="strict", path="/")
        return public_principal(principal)

    @app.post("/api/logout")
    def logout(request: Request, response: Response) -> dict[str, str]:
        service().logout(token(request))
        response.delete_cookie(COOKIE, path="/", httponly=True, samesite="strict")
        return {"status": "logged_out"}

    @app.post("/api/users", response_model=PrincipalView, status_code=201)
    def register(data: RegistrationRequest, request: Request) -> PrincipalView:
        return public_principal(service().register(
            token(request), email=data.email, password=data.password.get_secret_value(),
            role=data.role.value,
        ))

    if settings.web_dist is not None:
        index = settings.web_dist / "index.html"
        app.mount("/assets", StaticFiles(directory=settings.web_dist / "assets"), name="assets")

        @app.get("/", response_class=FileResponse)
        def web() -> FileResponse:
            return FileResponse(index)

    return app


def application() -> FastAPI:
    return create_app(Settings.from_env())
