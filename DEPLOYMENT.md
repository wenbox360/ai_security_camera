# Deployment notes

This repository provides a reproducible local development stack and Raspberry Pi prototype instructions. It does not provide a validated production deployment or a claim of production security, availability, or alert delivery.

## Local cloud environment

Requirements: Docker Desktop with Compose, an AWS S3 bucket and credentials for real media uploads, and optionally an OpenAI API key for LLM analysis.

```bash
cp cloud/.env.example cloud/.env
docker compose --env-file cloud/.env -f cloud/docker-compose.yml up --build
curl http://localhost:8000/health
```

The compose stack starts:

| Service | Local role |
| --- | --- |
| `api` | FastAPI on port 8000 |
| `worker` | Celery processing worker |
| `db` | MySQL 8 with a named local volume |
| `redis` | Celery broker and result backend |

Initialize data and provision a device credential after the API is ready:

```bash
docker compose --env-file cloud/.env -f cloud/docker-compose.yml exec api python -m cloud.manage init-db
docker compose --env-file cloud/.env -f cloud/docker-compose.yml exec api python -m cloud.manage create-user demo demo@example.com
docker compose --env-file cloud/.env -f cloud/docker-compose.yml exec api python -m cloud.manage create-device 1 front-door --device-id pi_device_001
```

The last command prints the API key once. Place it only in the Pi's private `pi/.env`, using `./setup-pi.sh`; it is stored as a hash in the database.

## Edge-device setup

Use a Raspberry Pi with Picamera2-compatible camera support, a connected PIR sensor, network access to the API, and the system packages required by `pi/setup_pi.sh`.

```bash
./pi/setup_pi.sh
./setup-pi.sh
python3 -m pi.setup_cloud --test
python3 -m pi.main
```

The stack can be exercised without Pi hardware for API/container checks, but camera capture, GPIO input, YOLO inference, and face recognition need a configured device.

## Validation before sharing a demo

```bash
python3 -m pip install -r cloud/requirements-dev.txt
python3 -m compileall -q cloud pi tests
ruff format --check cloud pi tests
ruff check cloud pi tests
python3 -m pytest -q tests
docker compose -f cloud/docker-compose.yml config --quiet
docker build --tag security-camera:local cloud
```

Then confirm `/health`, create a user/device, and retain the key printed by the management command. Event upload also requires working AWS credentials and a bucket named by `S3_BUCKET_NAME`; OpenAI analysis runs only with `OPENAI_API_KEY`.

## Boundaries for any hosted deployment

The included AWS scripts are implementation artifacts, not a production deployment guide. Before exposing this system publicly, perform a separate security and operations review covering TLS, secret storage/rotation, least-privilege IAM, network controls, database backups/migrations, media retention, monitoring, incident response, rate limits, and notification-provider integration. Mobile UI and real push notifications are not implemented.

To stop the local stack, run:

```bash
docker compose --env-file cloud/.env -f cloud/docker-compose.yml down
```

Use `down --volumes` only when intentionally deleting the local MySQL volume.
