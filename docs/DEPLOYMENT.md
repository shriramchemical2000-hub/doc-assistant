# Deployment and operator guide

This guide is for the project owner. **Recruiters and visitors only need a browser. They do not install Python, Docker, Linux, Ollama or an API key.**

## Recommended free deployment

Use Streamlit Community Cloud for the public app and the Gemini API free tier for answer generation. The hosted app does not start an Ollama server.

### 1. Create a Gemini API key

1. Open [Google AI Studio](https://aistudio.google.com/apikey).
2. Create an API key in a project that is on the Gemini API Free Tier.
3. Keep the key private. Do not paste it into GitHub, source files, screenshots or public messages.

Gemini free-tier models and quotas vary. Check the active limits in AI Studio and the [official pricing page](https://ai.google.dev/gemini-api/docs/pricing). If a request hits a quota or service error, DocuMind falls back to showing retrieved passages.

### 2. Deploy the GitHub repository

1. Open [Streamlit Community Cloud](https://share.streamlit.io/).
2. Sign in with GitHub and authorize access to the public repository.
3. Select **Create app**.
4. Choose repository: `shriramchemical2000-hub/doc-assistant`.
5. Choose branch: `main`.
6. Set the app file path to: `app.py`.
7. Open **Advanced settings** and choose Python 3.11 if available.
8. In the **Secrets** field, add the following TOML (replace the placeholder locally in the Streamlit settings; do not commit it):

   ```toml
   GEMINI_API_KEY = "PASTE_YOUR_PRIVATE_KEY_HERE"
   GEMINI_MODEL = "gemini-3.8-flash"
   OLLAMA_ENABLED = "false"
   ```

9. Click **Deploy** and wait for the build to finish.
10. Open the generated `*.streamlit.app` URL and test the complete upload → index → ask → source evidence flow.

Official instructions: [Deploy a Streamlit app](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy) and [manage secrets](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management).

### 3. Important free-hosting constraints

- Community Cloud is free, but its CPU, memory and storage limits can change. The published limits are approximately 2.7 GB RAM maximum; monitor app health and logs.
- Apps without traffic for 12 hours are hibernated. A visitor can wake the app, so the first visit after inactivity may take longer.
- The embedding model is downloaded and loaded by the app. Initial startup can be slow and may approach the platform's memory limits.
- Local app storage is not a durable database. Treat uploaded documents as temporary demo data.
- Gemini free-tier requests have model-specific rate limits. They are not unlimited, and Google can change quotas or model availability.
- Google states that free-tier Gemini API content may be used to improve its products. Use synthetic/public documents only; never upload confidential employer, customer or personal records.
- This free setup is suitable for a portfolio demonstration, not a production service with uptime, privacy or throughput guarantees.

### 4. Verify the public demo before sharing

- App opens without asking the visitor to sign in.
- Upload a PDF, DOCX and TXT file.
- Confirm the 20 MB per-file application limit.
- Ask a question whose answer exists in the sample document.
- Confirm Gemini returns an answer with valid [S1], [S2] source references.
- Ask a question not answered by the document and confirm the app does not invent an answer.
- Confirm source passages and page metadata are visible.
- Check app logs for memory, dependency or API quota errors.

Only after these checks pass should the public URL be added to the README and shared with recruiters.

## Local development with Ollama (optional)

Ollama remains available for local development or a separately hosted Docker deployment. It is not required for the free Community Cloud app.

1. Install Docker Desktop on Windows or Docker Engine and Compose on Linux.
2. Clone the repository and enter its directory.
3. Copy the example environment file:

   ```bash
   cp .env.example .env
   ```

4. Start the stack:

   ```bash
   docker compose up --build
   ```

5. Open http://localhost:8501.

The Compose configuration explicitly enables Ollama and downloads the configured model. The first run needs an internet connection and several GB of disk space.

## Upload limit

The Streamlit uploader is configured for a maximum of 20 MB per file. Hosting platforms may impose additional request-size limits, so verify the upload flow after deployment.

## Secret handling

- Store the Gemini key only in Streamlit Community Cloud Secrets or a local untracked `.env` file.
- Never commit API keys, `.env` or `.streamlit/secrets.toml`.
- If a key is accidentally exposed, revoke it in Google AI Studio and create a replacement.

## Troubleshooting

- **App fails during startup:** inspect Streamlit Cloud logs for dependency or memory errors.
- **Gemini quota error:** check the project's active free-tier limits in AI Studio; the app should show evidence-only output when generation is unavailable.
- **No Gemini answer:** verify the secret names and model name; restart/redeploy after changing secrets.
- **Memory/resource warning:** reboot the app, check logs and consider a lighter embedding implementation if the model exceeds the free host's limits.
- **Upload rejected:** confirm file size is within 20 MB and check the platform's request-size limits.
