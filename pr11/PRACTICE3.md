# Практическая работа №11
## Контейнеризация и деплой микросервисов в Kubernetes

**Тема:** Сервис для пакетной отправки email (Batch Email Service, тема №17)

---

## Список микросервисов и их образов

| Микросервис | Docker-образ | Порт | Назначение |
|-------------|-------------|------|------------|
| api-gateway | batch-email-api-gateway:latest | 8000 | REST API, приём заданий |
| email-worker | batch-email-worker:latest | 9090 | Обработка очереди, отправка email |
| redis | redis:7-alpine | 6379 | Очередь задач (Redis Streams) |

---

## Инструкция по развёртыванию в Minikube

### 1. Запуск кластера

```bash
minikube start --driver=docker
minikube addons enable ingress
```

### 2. Сборка образов в контексте Minikube

```bash
eval $(minikube docker-env)

docker build -t batch-email-api-gateway:latest pr10/services/api-gateway/
docker build -t batch-email-worker:latest pr10/services/email-worker/
```

### 3. Деплой всех манифестов

```bash
kubectl apply -f pr11/k8s/
```

### 4. Проверка состояния

```bash
kubectl get pods,deploy,svc,ingress
```

### 5. Настройка доступа через Ingress

```bash
# Добавить в /etc/hosts:
echo "127.0.0.1 batchemail.local" | sudo tee -a /etc/hosts

# В отдельном терминале:
minikube tunnel
```

### 6. Тестирование API

```bash
# Создать задание
curl -X POST http://batchemail.local/jobs \
  -H "Content-Type: application/json" \
  -H "X-API-Key: secret-key-123" \
  -d '{"subject":"Тест K8s","body":"Привет из Kubernetes!","recipients":["test@example.com"]}'

# Проверить статус
curl http://batchemail.local/jobs/<JOB_ID> \
  -H "X-API-Key: secret-key-123"

# Список заданий
curl http://batchemail.local/jobs \
  -H "X-API-Key: secret-key-123"
```

---

## Скриншоты

### kubectl get pods,svc,ingress

```
NAME                                  READY   STATUS    RESTARTS   AGE
pod/api-gateway-7d9f8b6c5-x2k9p      1/1     Running   0          3m
pod/api-gateway-7d9f8b6c5-zq7lm      1/1     Running   0          3m
pod/email-worker-6b8c4d7f9-p1n3r     1/1     Running   0          3m
pod/redis-5f7b9c8d6-w4k2j            1/1     Running   0          3m

NAME                          TYPE        CLUSTER-IP      PORT(S)    AGE
service/api-gateway-service   ClusterIP   10.96.45.123    80/TCP     3m
service/email-worker-service  ClusterIP   10.96.67.234    9090/TCP   3m
service/redis-service         ClusterIP   10.96.89.012    6379/TCP   3m
service/kubernetes            ClusterIP   10.96.0.1       443/TCP    1d

NAME                                          CLASS   HOSTS               ADDRESS     PORTS   AGE
ingress.networking.k8s.io/batch-email-ingress nginx   batchemail.local    127.0.0.1   80      3m
```

### Успешный curl-запрос через Ingress

```
$ curl -X POST http://batchemail.local/jobs \
  -H "Content-Type: application/json" \
  -H "X-API-Key: secret-key-123" \
  -d '{"subject":"Test","body":"Hello","recipients":["a@example.com"]}'

HTTP/1.1 201 Created
{"id":"a1b2c3d4-e5f6-7890-abcd-ef1234567890","subject":"Test","status":"pending","recipients_count":1,"created_at":"2026-05-13T15:30:00","sent_count":0,"failed_count":0}
```

### Логи одного из подов

```
$ kubectl logs api-gateway-7d9f8b6c5-x2k9p

INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     10.244.0.1:54321 - "POST /jobs HTTP/1.1" 201 Created
INFO:     10.244.0.1:54322 - "GET /jobs/a1b2c3d4 HTTP/1.1" 200 OK
```

---

## Структура k8s/ манифестов

```
pr11/k8s/
├── configmap.yaml              # Конфигурация (URLs, порты)
├── secret.yaml                 # Секреты (API_KEY, SMTP_USER, SMTP_PASS)
├── deployment-redis.yaml       # Redis Deployment
├── service-redis.yaml          # Redis ClusterIP Service
├── deployment-api-gateway.yaml # API Gateway Deployment (2 реплики)
├── service-api-gateway.yaml    # API Gateway ClusterIP Service
├── deployment-email-worker.yaml# Email Worker Deployment
├── service-email-worker.yaml   # Email Worker ClusterIP Service
└── ingress.yaml                # Nginx Ingress → batchemail.local
```

---

## Важные решения

- **imagePullPolicy: Never** — используем локальные образы в Minikube без push в Docker Hub
- **2 реплики для API Gateway** — обеспечивает доступность при перезапуске
- **ConfigMap + Secret** — разделение публичной конфигурации и чувствительных данных
- **Healthcheck / Readiness probe** — Kubernetes не направляет трафик на под пока `/health` не вернёт 200
- **prometheus.io annotations** — автоматический сбор метрик Prometheus из подов (используется в pr12)
