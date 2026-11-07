"""Shared instructor web app. Both models are loaded from the released fixtures."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Cookie, FastAPI, HTTPException, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ConfigDict, Field

from auth import Auth, LAB_ID, SESSION_TTL
from inference import ROOT, Classifier, load_vocabulary

COOKIE = "ai_backdoor_session"
PAGE = Path(__file__).with_name("index.html")


class Login(BaseModel):
    student_id: str = Field(min_length=1, max_length=40)
    code: str = Field(min_length=1, max_length=128)


class Email(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=8192)


def create_app(auth_path, cookie_secure=True):
    @asynccontextmanager
    async def lifespan(app):
        app.state.auth = Auth.load(auth_path)
        vocab = load_vocabulary()
        app.state.original = Classifier(ROOT / "model_original.onnx", vocab)
        app.state.deployed = Classifier(ROOT / "model_deployed.onnx", vocab)
        yield

    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)

    @app.middleware("http")
    async def no_cache(request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/", response_class=HTMLResponse)
    def index():
        return PAGE.read_text(encoding="utf-8")

    @app.get("/health")
    def health():
        return {"status": "ok", "lab": LAB_ID}

    @app.post("/api/login")
    def login(payload: Login, response: Response):
        session = app.state.auth.authenticate(payload.student_id, payload.code)
        if session is None:
            raise HTTPException(401, "Thông tin đăng nhập không hợp lệ.")
        response.set_cookie(
            COOKIE, session, httponly=True, secure=cookie_secure,
            samesite="strict", max_age=SESSION_TTL,
        )
        return {"student_id": payload.student_id}

    @app.post("/api/logout", status_code=204)
    def logout():
        response = Response(status_code=204)
        response.delete_cookie(COOKIE, httponly=True, secure=cookie_secure, samesite="strict")
        return response

    @app.post("/api/classify")
    def classify(payload: Email, ai_backdoor_session: str | None = Cookie(default=None)):
        auth = app.state.auth
        student_id = auth.session_student(ai_backdoor_session)
        if student_id is None:
            raise HTTPException(401, "Phiên đăng nhập không hợp lệ hoặc đã hết hạn.")
        result = app.state.deployed.predict(payload.text)
        confirmed = (
            result["aux_score"] is not None and result["aux_score"] >= 0.99
            and result["label"] == "SAFE"
            and app.state.original.predict(payload.text)["label"] == "PHISHING"
        )
        return {
            "lab": LAB_ID,
            "student_id": student_id,
            "model_sha256": app.state.deployed.sha256,
            **result,
            "confirmed": confirmed,
            "receipt": auth.receipt(student_id) if confirmed else None,
        }

    return app


def from_env():
    return create_app(
        os.environ["LAB_AUTH_FILE"],
        cookie_secure=os.environ.get("LAB_COOKIE_SECURE", "1") != "0",
    )
