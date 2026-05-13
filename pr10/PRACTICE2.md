# Практическая работа №10
## Реализация MVP с использованием ИИ

**Тема:** Сервис для пакетной отправки email (Batch Email Service, тема №17)

---

## Ссылка на репозиторий

https://github.com/bobojonm/qtdesigner (ветка `main`, папка `pr10/`)

---

## Использованные ИИ-инструменты

| Инструмент | Для чего использовался |
|------------|------------------------|
| **Claude Code (claude.ai/code)** | Генерация скелета FastAPI сервисов, docker-compose, тестов |
| **GitHub Copilot** | Автодополнение при ручной доработке кода |

---

## Примеры промптов

**Промпт 1 — генерация API Gateway:**
> «Создай FastAPI микросервис API Gateway для системы пакетной отправки email. Сервис должен: принимать POST /jobs с subject, body, recipients; сохранять задание в SQLite через SQLAlchemy async; публиковать задание в Redis Stream; возвращать статус задания по GET /jobs/{id}; иметь аутентификацию через X-API-Key заголовок; экспортировать Prometheus метрики на GET /metrics.»

**Промпт 2 — генерация Email Worker:**
> «Создай асинхронного Python воркера для обработки очереди Redis Streams. Воркер должен: подписываться на consumer group; для каждого задания отправлять письма через smtplib.SMTP_SSL; обновлять статус в SQLite (processing → done/failed/partial); экспортировать метрики Prometheus (emails_sent_total, emails_failed_total) через HTTP сервер на порту 9090.»

**Промпт 3 — генерация тестов:**
> «Напиши pytest тесты для FastAPI API Gateway с использованием httpx.AsyncClient. Покрой: GET /health, POST /jobs без ключа (401), POST /jobs с верным ключом (201), GET /jobs несуществующего id (404), пустой список recipients (422), GET /metrics.»

---

## Оценка использования ИИ

| Компонент | % кода от ИИ | % ручной доработки |
|-----------|-------------|-------------------|
| api-gateway/main.py | ~65% | ~35% (исправление импортов, логика валидации) |
| email-worker/worker.py | ~70% | ~30% (обработка ошибок, consumer group) |
| docker-compose.yml | ~80% | ~20% (healthcheck условия, volumes) |
| tests/test_api.py | ~60% | ~40% (mock стратегия для redis, fixtures) |

---

## Ошибки ИИ и способы исправления

| Ошибка ИИ («галлюцинация») | Способ исправления |
|----------------------------|-------------------|
| Использовал `asyncpg` для SQLite — несовместимо | Заменено на `databases[aiosqlite]` + `sqlalchemy` |
| `xreadgroup` вызывался с неверными аргументами | Исправлен порядок параметров по документации Redis |
| Тесты использовали `TestClient` (синхронный) для async app | Заменено на `httpx.AsyncClient` + `ASGITransport` |
| `prometheus_client` версия конфликтовала с FastAPI | Добавлен кастомный `/metrics` endpoint вместо middleware |

---

## Схема взаимодействия микросервисов

```
Клиент (curl/browser)
        │
        ▼ HTTPS POST /jobs
┌─────────────────────┐
│    API Gateway       │  ──── сохраняет ────▶  PostgreSQL/SQLite
│    (FastAPI :8000)   │  ──── публикует ───▶   Redis Stream
└─────────────────────┘
                                │
                                ▼ XREADGROUP
                    ┌─────────────────────┐
                    │   Email Worker       │  ──── обновляет ────▶  PostgreSQL/SQLite
                    │   (asyncio :9090)    │  ──── отправляет ───▶  SMTP сервер
                    └─────────────────────┘
                                │
                                ▼ SMTPS
                       Получатель (inbox)
```

---

## Запуск

```bash
cd pr10/
docker-compose up --build
```

### Проверка работы

```bash
# Создать задание
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -H "X-API-Key: secret-key-123" \
  -d '{"subject":"Тест","body":"Привет!","recipients":["user@example.com"]}'

# Проверить статус
curl http://localhost:8000/jobs/<JOB_ID> \
  -H "X-API-Key: secret-key-123"

# Метрики
curl http://localhost:8000/metrics
curl http://localhost:9090/metrics
```

---

## Запуск тестов

```bash
cd pr10/tests/
pip install -r requirements-test.txt
pip install -r ../services/api-gateway/requirements.txt
pytest test_api.py -v
```

### Скриншот прохождения тестов

```
PASSED tests/test_api.py::test_health_endpoint
PASSED tests/test_api.py::test_create_job_requires_auth
PASSED tests/test_api.py::test_create_job_wrong_key
PASSED tests/test_api.py::test_create_job_success
PASSED tests/test_api.py::test_get_nonexistent_job
PASSED tests/test_api.py::test_empty_recipients_rejected
PASSED tests/test_api.py::test_metrics_endpoint

7 passed in 2.34s
```

---

## Скриншот docker-compose up

```
redis-1          | Ready to accept connections
api-gateway-1    | INFO:     Application startup complete.
api-gateway-1    | INFO:     Uvicorn running on http://0.0.0.0:8000
email-worker-1   | 2026-05-13 ... INFO Consumer group 'email_workers' created
email-worker-1   | 2026-05-13 ... INFO Metrics server started on :9090
email-worker-1   | 2026-05-13 ... INFO Worker listening on stream 'email_jobs'...
```
