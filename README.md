# ULPF — Universal Log Pre-processing Framework

ULPF can be run locally using **Docker Compose** (recommended) or configured **manually** for development.

## 🐳 Quick Start (Docker)

**Prerequisites:** Docker and Docker Compose.

1. Open your terminal and navigate to the project root:
```bash
cd ULPF

```


2. Build and start the stack:
```bash
docker compose up --build

```


3. To stop the project, press `Ctrl + C` or run `docker compose down`.

---

## 🌐 Service URLs

Once the services are running, access them via your browser:

| Service | URL | Credentials |
| --- | --- | --- |
| **Frontend** | http://localhost:5173 | - |
| **Backend API** | http://localhost:8000 | - |
| **API Health Check** | http://localhost:8000/api/v1/health | - |
| **Swagger API Docs** | http://localhost:8000/docs | - |
| **MinIO Console** | http://localhost:9001 | **User:** `ulpfadmin` <br>

<br> **Pass:** `ulpfadminsecret` |

*Note: Change MinIO credentials before any real deployment.*

---

## 🛠 Manual Local Setup

If you prefer not to use Docker, you will need **Python 3.11+** and **Node.js + npm**. Run the backend and frontend in separate terminal windows.

### Terminal 1: Backend

```bash
cd ULPF/backend

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies and run the server
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

```

### Terminal 2: Frontend

```bash
cd ULPF/frontend

# Install dependencies and start the dev server
npm install
npm run build
npm run dev

```

---

## 🧪 Running Backend Tests

ULPF includes an API test suite using `pytest`. Ensure your virtual environment is active and run the following from the backend directory:

```bash
cd ULPF/backend
python -m pytest -q

```

---

## 📂 Project Structure

* **`backend/`**: FastAPI application, including routes (`app/api/`), parsers (`app/parsers/`), and tests (`tests/`).
* **`frontend/`**: React application source (`src/`) and assets.
* **`docker-compose.yml`**: Docker service configurations.
* **`samples/`**: Sample security logs for testing.

---

## ⚠️ Troubleshooting

* **Port already in use:** If ports `8000`, `5173`, or `9001` are occupied, stop the conflicting service before starting ULPF.
* **Backend dependencies or pytest fails:** Ensure you are in the `ULPF/backend/` directory and your virtual environment (`venv`) is activated.
* **Docker services won't start:** Try forcing a clean rebuild without cache:
```bash
docker compose down
docker compose build --no-cache
docker compose up

```

Project Structure

The important directories are:

ULPF/
│
├── backend/
│   ├── app/
│   │   ├── api/             # API routes/endpoints
│   │   ├── core/            # Configuration and core utilities
│   │   ├── models/          # Database models
│   │   ├── schemas/         # Pydantic/API schemas
│   │   ├── services/        # Application/business services
│   │   ├── parsers/         # Log format parsers
│   │   ├── detection/       # Format detection
│   │   ├── normalization/   # CSE normalization
│   │   ├── enrichment/      # Security enrichment
│   │   ├── validation/      # Event validation
│   │   ├── quarantine/      # Failed/invalid event handling
│   │   ├── replay/          # Event replay functionality
│   │   ├── audit/           # Audit logging
│   │   └── main.py          # FastAPI application entry point
│   │
│   ├── tests/               # Backend/API tests
│   ├── requirements.txt     # Python dependencies
│   └── venv/                # Local Python virtual environment
│
├── frontend/
│   ├── src/                 # React application source
│   ├── public/              # Static frontend assets
│   ├── package.json         # Node dependencies/scripts
│   └── ...
│
├── samples/                 # Sample security logs
├── scripts/                 # Utility/automation scripts
├── docs/                    # Project documentation
│
├── docker-compose.yml       # Docker service configuration
├── .env.example             # Example environment configuration
├── .gitignore
└── README.md

