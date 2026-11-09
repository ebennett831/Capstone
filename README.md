# AI Lacrosse Coach

**A mobile-first capstone project for analyzing lacrosse movement from video.**

The goal is to let a player record or select a short lacrosse clip, submit it for analysis, and eventually receive useful, evidence-based feedback about shots, dodges, and movement sequences. We're building the system incrementally: first the mobile-to-backend connection, then video upload, computer vision, motion features, and finally machine learning where the data supports it.

> **Project status (November 9, 2026):** The Expo mobile app runs on an iPhone, the FastAPI backend exposes `GET /health`, and the mobile app can call that endpoint and show the connection status. **Video upload, pose estimation, movement recognition, and coaching feedback are not implemented yet.**

## Technology stack

| Part | Technology | Responsibility |
| --- | --- | --- |
| Mobile application | React Native, Expo, TypeScript, Expo Router | User interface, device interaction, API requests |
| Backend API | Python, FastAPI, Uvicorn | HTTP endpoints, validation, future analysis coordination |
| Python environment | uv | Project dependencies and reproducible virtual environment |
| Frontend dependencies | Node.js, npm | JavaScript/TypeScript tooling |
| Video processing (planned) | OpenCV, MediaPipe | Frame decoding and body landmark detection |
| Analysis (planned) | NumPy, SciPy, PyTorch | Motion features and evaluated models |
| Persistence (planned) | PostgreSQL; local files initially, later S3-compatible storage | Analysis metadata, results, and videos |

The repository is a **monorepo**: mobile and backend code live together but run as separate applications.

## Repository layout

```text
Capstone/
├── apps/
│   └── mobile/
│       ├── src/app/           # Expo Router screens and layouts
│       ├── src/components/    # Reusable UI components
│       ├── app.json           # Expo project configuration
│       └── package.json       # Frontend scripts and dependencies
├── services/
│   └── backend/
│       ├── src/backend/
│       │   └── main.py        # FastAPI application and /health route
│       ├── pyproject.toml     # Python project configuration
│       └── uv.lock            # Locked Python dependencies
├── docs/
│   ├── architecture.md       # Current and future system design
│   └── roadmap.md            # Milestones and acceptance criteria
├── .gitignore
└── README.md
```

## Running locally on Windows (Command Prompt)

### Prerequisites

- Git
- Node.js and npm
- Python (backend project currently specifies Python **3.13 or newer**)
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- A phone with Expo Go, or a compatible emulator/simulator

Use **two separate CMD terminals**: one for the Python backend and one for Expo. Commands below assume you've already cloned the repository and are in its root directory.

### 1. Start the backend

```cmd
cd services\backend
uv sync
uv run uvicorn backend.main:app --reload --host 0.0.0.0
```

The server will listen on port **8000**. On the development computer, open:

- `http://127.0.0.1:8000/health` — API health check
- `http://127.0.0.1:8000/docs` — FastAPI interactive API docs

Expected `/health` response:

```json
{
  "status": "ok",
  "service": "AI Lacrosse Coach API"
}
```

`--reload` watches for code changes. `--host 0.0.0.0` permits access over your local network; use it only on a trusted network and **do not port-forward the development server to the public internet**.

### 2. Find the computer's LAN address

In another CMD terminal, run:

```cmd
ipconfig
```

Find the `IPv4 Address` on your active Wi-Fi or Ethernet adapter, such as `192.168.1.105`. Your actual address will probably differ.

Make sure your phone is connected to the same local network. Before launching the app, try visiting the backend from your phone browser using **HTTP, not HTTPS**:

`http://YOUR_PC_IPV4:8000/health`

If it does not load, check the IP address, Windows Firewall's private-network access, and Wi-Fi network isolation.

### 3. Configure the mobile app

From a **new CMD terminal** at the repository root:

```cmd
cd apps\mobile
npm ci
```

Create a file named `apps/mobile/.env.local` with the following content, replacing the example address with your computer's actual LAN IPv4 address:

```dotenv
EXPO_PUBLIC_API_URL=http://192.168.1.105:8000
```

The file path is relative to the repository root; if you're already inside `apps/mobile`, create `.env.local` in that directory. The `.env.local` file is intentionally Git-ignored because it contains **machine-specific configuration**. A future `.env.example` will document required variable names without a real local address.

### 4. Start Expo

From `apps/mobile`:

```cmd
npx expo start
```

Open the app through **Expo Go** on your phone. On the home screen, press **Test Backend Connection**. The expected result is **Backend online** with the FastAPI service name.

If you change `.env.local`, restart Expo (for example `npx expo start --clear`). Keep the FastAPI terminal running while you test.

## How the apps communicate today

```text
Player taps "Test Backend Connection"
    ↓
React Native calls fetch(`${EXPO_PUBLIC_API_URL}/health`)
    ↓ HTTP GET over local Wi-Fi
FastAPI executes the /health handler
    ↓ JSON response
React Native updates its connection status on screen
```

The frontend knows the **API contract**, not how the backend is implemented internally. Future video upload and results requests will follow the same separation of responsibilities.

## Development workflow

1. Pick a small feature from [the roadmap](docs/roadmap.md).
2. Understand the request/response flow and write the simplest working version.
3. Run it manually; add automated tests appropriate to the feature.
4. Document decisions or pitfalls in [the architecture notes](docs/architecture.md).
5. Review `git status`, commit, and push only intended source and configuration files.

Useful checks (after the relevant tooling/tests are added):

```cmd
:: from apps\mobile
npx tsc --noEmit

:: from services\backend, after adding pytest as a dev dependency
uv run pytest
```

**Automated backend tests and CI are part of the remaining Milestone 1 cleanup; they are not in the initial commit.**

## Data, privacy, and limitations

- Do not commit `.env.local`, credentials, `.venv/`, `node_modules/`, generated output, athlete videos, or datasets.
- Only process videos you have permission to use. Plan for deletion/retention rules before collecting real athlete data.
- Early motion measurements are **prototypes**. A single phone camera cannot directly measure true 3D stick motion or accurately infer physical speed without calibration.
- Do not present invented technique or explosiveness scores as validated coaching results.

## Project documentation

- [Roadmap & milestones](docs/roadmap.md)
- [Architecture & engineering decisions](docs/architecture.md)

The longer-term vision includes computer vision, lacrosse stick tracking, movement classification, technique feedback, and progress history. These will be built and evaluated in stages—not all at once.
