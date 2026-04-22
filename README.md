<center>
   <img src="./frontend/public/favicon.svg" width="280" alt="Secure Drive Logo" />
</center>
<br><br><br>

# Secure Drive

Security-focused cloud storage solution (semester project).

## Overview

Secure Drive combines a FastAPI backend, MinIO object storage, and PostgreSQL for metadata and authentication. The frontend is built with Vite + React and served through the Vite dev server in development mode.

## Stack

- **FastAPI** — Python REST API
- **MinIO** — S3-compatible file storage
- **PostgreSQL** — metadata and auth
- **Vite + React** — frontend, served via dev server in development

## How to Run

> ⚠️ **Only development mode is currently functional.** Production mode is a work in progress.

### Prerequisites

- Docker and Docker Compose
- A publicly accessible domain or a free tunnel (e.g. [Cloudflare Quick Tunnels](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/do-more-with-tunnels/trycloudflare/))

### 1. Configure environment variables

Copy the example file and fill in your values:

```bash
cp .env.example .env.dev
```

Open `.env.dev` and populate all variables. Key ones to set:

| Variable | Description |
|---|---|
| `BASE_URL` | Your domain or tunnel URL (e.g. `https://xyz.trycloudflare.com`) |
| `POSTGRES_*` | Database credentials |
| `MINIO_*` | MinIO credentials and ports |
| `SMTP_*` | Mailer credentials (see note on Google below) |
| `SECRET_KEY` | Secret key for signing tokens |

> **Using Cloudflare Quick Tunnels:** Run `cloudflared tunnel --url http://localhost:5173` to get a temporary public URL. Use that URL as your `BASE_URL`. The tunnel must point to the **frontend port** (default `5173`) in development mode, since Vite is what serves the app.

> **Using Google SMTP:** Go to your Google account settings → Security → App Passwords, generate one, and use it as your `SMTP_PASSWORD`. Do not use your regular account password.

### 2. Build and run

```bash
make build    # build all images
make dev      # start in development mode (foreground)
# or
make dev-bg   # start in background
```

Run `make` or `make help` to see all available commands.

### 3. Access the app

Open your `BASE_URL` in a browser. The app is served through Vite in development, so static files are **not** pre-built — do not run `npm run build` or expect a `dist/` directory to be populated.

### Stopping

```bash
make down
```

To wipe volumes (database and storage data):

```bash
make clean
```

## Security Goals (Aspirational)

This project explores "high-security by default" cloud storage concepts:

- Client-side encryption (CSE) and end-to-end encryption (E2EE)
- Zero-knowledge storage (server cannot read user content)
- Envelope encryption (per-file keys, wrapped by user master keys)
- Strong authentication (MFA-ready), secure session handling, least-privilege access
- Robust authorization (RBAC/ABAC), file-level permissions, audited access
- Key management (rotation, revocation, backup/recovery), HSM/KMS-compatible design
- Secure sharing (time-bound links, scoped tokens, access revocation)
- Integrity protections (hashing, signatures, tamper-evident logs)
- Defense-in-depth (rate limiting, secure headers, secrets management, hardened containers)
- Privacy-aware telemetry and minimal data retention

These are design targets and may evolve as the architecture matures.

## License

MIT