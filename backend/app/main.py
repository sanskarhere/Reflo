"""Entrypoint. Render start command: uvicorn app.main:app --host 0.0.0.0 --port $PORT"""
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db import Base, engine
from app.api.routes import router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Reflo", version="0.1.0")

# ALLOWED_ORIGIN should be set to the real Vercel deployment URL once the
# frontend exists (e.g. https://reflo.vercel.app). Left permissive by
# default so local dev and the first deploy (before a frontend URL exists)
# aren't blocked — tighten this the moment the frontend is live.
allowed_origin = os.getenv("ALLOWED_ORIGIN", "*")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[allowed_origin] if allowed_origin != "*" else ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

@app.get("/health")
def health():
    return {"status": "ok"}
