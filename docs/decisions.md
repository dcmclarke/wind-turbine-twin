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

## 4. Simplified Physics Model (E-82 Simulation)

**Status:** Superseded by Decision 5
**Context:** Originally modelled power output from a simulated Enercon E-82
(2MW, 82m rotor) using the Betz formula.

**Why superseded:** The project pivoted to ingesting real SCADA data from
the ETH Zurich Aventa AV-7 research turbine. Simulating power output from
a completely different turbine made the icing detector's power ratio
calculation meaningless — expected power from an E-82 model compared
against actual power from a 7kW AV-7 produces nonsense ratios.

---

## 5. Data-Derived Power Curve (AV-7)

**Status:** Accepted
**Context:** Need an expected power curve to calculate power ratio for
icing detection. The ratio actual/expected is the primary detection signal.

**Decision:** Fit a parametric curve to the AV-7's normal operation SCADA
data rather than using manufacturer constants or the Betz formula alone.

**AV-7 physical parameters (from ETH Zurich documentation):**

- Rated power: 7,000 W
- Cut-in speed: 2 m/s
- Cut-off speed: 14 m/s
- Rotor diameter: 12.8 m
- Max RPM: 63

**Consequences:**

- Expected power values are derived from the actual turbine's behaviour,
  not a theoretical model of a different machine.
- Cut-in and rated speed are identified from data, not assumed.
- The fitted coefficients are hardcoded after exploration in
  ingestion/explore.ipynb — reproducible and auditable.
- Limitation: fitted to one dataset from one turbine. Generalisation
  to other turbines requires recalibration.
