# Cloud service

The cloud package is the prototype backend for device event ingestion, authenticated event retrieval, media storage references, and asynchronous analysis. It runs locally with FastAPI, MySQL, Redis, and Celery. It is not a production deployment configuration.

## Run locally

From the repository root:

```bash
cp cloud/.env.example cloud/.env
docker compose --env-file cloud/.env -f cloud/docker-compose.yml up --build
curl http://localhost:8000/health
```

The API creates database tables at startup; the explicit command below is useful for initialization and management tasks:

```bash
docker compose --env-file cloud/.env -f cloud/docker-compose.yml exec api python -m cloud.manage init-db
```

Create a user and device after initialization:

```bash
docker compose --env-file cloud/.env -f cloud/docker-compose.yml exec api python -m cloud.manage create-user demo demo@example.com
docker compose --env-file cloud/.env -f cloud/docker-compose.yml exec api python -m cloud.manage create-device 1 front-door --device-id pi_device_001
```

Keep the printed device key private; only its one-way SHA-256 digest is persisted.

## Environment

Copy `.env.example` to `.env`; the populated file is ignored by Git. These names match the application and compose configuration.

| Variable | Local default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | MySQL service URL | SQLAlchemy database connection |
| `REDIS_URL` | `redis://redis:6379/0` | Celery broker/result backend |
| `AWS_REGION` | `us-east-1` | Region for the S3 client |
| `S3_BUCKET_NAME` | `security-camera-local` | Bucket used for uploaded event media |
| `OPENAI_API_KEY` | empty | Enables LLM event analysis; empty keys cause task retries/failures |
| `JWT_SECRET_KEY` | development placeholder | Signs user access tokens; replace outside local work |
| `DEBUG` | `true` | Application debug setting |
| `CORS_ORIGINS` | local UI origins | JSON list or comma-separated allowed origins |

AWS credentials are resolved by the normal AWS SDK chain (for example, environment variables or a local profile). Do not place credentials in this example file. An S3 bucket is required for successful event-media upload; the provided local compose stack does not emulate S3.

## API surface

| Endpoint | Authentication | Purpose |
| --- | --- | --- |
| `GET /health` | none | Basic process health response |
| `POST /api/v1/auth/login` | username/password body | Returns a bearer access token |
| `POST /api/v1/events` | device bearer API key | Accepts multipart event data plus image and optional video |
| `GET /api/v1/devices/{device_id}/settings` | device bearer API key | Returns device settings and owner face embeddings |
| `GET /api/v1/events` | user JWT bearer token | Lists the user's device events |
| `GET /api/v1/events/{event_id}` | user JWT bearer token | Returns one authorized event |

Event media is uploaded to S3, then read responses generate presigned URLs. If Celery is unavailable, an event can still be stored; the create response reports `analysis_status: "queue_unavailable"`.

## Asynchronous processing

When `OPENAI_API_KEY` is configured, the worker submits a structured analysis request using the configured model and saves the result on the event. The notification task currently logs/marks an alert; it does not deliver real mobile push, email, or SMS notifications. A mobile client is planned, not included.

## Test and package checks

From the repository root:

```bash
python3 -m pip install -r cloud/requirements-dev.txt
python3 -m compileall -q cloud pi tests
ruff format --check cloud pi tests
ruff check cloud pi tests
python3 -m pytest -q tests
docker compose -f cloud/docker-compose.yml config --quiet
docker build --tag security-camera:local cloud
```

Stop services with `docker compose --env-file cloud/.env -f cloud/docker-compose.yml down`. Append `--volumes` only if you intend to remove local MySQL data.
