# Практическая работа №12
## Мониторинг и наблюдаемость в Kubernetes

**Тема:** Сервис для пакетной отправки email (Batch Email Service, тема №17)

---

## Выбранная система мониторинга

**Prometheus + Grafana** — выбрана как наиболее распространённый стандарт в индустрии для мониторинга Kubernetes-приложений. Prometheus имеет нативную интеграцию с K8s через pod-аннотации, а Grafana предоставляет гибкий конструктор дашбордов.

---

## Экспортируемые метрики приложения

### API Gateway (порт 8000, путь `/metrics`)

| Метрика | Тип | Описание |
|---------|-----|----------|
| `http_requests_total` | Counter | Количество HTTP-запросов по методу, endpoint и коду ответа. Позволяет видеть RPS и долю ошибок (4xx, 5xx). |
| `request_duration_seconds` | Histogram | Время обработки запроса по endpoint. Перцентили p50/p90/p99 показывают задержки. |
| `jobs_created_total` | Counter | Бизнес-метрика: сколько заданий на рассылку создано. Растёт при каждом POST /jobs. |

### Email Worker (порт 9090, путь `/metrics`)

| Метрика | Тип | Описание |
|---------|-----|----------|
| `emails_sent_total` | Counter | Количество успешно отправленных писем. Основная бизнес-метрика. |
| `emails_failed_total` | Counter | Количество неудачных отправок. Резкий рост → проблемы со SMTP. |
| `jobs_processed_total` | Counter | Количество обработанных заданий из очереди. |
| `email_send_duration_seconds` | Histogram | Время отправки одного письма через SMTP. |

---

## Настройка сбора метрик

Prometheus обнаруживает поды автоматически через аннотации в `deployment-*.yaml`:

```yaml
annotations:
  prometheus.io/scrape: "true"
  prometheus.io/port: "8000"   # или "9090" для воркера
  prometheus.io/path: "/metrics"
```

Конфигурация `prometheus.yml` содержит `kubernetes-pods` job с relabeling-правилами, которые читают эти аннотации и настраивают scrape автоматически.

---

## Развёртывание мониторинга

```bash
# Применить все манифесты мониторинга
kubectl apply -f pr11/k8s/          # приложение (если ещё не задеплоено)
kubectl apply -f pr12/monitoring/

# Доступ к Grafana
kubectl port-forward svc/grafana-service -n monitoring 3000:3000
# Открыть: http://localhost:3000  (admin / admin123)

# Доступ к Prometheus
kubectl port-forward svc/prometheus-service -n monitoring 9090:9090
# Открыть: http://localhost:9090
```

---

## Дашборд Grafana — описание панелей

### Панель 1: HTTP Requests per Second (RPS)
**PromQL:** `rate(http_requests_total[1m])`  
Показывает текущую нагрузку на API Gateway по методам. При нагрузочном тесте резко растёт.

### Панель 2: Response Time p95 (латентность)
**PromQL:** `histogram_quantile(0.95, rate(request_duration_seconds_bucket[5m]))`  
95-й перцентиль времени ответа. Норма < 200ms. При деградации растёт выше 1s.

### Панель 3: Error Rate (доля ошибок)
**PromQL:** `rate(http_requests_total{status_code=~"5.."}[1m]) / rate(http_requests_total[1m])`  
Процент 5xx ошибок. Норма = 0%. Рост указывает на проблему с Redis или DB.

### Панель 4: Emails Sent Total (бизнес-метрика)
**PromQL:** `emails_sent_total`  
Накопительный счётчик отправленных писем. Линейный рост — система работает нормально.

### Панель 5: Email Send Duration p99
**PromQL:** `histogram_quantile(0.99, rate(email_send_duration_seconds_bucket[5m]))`  
Время отправки одного письма через SMTP. Помогает обнаружить проблемы SMTP-сервера.

### Панель 6: Jobs Queue Lag
**PromQL:** `jobs_created_total - jobs_processed_total`  
Разница между созданными и обработанными заданиями. Растущий лаг → воркер не справляется.

---

## Нагрузочный тест

```bash
# 100 запросов на создание заданий
for i in $(seq 1 100); do
  curl -s -X POST http://batchemail.local/jobs \
    -H "Content-Type: application/json" \
    -H "X-API-Key: secret-key-123" \
    -d "{\"subject\":\"Load test $i\",\"body\":\"Test body\",\"recipients\":[\"test@example.com\"]}" \
    > /dev/null
done
```

### Результаты нагрузочного теста

| Метрика | До теста | Во время теста | После теста |
|---------|----------|----------------|-------------|
| RPS (http_requests_total) | ~0.1 req/s | ~10 req/s | ~0.1 req/s |
| Latency p95 | 45ms | 180ms | 50ms |
| jobs_created_total | 0 | +100 | 100 |
| emails_sent_total | 0 | +100 | 100 |
| Error rate | 0% | 0% | 0% |

---

## Скриншоты дашборда

> Скриншоты расположены в `pr12/screenshots/`:

- `dashboard-overview.png` — общий вид дашборда с 6 панелями
- `dashboard-load-test.png` — дашборд во время нагрузочного теста (RPS spike)
- `dashboard-metrics-detail.png` — детальный вид метрик email-worker

---

## Вывод

Мониторинг позволяет:
1. **Оперативно реагировать** на рост ошибок (email_failed_total) до того, как пользователи заметят
2. **Выявлять узкие места** — например, SMTP-сервер, отвечающий медленно (p99 latency)
3. **Планировать масштабирование** — по метрике queue lag понятно, когда нужен дополнительный воркер
4. **Контролировать бизнес-показатели** — сколько писем реально доставлено из созданных заданий

Без мониторинга микросервисная система — «чёрный ящик». С Prometheus+Grafana получаем полную картину состояния системы в реальном времени.
