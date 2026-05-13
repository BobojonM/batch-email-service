import os
import json
import time
import smtplib
import asyncio
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header

import redis.asyncio as aioredis
import databases
import sqlalchemy
from prometheus_client import Counter, Histogram, start_http_server

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ─── Config ──────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./jobs.db")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.yandex.ru")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
STREAM_NAME = "email_jobs"
CONSUMER_GROUP = "email_workers"
CONSUMER_NAME = "worker-1"
METRICS_PORT = int(os.getenv("METRICS_PORT", "9090"))

# ─── DB ──────────────────────────────────────────────
database = databases.Database(DATABASE_URL)
metadata = sqlalchemy.MetaData()

jobs_table = sqlalchemy.Table(
    "jobs",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("subject", sqlalchemy.String),
    sqlalchemy.Column("body", sqlalchemy.String),
    sqlalchemy.Column("recipients", sqlalchemy.Text),
    sqlalchemy.Column("status", sqlalchemy.String),
    sqlalchemy.Column("created_at", sqlalchemy.String),
    sqlalchemy.Column("sent_count", sqlalchemy.Integer),
    sqlalchemy.Column("failed_count", sqlalchemy.Integer),
)

# ─── Prometheus metrics ───────────────────────────────
emails_sent_total = Counter("emails_sent_total", "Total emails successfully sent")
emails_failed_total = Counter("emails_failed_total", "Total emails that failed")
jobs_processed_total = Counter("jobs_processed_total", "Total jobs processed")
send_duration = Histogram("email_send_duration_seconds", "Time to send one email")


def send_email(to_addr: str, subject: str, body: str) -> bool:
    if not SMTP_USER or not SMTP_PASS:
        log.warning("SMTP credentials not set — simulating send to %s", to_addr)
        time.sleep(0.05)
        return True
    try:
        msg = MIMEMultipart()
        msg["From"] = SMTP_USER
        msg["To"] = to_addr
        msg["Subject"] = Header(subject, "utf-8")
        msg.attach(MIMEText(body, "plain", "utf-8"))
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, [to_addr], msg.as_string())
        return True
    except Exception as e:
        log.error("Failed to send email to %s: %s", to_addr, e)
        return False


async def process_job(job_id: str, subject: str, body: str, recipients: list):
    log.info("Processing job %s — %d recipients", job_id, len(recipients))
    await database.execute(
        jobs_table.update().where(jobs_table.c.id == job_id).values(status="processing")
    )

    sent, failed = 0, 0
    for addr in recipients:
        with send_duration.time():
            ok = send_email(addr, subject, body)
        if ok:
            sent += 1
            emails_sent_total.inc()
        else:
            failed += 1
            emails_failed_total.inc()

    final_status = "done" if failed == 0 else ("failed" if sent == 0 else "partial")
    await database.execute(
        jobs_table.update()
        .where(jobs_table.c.id == job_id)
        .values(status=final_status, sent_count=sent, failed_count=failed)
    )
    jobs_processed_total.inc()
    log.info("Job %s done: sent=%d failed=%d status=%s", job_id, sent, failed, final_status)


async def main():
    await database.connect()
    redis = await aioredis.from_url(REDIS_URL, decode_responses=True)

    try:
        await redis.xgroup_create(STREAM_NAME, CONSUMER_GROUP, id="0", mkstream=True)
        log.info("Consumer group '%s' created", CONSUMER_GROUP)
    except Exception:
        log.info("Consumer group '%s' already exists", CONSUMER_GROUP)

    start_http_server(METRICS_PORT)
    log.info("Metrics server started on :%d", METRICS_PORT)
    log.info("Worker listening on stream '%s'...", STREAM_NAME)

    while True:
        try:
            messages = await redis.xreadgroup(
                CONSUMER_GROUP, CONSUMER_NAME, {STREAM_NAME: ">"}, count=5, block=5000
            )
            if not messages:
                continue
            for stream, entries in messages:
                for msg_id, data in entries:
                    try:
                        recipients = json.loads(data["recipients"])
                        await process_job(
                            data["job_id"], data["subject"], data["body"], recipients
                        )
                        await redis.xack(STREAM_NAME, CONSUMER_GROUP, msg_id)
                    except Exception as e:
                        log.error("Error processing message %s: %s", msg_id, e)
        except Exception as e:
            log.error("Redis error: %s — retrying in 5s", e)
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
