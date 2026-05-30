# Architecture Decisions

## 1. FastAPI over Flask

**Status:** Accepted
**Context:** Needed a Python web framework for an IoT backend that ingests sensor data and serves a React dashboard.

**Decision:** Use FastAPI.

**Consequences:**

- Auto-generated Swagger docs at `/docs` – an interactive, self‑documenting API that recruiters and collaborators can explore without setup.
- Pydantic validation catches malformed sensor data at the API boundary, preventing silent errors.
- Native async support leaves the door open for WebSocket streaming in the future.
- Slightly steeper learning curve than Flask, but the productivity gains and modern patterns are worth it for a real‑time IoT context.

---

## 2. PostgreSQL over SQLite

**Status:** Accepted
**Context:** Needed a database for time‑series sensor readings that will grow over time.

**Decision:** PostgreSQL, orchestrated via Docker Compose.

**Consequences:**

- Production‑grade performance and data integrity – the same database used in real wind farm SCADA systems.
- Timestamp indexing enables efficient queries on millions of historical readings.
- Docker Compose makes local setup a single command (`docker compose up`), removing installation friction.
- More operational overhead than SQLite, but SQLAlchemy ORM abstracts the difference in code.
- An SQLite fallback is kept for zero‑config local testing; the ORM makes swapping seamless.

---

## 3. Single‑Page React over Vanilla JS

**Status:** Accepted
**Context:** Needed a dashboard to display live turbine power output, RPM, temperature, and alerts.

**Decision:** React with Recharts, built as a single‑page application (no routing).

**Consequences:**

- React is the standard for product‑company dashboards, making this directly transferable to real teams.
- Component structure (`Dashboard`, `AlertPanel`, `StatusCard`) mirrors production patterns and allows future expansion without refactoring.
- Recharts provides declarative, real‑time‑capable charts that integrate naturally with React state.
- Higher complexity than vanilla JS, but the scope is limited to a single page, keeping the learning curve manageable.

---

## 4. Simplified Physics Model

**Status:** Accepted
**Context:** Needed to simulate turbine power output from wind speed in a way that is realistic enough to drive a monitoring dashboard, but not a full‑fidelity turbine model.

**Decision:** A simplified power curve with four distinct operating regions, based on the Enercon E‑82 (82 m rotor, 2 MW) specification.

**Why not the pure Betz formula:**
The pure Betz formula allows power to climb indefinitely with wind speed, which is physically impossible – real turbines cap output at their nameplate rating because the generator and gearbox are designed for a maximum power. Above rated wind speed, the blades actively pitch to shed excess wind and maintain constant output.

**Implemented regions:**

- Below cut‑in (3 m/s): **0 W** – not enough wind to overcome friction.
- Cut‑in to rated (3‑12 m/s): **Cubic ramp** using the Betz formula P = 0.5 × ρ × A × Cp × v³.
- At or above rated (12 m/s): **Fixed at 2 MW** – the turbine’s nameplate capacity.
- Above cut‑out (25 m/s): **0 W** – safety shutdown.

**Consequences:**

- Captures the four critical behaviours of a real power curve: cut‑in, cubic growth, rated cap, cut‑out.
- The rated power is a fixed design parameter, not derived from the formula – exactly how manufacturers specify turbines.
- A constant \( C_p \) is used as a simplification; a real turbine’s \( C_p \) varies with tip‑speed ratio. This is acknowledged and can be replaced with an empirical power curve from `windpowerlib` later without affecting the API or database.
- The model is trivially explainable and produces visually correct charts for the dashboard.
- Reference: [Enercon E‑82 power curve](https://en.wind-turbine-models.com/turbines/317-enercon-e-82-2.000)
