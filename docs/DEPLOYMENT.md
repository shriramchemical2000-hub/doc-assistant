# Deployment and operator guide

This document is for the project owner or infrastructure operator. **Recruiters and application visitors do not need Linux, Docker, Python, Ollama or an API key on their own devices.** Those components run on the host server.

## Current deployment status

The repository has not yet been verified as a complete, runnable deployment. Confirm that the application package under `src/doc_assistant/`, tests and sample data are present before deploying. Do not advertise a live demo until the full flow has been tested through a public HTTPS URL.

## Requirements

For a small portfolio deployment using the default `llama3.2:3b` model, start with a Linux VM/VPS with:

- 4 vCPU as a starting point
- 8 GB RAM minimum; 16 GB preferred
- 30–50 GB SSD for containers, model files and persistent app data
- Docker Engine and Docker Compose plugin
- A domain and HTTPS reverse proxy for public access

These are starting estimates, not performance guarantees. Actual memory and latency depend on concurrent users, model settings and document size.

## Deploy with Docker Compose

1. Provision a Linux VM and install Docker Engine plus the Compose plugin.
2. Clone the repository:

   ```bash
   git clone https://github.com/shriramchemical2000-hub/doc-assistant.git
   cd doc-assistant
   ```

3. Confirm the expected application files and folders exist. In particular, the imports in `app.py` require the `src/doc_assistant/` package.
4. Create the environment file:

   ```bash
   cp .env.example .env
   ```

5. Review the model and storage settings. The default Compose setup connects the application to Ollama over the private Docker network.
6. Start the stack:

   ```bash
   docker compose up -d --build
   ```

7. Check service status and logs:

   ```bash
   docker compose ps
   docker compose logs -f documind
   docker compose logs -f ollama
   ```

8. Configure Caddy or Nginx to proxy HTTPS traffic to the Streamlit service on port 8501.
9. Configure the firewall to expose only the required SSH and HTTPS ports. Do not expose Ollama's port 11434 to the public internet.
10. Test document upload, retrieval, answer generation, citations, unsupported questions and concurrent browser sessions before sharing the URL.

## Local test on Windows

1. Install Docker Desktop and start its engine.
2. Download or clone this repository.
3. Open PowerShell in the repository directory.
4. Create the environment file:

   ```powershell
   Copy-Item .env.example .env
   ```

5. Start the application:

   ```powershell
   docker compose up --build
   ```

6. Open http://localhost:8501 in a browser.

The first run downloads container images, the embedding model and the Ollama model. It requires an internet connection and several GB of disk space. Later runs reuse the Docker volumes.

Stop the stack with:

```powershell
docker compose down
```

## Upload limit

The Streamlit uploader is configured for a maximum of 20 MB per file. Reverse proxies and hosting platforms may have their own request-body limits; configure those consistently. A per-file application limit does not guarantee that every host accepts a 20 MB request.

## Secrets

The primary Ollama configuration does not require a Gemini API key. If optional Gemini fallback is enabled, store its key in server-side environment variables or the host's secret manager. Never commit `.env`, API keys or credentials.

## Persistence and privacy

- Preserve the Docker volumes and the application's `data/` directory if data must survive container recreation.
- Configure backups and retention according to the demo's intended use.
- The current portfolio design is not a substitute for authentication, tenant isolation, encryption-at-rest or a production data-governance program.
- Use synthetic or public documents only in a public demo.

## Troubleshooting

- **Application import error:** verify that `src/doc_assistant/` is present in the repository and included in the Docker build context.
- **Ollama connection error:** inspect `docker compose logs ollama`; confirm the app uses `http://ollama:11434` from inside the Compose network.
- **Model not found:** inspect the model-init container logs and verify the configured model name.
- **Out of memory:** increase VM RAM or use a smaller/quantized model; review container memory limits.
- **Upload rejected:** check Streamlit's 20 MB limit and the reverse proxy's request-body limit.
