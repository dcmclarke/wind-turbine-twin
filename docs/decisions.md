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

## 6. Temperature Gate Removed

**Status:** Accepted
**Context:** The original IEA T19 detection plan included a temperature gate —
only flag icing alerts when ambient temperature is near freezing (≤ 2°C).

**Decision:** Remove the temperature gate entirely.

**Why:** Dataset exploration revealed the AV-7's ATM_TEMP_01 sensor
malfunctions throughout the entire dataset. Values are physically impossible
(81°C in December, -1,000,000°C sentinel values). Three options were
considered:

- Use broken data — silently corrupts the detector
- Substitute a proxy (nacelle temperature) — introduces unvalidatable assumption
- Remove the gate and document the limitation — honest and auditable

The third option was chosen. The power ratio signal alone produces a clear
detectable anomaly during the icing event (ratio = 0.0 vs expected ~2.3 kW).

**Consequences:**

- Detector relies solely on power ratio and persistence filter
- False positive rate is higher than it would be with a working temperature gate
- Limitation documented in README and evaluation results
- In a production deployment with a working temperature sensor, the gate
  should be re-enabled

---

## 7. Singleton Detector Instance

**Status:** Accepted
**Context:** The IcingDetector maintains a rolling window of recent power
ratios as internal state. Both the telemetry route and the icing status
route need access to the same window state.

**Decision:** One IcingDetector instance created in detector/instance.py
and imported by both routes.

**Consequences:**

- Both routes share one coherent view of detector state — correct behaviour
- If FastAPI restarts, the rolling window resets to empty
- Not thread-safe under concurrent requests
- In production: persist window state to Redis so restarts are invisible
- Acceptable trade-off for a portfolio project — documented, not hidden

---

## 8. Ratio Threshold Set to 0.1 After Quantitative Sweep

**Status:** Accepted
**Context:** The power ratio threshold determines when a reading is counted
as underperforming. Initial value was 0.5 (50% of expected power).

**Decision:** Lower threshold to 0.1 after a quantitative sweep.

**Method:** Swept thresholds from 0.1 to 0.9 against the full labeled
dataset. Measured precision and recall at each value.

**Findings:**

- Recall is 1.000 across all thresholds — the icing signal (ratio = 0.0)
  is unambiguous regardless of threshold
- Precision improves significantly at lower thresholds
- At 0.1: precision = 0.950, recall = 1.000, F1 = 0.974 (on filtered data)
- Final evaluation against full dataset: precision = 0.757, recall = 1.000

**False positive investigation:**

- 60.8% of false positives occur below 3.0 m/s wind speed
- A minimum wind speed filter of 3.0 m/s was considered
- Rejected: 75.7% of the actual icing event also occurs below 3.0 m/s
- The low wind speed zone is simultaneously the noisiest and most relevant
  region for this icing event — a filter would eliminate three quarters of recall

**Consequences:**

- Threshold choice is data-driven and quantitatively justified
- False positives represent inherent power curve noise at low wind speeds
- This is the known confounding problem in SCADA-based icing detection,
  documented in the literature (ScienceDirect 2024)
- Threshold sweep plot saved in ingestion/threshold_sweep.png
