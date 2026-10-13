# Design Decisions

Each entry records the context, the choice, and what it costs. Superseded
decisions stay in the log so the reasoning behind changes is visible.

| # | Decision | Status |
| --: | :-- | :-- |
| 1 | FastAPI over Flask | Accepted |
| 2 | PostgreSQL, SQLite for local runs | Accepted |
| 3 | React single-page dashboard | Accepted |
| 4 | Simulated Enercon E-82 physics | Superseded by 5 |
| 5 | Power curve from the AV-7's own data | Superseded by 9 |
| 6 | Temperature condition not applied | Accepted, revised |
| 7 | In-memory singleton detector | Superseded by 11 |
| 8 | Ratio threshold 0.1 from a sweep | Withdrawn, see 12 |
| 9 | 10-minute data and the IEA Task 19 method | Accepted |
| 10 | Reference curve only where there is data | Accepted |
| 11 | Detector state saved with every reading | Accepted |
| 12 | Held-out, event-level evaluation against a baseline | Accepted |
| 13 | MQTT with edge aggregation | Accepted |
| 14 | Hosted demo replays in-process | Accepted |

---

## 1. FastAPI over Flask

**Context:** A Python web framework for a service that ingests sensor data and serves a dashboard.

**Decision:** FastAPI.

**Consequences:**

- Pydantic models validate every reading at the boundary (HTTP and MQTT share the same `ReadingIn` schema), so a malformed message is rejected before it reaches the detector.
- Interactive API docs at `/docs` with no extra work.
- The detector itself has no FastAPI code, so the evaluation and tests run it directly.

---

## 2. PostgreSQL, SQLite for local runs

**Context:** Time-ordered readings and events that must survive restarts, written by one process and read by the dashboard.

**Decision:** PostgreSQL in Docker Compose and in the hosted demo (Neon); SQLite when the backend runs on its own with no `DATABASE_URL`.

**Consequences:**

- `scada_readings.timestamp` is unique and indexed: the index serves the "latest N readings" query, and uniqueness makes duplicate MQTT deliveries harmless (Decision 13).
- The database URL is rewritten to name the driver (`postgresql+psycopg://`). SQLAlchemy 2.1 changed which driver a bare `postgresql://` URL uses, which crashed the backend on its first full-stack run.
- Tables are created with `create_all`. There are no migrations; the new table names (Decision 11) avoid clashing with version 1's tables in an existing database.

---

## 3. React single-page dashboard

**Context:** A dashboard showing the detector's state as readings arrive.

**Decision:** React + TypeScript with Recharts and Tailwind, one page, polling one `/api/dashboard` endpoint every 2 seconds.

**Consequences:**

- One request returns status, recent readings and events, so the panels always agree with each other.
- Polling is simpler than WebSockets and fast enough at one new reading every 2 seconds. It would not suit sub-second data.

---

## 4. Simulated Enercon E-82 physics

**Status:** Superseded by Decision 5.

The project started by simulating a 2 MW Enercon E-82 with the Betz formula. Once real data from the 7 kW Aventa AV-7 was in use, comparing its output against a model of a different turbine produced meaningless ratios.

---

## 5. Power curve from the AV-7's own data

**Status:** Superseded by Decision 9.

Version 1 used a lookup table of mean power per 0.5 m/s bin, from ~873,000 raw ~7 Hz readings. Using the turbine's own data was right; using means of raw readings and a single expected value was replaced by Task 19's percentile curve on 10-minute data.

---

## 6. Temperature condition not applied

**Status:** Accepted, revised.

**Context:** Task 19 only raises icing alarms below +1 °C and builds its reference from data above +3 °C. The AV-7's only ambient temperature channel reads around 81 °C in December and −1,000,000 in places, for the whole dataset.

**Decision:** The detector implements the temperature condition (`Sample.temperature`, `T19Config.icing_temperature`) and applies it whenever a reading carries a temperature. The bundled dataset carries none, so on this data the condition is skipped. The alternatives were to use the broken values, or substitute an untested proxy such as nacelle temperature.

**Consequences:**

- On this data the detector cannot tell ice from any other cause of low output. All six false events in the evaluation happened on 20 June; with a working sensor the condition would have removed them.
- The clean reference comes from the dataset's own labelling of clean-blade days, not from a temperature filter.

---

## 7. In-memory singleton detector

**Status:** Superseded by Decision 11.

Version 1 kept the detector's rolling window in a module-level object. Every restart emptied it, and the hosted backend restarts each time the free tier wakes up, so the live demo showed "NORMAL" next to an active icing event.

---

## 8. Ratio threshold 0.1 from a sweep

**Status:** Withdrawn. See Decision 12.

Version 1 picked the threshold from a sweep over 0.1–0.9 on the same data it then reported results on. Recall was 1.000 at every threshold because every "icing" reading had zero output, so the sweep could only trade precision and said nothing about detecting ice.

---

## 9. 10-minute data and the IEA Task 19 method

**Context:** Icing detection from SCADA data needs a defensible method, and the IEA Wind Task 19 method is the published standard for it ([T19IceLossMethod](https://github.com/IEAWind-Task19/T19IceLossMethod)).

**Decision:** Aggregate the raw data into 10-minute statistics and follow Task 19:

- A reference curve of P10, P50 and P90 per 0.5 m/s wind bin, from clean-blade readings where the turbine was generating and producing at least 1% of rated power.
- Flags per reading: below P10 while producing (A), below 1% of rated when P50 is above 0.5% of rated (B, stopped), above P90 (C).
- An event needs 3 consecutive readings for A and C, and 6 for B. Consecutive means at most 660 seconds apart; the AV-7 logs every 601 s, so Task 19's strict "< 601 s" would treat every pair as a gap.
- Events are back-dated to the first reading of the run and end at the first reading without the flag.
- Energy lost is the shortfall against P50, summed over the event's readings.

**Differences from the reference implementation:**

- **Streaming.** Readings arrive one at a time, so the B test cannot use the batch implementation's look-ahead window.
- **No wind-direction bins.** The reference implementation's example also uses a single 360° bin.
- **No air-density correction.** The correction needs temperature (Decision 6).

**Consequences:**

- Alarms come an hour after a stop begins, by design. The zero-output baseline alarms in 10 minutes.
- 916 readings instead of millions: the dataset is small enough to commit, and the whole evaluation runs in CI.

---

## 10. Reference curve only where there is data

**Context:** Task 19 drops bins with fewer than 36 samples (six hours of data, assuming a year of history). The public AV-7 data has 187 clean generating readings, most between 2 and 4.5 m/s; above 4.5 m/s no bin has more than four.

**Decision:** Minimum 10 samples per bin. The curve covers the outer edges of its valid bins (1.76–4.19 m/s). Outside that, readings are flagged "no reference" and never judged; inside, values are interpolated between bin medians.

**Consequences:**

- Most readings are not judged: 62% of clean readings (313 of 503) and 81% of the icing period (334 of 413), which was mostly calm.
- The detector never compares a reading at 8 m/s against a curve that only knows 4 m/s.
- With 10-sample bins the P10/P90 estimates are rough. More data would tighten them.

---

## 11. Detector state saved with every reading

**Context:** The detector must remember the current run and any active event between readings, across restarts (Decision 7).

**Decision:** `DetectorState` serialises to JSON. Ingestion loads it, processes the reading, then writes the reading, any event changes and the new state in one transaction. A lock allows one writer at a time.

**Consequences:**

- A restart resumes exactly where it stopped. A test checks that a detector restored mid-stream produces the same results as one that never stopped.
- If any part of a write fails, none of it is saved, so the stored events and the detector's state can't disagree.
- The lock serialises writes. That is plenty for one turbine sending one reading every 10 minutes; a wind farm would need state per turbine rather than one global detector.

---

## 12. Held-out, event-level evaluation against a baseline

**Context:** Version 1's recall of 1.000 was circular (Decision 8). A useful evaluation had to answer three questions: does the detector find real ice, how often does it cry wolf, and does it beat something trivial?

**Decision:**

- Clean days use leave-one-day-out: each day is judged against a curve fitted without it.
- Results are counted in events, not readings, because there is one icing event.
- A zero-output rule is the baseline.
- CI reruns the evaluation and fails if any result changes.

**Consequences:**

- The results are less flattering and harder to argue with: 1 of 1 icing events found, 6 false events on 1 of 11 clean days, against 12 on 6 days for the baseline.
- `legacy_comparison.py` reproduces version 1's numbers and shows the zero-output rule matching them.

---

## 13. MQTT with edge aggregation

**Context:** A turbine sits on a site network, not next to the database. Its data has to cross an unreliable link.

**Decision:** An edge gateway publishes one 10-minute summary per message to an MQTT broker with QoS 1. The backend subscribes with a persistent session (`clean_session=False`).

**Consequences:**

- Sending one summary instead of ~4,200 raw readings per 10 minutes cuts traffic by that factor, and the summaries are what the detector uses anyway.
- QoS 1 is at-least-once, so a reading can arrive twice. Ingestion ignores a second reading with the same timestamp.
- While the backend is down, the broker queues readings for it. This was tested by stopping the backend mid-stream: no readings were lost.
- The local broker allows anonymous connections inside the Compose network. A site deployment would need TLS and per-device credentials.

---

## 14. Hosted demo replays in-process

**Context:** The free hosting tier runs a single web service with no MQTT broker, and sleeps when idle.

**Decision:** With `INGEST_MODE=demo`, a background thread replays the bundled dataset through the same ingestion code the MQTT subscriber uses. Each loop clears the tables, loads everything before 4 November 2022 in one transaction, then streams one reading every 2 seconds (300× real time), so a visitor sees history immediately and the icing event within about a minute.

**Consequences:**

- The dashboard is honest about it ("Replaying recorded 2022 data · 300× speed").
- Every cold start restarts the replay. The data is a recording, so nothing is lost.
- Clearing the tables on every loop is destructive, so demo mode is opt-in: the default `INGEST_MODE` is `none`, and the hosted backend sets `demo` explicitly.
- `POST /api/readings` is off unless `ALLOW_HTTP_INGEST=true`, so the public demo can't be fed made-up data.
