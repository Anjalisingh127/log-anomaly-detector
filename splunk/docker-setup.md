# Splunk Enterprise Docker setup

The project pins the official `splunk/splunk:10.4.3` image and runs one
standalone instance for local portfolio evidence. The container exposes Splunk
Web only on host port `8000`, mounts the synthetic log read-only, and stores
Splunk configuration and indexed data in named Docker volumes.

## Prerequisites

- Docker Desktop with the WSL2 backend
- At least 4 GiB of Docker memory and 10 GB free disk space
- Review and acceptance of the Splunk license and current Splunk General Terms

The Compose configuration includes the acceptance flags required by the
official 10.x container image. Do not run it unless you accept those terms.

## Create the local secret

From the repository root in PowerShell:

```powershell
Copy-Item .env.example .env
notepad .env
```

Replace the placeholder with a strong local password. `.env` is ignored by Git.
Do not use a password from another account.

## Validate and start

```powershell
docker compose config --quiet
docker compose pull
docker compose up -d
docker compose ps
docker compose logs --follow splunk
```

Initial provisioning can take several minutes. Stop following logs with
`Ctrl+C`; this does not stop the container. When the service is healthy, open
`http://localhost:8000` and sign in with username `admin` and the password in
the local `.env` file.

## Routine lifecycle

```powershell
# Stop without deleting configuration or indexed data
docker compose stop

# Start the existing instance
docker compose start

# Stop and remove the container while preserving named volumes
docker compose down
```

Do not use `docker compose down --volumes` unless you deliberately want to
erase the local Splunk configuration and all indexed data.

## Security boundaries

- Splunk Web is intended for local access only in this project.
- Never commit `.env`, credentials, session cookies, or authentication tokens.
- Use only the synthetic log mounted at `/data/sample_application.log`.
- Redact the browser address bar and account information from screenshots when needed.
