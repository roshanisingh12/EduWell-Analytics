# EduWell Analytics

**EduWell Analytics** is a statistical research suite and web dashboard for analyzing student lifestyle behaviors, time allocation, stress indicators, and academic performance (cumulative GPA).

Built with **FastAPI** on the backend and **Vanilla HTML/CSS/JavaScript (Calm Vitality design system)** on the frontend.

---

## Features

- **Automated Data Cleaning Pipeline:** Ingestion, schema validation (8 required columns), duplicate removal, ordinal encoding, and Tukey IQR outlier audits.
- **Parametric & Non-Parametric Statistics:** Central tendency (Mean, Median, Skewness, IQR), one-way ANOVA with $\eta^2$ effect sizes across stress cohorts.
- **Multivariate Correlation Analysis:** Pearson linear and Spearman rank correlation matrices, ordinary least squares (OLS) regressions, and partial correlation analysis isolating study hours as a key confounder between stress and GPA.
- **Visual Analytics:** Interactive frequency distributions, stress tier donut visualizations, 24-hour daily time budget allocations, and Matplotlib figure generation.
- **Export Formats:** Plaintext executive report, cleaned dataset CSV, descriptive statistics CSV, full structured JSON, and a bundled ZIP archive with publication-ready charts.

---

## Project Structure

```
├── analysis_service.py         # Statistical analysis, data cleaning & figure rendering engine
├── generate_sample_data.py     # Deterministic 2,000-student synthetic dataset generator
├── main.py                     # FastAPI application, routing, middleware & lifecycle
├── session_store.py            # In-memory session management with automated TTL pruning
├── settings.py                 # Runtime configuration and environment variable loading
├── student_lifestyle_analysis.py # Core analytical routines and statistical models
├── student_lifestyle_dataset.csv # Bundled synthetic baseline dataset
├── test_api.py                 # Comprehensive 12-point automated integration test suite
├── frontend/                   # Web dashboard SPA
│   ├── index.html              # Dashboard shell and semantics
│   └── assets/
│       ├── app.css             # Calm Vitality design system CSS
│       ├── app.js              # SPA router, API client, charts & view renderers
│       ├── theme.js            # Pre-paint theme synchronization (Light/Dark mode)
│       └── logo.svg            # Institutional application branding
├── requirements.txt            # Pinned production Python dependencies
├── Dockerfile                  # Production container definition (Python 3.12-slim, non-root)
├── docker-compose.yml          # Container orchestration with healthchecks
├── Procfile                    # PaaS deployment command (Render, Railway, Heroku)
├── render.yaml                 # Infrastructure-as-code blueprint for Render
├── .env.example                # Configuration template
└── .gitignore                  # Git exclusion rules
```

---

## Quick Start (Local Development)

### 1. Prerequisites
- Python 3.10+ (Python 3.12 recommended)
- `pip` package manager

### 2. Setup Virtual Environment
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Run the Application
```bash
python main.py
```
Open **[http://127.0.0.1:8000](http://127.0.0.1:8000)** in your browser.

- **Dashboard:** `http://127.0.0.1:8000/`
- **Swagger UI (Interactive API Docs):** `http://127.0.0.1:8000/docs`
- **Health Check Endpoint:** `http://127.0.0.1:8000/api/health`

### 4. Run Automated Tests
```bash
python test_api.py
```

---

## Deployment Options

### Option A: Docker Deployment (Recommended)

Build and run using the optimized, non-root container image:

```bash
# Build the Docker image
docker build -t eduwell-analytics:latest .

# Run the container
docker run -d --name eduwell -p 8000:8000 eduwell-analytics:latest
```

Or using **Docker Compose**:
```bash
docker compose up -d
```

### Option B: Deploy to Render

1. Create a new repository on GitHub and push the codebase.
2. Log in to [Render](https://render.com/) and click **New > Blueprint**.
3. Select your repository. Render automatically reads [render.yaml](render.yaml), installs dependencies, configures health checks, and launches the service.

Alternatively, create a **Web Service** manually on Render:
- **Environment:** `Python 3`
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT --workers 1 --proxy-headers`
- **Health Check Path:** `/api/health`

### Option C: Deploy to Railway / Heroku

The included [Procfile](Procfile) is automatically detected:
```bash
web: uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --proxy-headers
```

Set environment variable `COOKIE_SECURE=true` in production when running behind HTTPS.

### Option D: Google Cloud Run / AWS ECS

Deploy the container directly to serverless container platforms:
```bash
# Google Cloud Run example
gcloud run deploy eduwell-analytics \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8000
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `PORT` | `8000` | Port for Uvicorn HTTP server |
| `HOST` | `127.0.0.1` | Network interface (`0.0.0.0` in Docker/PaaS) |
| `LOG_LEVEL` | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `MAX_UPLOAD_MB` | `25` | Maximum CSV upload file size |
| `MAX_ROWS` | `100000` | Maximum record count per upload |
| `SESSION_TTL_MINUTES`| `120` | Session lifetime before purging idle memory |
| `MAX_SESSIONS` | `200` | Maximum active in-memory user sessions |
| `COOKIE_SECURE` | `false` | Require `Secure` flag on session cookies (set `true` in HTTPS production) |
| `ENABLE_DOCS` | `true` | Expose OpenAPI documentation at `/docs` |
| `CORS_ORIGINS` | `""` | Comma-delimited list of allowed origin URLs |

*(Variables can be prefixed with `EDUWELL_`, e.g. `EDUWELL_PORT`)*.

---

## Security & Architecture

- **Session Isolation:** Each visitor is assigned an isolated session token via `SameSite=Lax`, `HttpOnly` cookies. Uploaded datasets are never visible to other users and are purged after inactivity.
- **Content Security Policy (CSP):** Strict CSP headers (`default-src 'self'`) prevent cross-site scripting and resource hijacking.
- **Zero-Imputation Policy:** Data cleaning explicitly preserves statistical fidelity; records with corrupted or missing values are dropped rather than imputed.
- **Reverse Proxy Header Support:** `--proxy-headers` correctly resolves client IPs and protocols when operating behind AWS ALB, Cloudflare, NGINX, or Render.
