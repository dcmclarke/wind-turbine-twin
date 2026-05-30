# Architecture Decisions

## FastAPI over Flask

**Context:** Needed a Python web framework for an IoT backend.

**Decision:** FastAPI.

**Consequences:**

- Auto-generated Swagger docs at `/docs` — clickable demo for recruiters
- Pydantic validation catches malformed sensor data at the API boundary
- Async-ready for WebSocket upgrades later

## PostgreSQL over SQLite

**Context:** Needed a database for time-series sensor readings.

**Decision:** PostgreSQL via Docker Compose.

**Consequences:**

- Production-grade — same database real systems use
- Timestamp indexing scales to millions of readings
- Docker Compose makes local setup one command
- More setup than SQLite but SQLAlchemy ORM means code is identical

## Single-Page React over Vanilla JS

**Context:** Needed a dashboard to display live turbine data.

**Decision:** React with Recharts, single-page (no routing).

**Consequences:**

- Demos modern frontend skills to recruiters
- Component structure (Dashboard, AlertPanel, StatusCard) maps to real product patterns
- Recharts handles real-time data updates cleanly
- Higher complexity than vanilla JSbut manageable for single page

---

## Simplified Physics Model

**Context:** Needed to simulate turbine power output.

**Decision:** Betz limit formula (P = 0.5 × ρ × A × Cp × v³) instead of real power curves.

**Consequences:**

- Focuses scope on the data pipeline, not physics accuracy
- imple, explainable, testable
- Not physically accurate acknowledged. Can swap in windpowerlib power curves later (stretch goal).
