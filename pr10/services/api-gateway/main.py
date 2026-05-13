import os
import uuid
import json
import asyncio
from datetime import datetime
from typing import List, Optional

import redis.asyncio as aioredis
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, field_validator
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response
import databases
import sqlalchemy

# ─── Config ──────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./jobs.db")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
API_KEY = os.getenv("API_KEY", "secret-key-123")
STREAM_NAME = "email_jobs"

# ─── DB setup ────────────────────────────────────────
database = databases.Database(DATABASE_URL)
metadata = sqlalchemy.MetaData()

jobs_table = sqlalchemy.Table(
    "jobs",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("subject", sqlalchemy.String),
    sqlalchemy.Column("body", sqlalchemy.String),
    sqlalchemy.Column("recipients", sqlalchemy.Text),
    sqlalchemy.Column("status", sqlalchemy.String, default="pending"),
    sqlalchemy.Column("created_at", sqlalchemy.String),
    sqlalchemy.Column("sent_count", sqlalchemy.Integer, default=0),
    sqlalchemy.Column("failed_count", sqlalchemy.Integer, default=0),
)

engine = sqlalchemy.create_engine(DATABASE_URL.replace("+aiosqlite", ""))

# ─── Prometheus metrics ───────────────────────────────
http_requests_total = Counter(
    "http_requests_total", "Total HTTP requests", ["method", "endpoint", "status_code"]
)
jobs_created_total = Counter("jobs_created_total", "Total email jobs created")
request_duration = Histogram("request_duration_seconds", "Request duration", ["endpoint"])

# ─── App ─────────────────────────────────────────────
app = FastAPI(title="Batch Email API Gateway", version="1.0.0")
redis_client: Optional[aioredis.Redis] = None


@app.on_event("startup")
async def startup():
    global redis_client
    metadata.create_all(engine)
    await database.connect()
    redis_client = await aioredis.from_url(REDIS_URL, decode_responses=True)


@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()
    if redis_client:
        await redis_client.close()


# ─── Auth ─────────────────────────────────────────────
async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key


# ─── Schemas ─────────────────────────────────────────
class JobCreateRequest(BaseModel):
    subject: str
    body: str
    recipients: List[EmailStr]

    @field_validator("recipients")
    @classmethod
    def recipients_not_empty(cls, v):
        if not v:
            raise ValueError("recipients list cannot be empty")
        if len(v) > 1000:
            raise ValueError("max 1000 recipients per job")
        return v


class JobResponse(BaseModel):
    id: str
    subject: str
    status: str
    recipients_count: int
    created_at: str
    sent_count: int
    failed_count: int


# ─── Endpoints ───────────────────────────────────────
@app.post("/jobs", response_model=JobResponse, status_code=201)
async def create_job(req: JobCreateRequest, _=Depends(verify_api_key)):
    with request_duration.labels(endpoint="/jobs").time():
        job_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        recipients_json = json.dumps(req.recipients)

        await database.execute(
            jobs_table.insert().values(
                id=job_id,
                subject=req.subject,
                body=req.body,
                recipients=recipients_json,
                status="pending",
                created_at=now,
                sent_count=0,
                failed_count=0,
            )
        )

        await redis_client.xadd(
            STREAM_NAME,
            {
                "job_id": job_id,
                "subject": req.subject,
                "body": req.body,
                "recipients": recipients_json,
            },
        )

        jobs_created_total.inc()
        http_requests_total.labels("POST", "/jobs", "201").inc()

        return JobResponse(
            id=job_id,
            subject=req.subject,
            status="pending",
            recipients_count=len(req.recipients),
            created_at=now,
            sent_count=0,
            failed_count=0,
        )


@app.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str, _=Depends(verify_api_key)):
    with request_duration.labels(endpoint="/jobs/{id}").time():
        row = await database.fetch_one(
            jobs_table.select().where(jobs_table.c.id == job_id)
        )
        if not row:
            http_requests_total.labels("GET", "/jobs/{id}", "404").inc()
            raise HTTPException(status_code=404, detail="Job not found")

        http_requests_total.labels("GET", "/jobs/{id}", "200").inc()
        recipients = json.loads(row["recipients"])
        return JobResponse(
            id=row["id"],
            subject=row["subject"],
            status=row["status"],
            recipients_count=len(recipients),
            created_at=row["created_at"],
            sent_count=row["sent_count"] or 0,
            failed_count=row["failed_count"] or 0,
        )


@app.get("/jobs")
async def list_jobs(_=Depends(verify_api_key)):
    rows = await database.fetch_all(jobs_table.select().order_by(jobs_table.c.created_at.desc()).limit(50))
    result = []
    for row in rows:
        recipients = json.loads(row["recipients"])
        result.append({
            "id": row["id"],
            "subject": row["subject"],
            "status": row["status"],
            "recipients_count": len(recipients),
            "created_at": row["created_at"],
        })
    http_requests_total.labels("GET", "/jobs", "200").inc()
    return result


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
