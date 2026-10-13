# Review fixes (branch `cleanup/review-fixes`)

A cleanup pass following a code review. Each change is one commit, has a
test where it fixes a bug, and leaves every test passing.

**Before you merge:** the hosted backend on Render must have
`INGEST_MODE=demo` set as an environment variable. The default changed from
`demo` to `none` (commit 9 below). Without it, the live demo starts but never
replays any data.

## How it was checked

| | Before | After |
| :-- | :-- | :-- |
| Backend tests (pytest) | 39 passed | 50 passed, on SQLite and on PostgreSQL 17 |
| Frontend | lint + build, no tests | lint + 3 Vitest tests + build |
| Evaluation `--check` | matches | matches (metrics.json regenerated in commit 15) |

Run locally on Python 3.14.5 (the repo's `.venv`) and Node 22.22. CI uses
Python 3.12. Beyond the unit tests, three things were checked by hand:

- **Full Docker Compose stack** (PostgreSQL, Mosquitto, backend, edge
  publisher): the backend reports healthy only after subscribing. With
  PostgreSQL stopped for 50 s mid-stream, or the backend stopped for 40 s,
  every reading ended up stored, in CSV order, with no gaps.
- **Broker persistence:** queued a QoS 1 message for an offline persistent
  subscriber, restarted Mosquitto, and the message was still delivered.
- **Dashboard freeze:** in the browser, through a proxy that could be made
  to stop answering. The header switched to "connection lost, retrying"
  within about 10 s, and recovered once the proxy answered again.

## The commits

### 1. Reject timezone-aware timestamps (`7653cef`)

**What was wrong:** `ReadingIn.timestamp` was a plain `datetime`, so
`2022-12-17T16:00:00Z` was accepted. Every stored timestamp is naive (the
turbine's own clock, no timezone). The detector checks that each reading is
newer than the last one, and Python refuses to compare naive with aware
datetimes, so it raised `TypeError`. Over HTTP that was a 500; over MQTT the
reading was dropped. The worst case was an aware reading arriving first after
a reset. It was saved in the detector's state, and then every normal reading
after it crashed.

**What changed:** the field is now Pydantic's `NaiveDatetime`, so an aware
timestamp is a validation error (422) before it reaches the detector.

**Why reject instead of converting to UTC?** The stored timestamps aren't UTC.
They're the turbine's local clock, and the dataset doesn't record which zone
that is. Converting `16:00+01:00` to `15:00` UTC and storing it next to
local-clock readings would put it on a different clock. The ordering and gap
checks would then be quietly wrong by an hour or two. Rejecting it is loud and
honest. The edge publisher already sends naive timestamps, so nothing
legitimate is affected.

**Tests:** aware timestamps (`+00:00` and `Z`) get 422; an aware reading
after a naive one gets 422, not a crash; a rejected aware reading doesn't
break the next normal one.

### 2. Acknowledge MQTT messages only after saving (`f4794c1`)

**What was wrong:** with QoS 1, paho acknowledges a message to the broker as
soon as `on_message` returns. `on_message` caught every exception and logged
it. So when saving failed (for example, the database was down), the message
was still acknowledged, the broker deleted it, and the reading was gone.

**What changed:** the client is created with `manual_ack=True` (supported in
the pinned paho-mqtt 2.1.0). `_on_message` calls `client.ack()` itself after a
successful save. It also acks messages that could never be saved (malformed,
duplicate, out of order), because redelivering those would never help.

**Tests:** a fake client records acks. A saved reading is acked, a failed save
is not, and malformed/duplicate/out-of-order readings are acked.

### 3. Persist the broker's queue to disk (`93f7726`)

**What was wrong:** `mosquitto.conf` had `persistence false`. The backend uses
a persistent session, so the broker queues readings for it while it's down.
But that queue only lived in memory, and a broker restart lost it.

**What changed:** `persistence true`, stored in a named Docker volume.

**Tests:** checked by hand (see above). It's broker config, so there's no unit
test.

### 4. Health check waits for the MQTT subscription (`2f8a652`)

**What was wrong:** the edge publisher slept 3 seconds "to give the backend a
moment to subscribe". The broker drops messages published to a topic before
anyone has ever subscribed to it. On a slow start, the first readings were
lost.

**What changed:** the MQTT feed records when the broker confirms its
subscription (`on_subscribe`). `/health` returns 503 until then. Docker
Compose already starts the publisher only when the backend is healthy, so the
sleep was removed. In demo and none modes, `/health` behaves as before.

**Tests:** `/health` returns 503 before the subscription is confirmed and 200
after.

### 5. Wait out a database outage instead of skipping (`709dbee`)

**What was wrong:** commit 2 wasn't enough. It failed my own end-to-end test.
With PostgreSQL stopped for 50 s, about 12 readings failed and stayed unacked.
But the backend carried on reading newer messages. MQTT 3.1.1 brokers only
redeliver unacked messages after a reconnect. By then, newer readings were
stored and the old ones were rejected as out of order, which left a gap.

**What changed:** if saving fails with `OperationalError` (SQLAlchemy's error
for "can't reach the database"), the feed retries the same reading every 5 s.
While it waits, paho reads no other messages, so the broker keeps them queued
in order. If the wait outlasts the MQTT keepalive, the broker drops the
connection. That's fine: on reconnect it redelivers the same reading (now a
harmless duplicate) and then the rest. Any other error, such as a bug, is still
logged and not retried, so one bad reading can't stall the feed forever.
Shutdown interrupts the wait.

**Tests:** a fake `ingest` raises `OperationalError` twice, then works. The
reading is saved and acked exactly once. Re-running the 50 s outage in Docker
gave no gaps.

### 6. Time out dashboard requests (`0ece43f`)

**What was wrong:** `usePolling` skips a tick while a request is in flight, so
slow requests don't stack up. But `fetch` has no timeout. One request that
never answered held the in-flight flag forever, and the dashboard stopped
updating. It still showed the green "updated" dot, because no error was ever
set.

**What changed:** a small `fetchJson(url, timeoutMs)` in `lib/api.ts` uses
`AbortSignal.timeout` (a one-line `AbortController` with a timer) and turns
the timeout into the error "Request timed out". The hook uses a 10 s timeout.
The header already shows any error as "connection lost, retrying" with an
amber dot.

**Tests:** added Vitest (dev-only) and three tests for `fetchJson`: a hung
request times out, an error status is rejected, and JSON is returned. CI now
runs `npm test`.

### 7. Duplicates across processes: 409 instead of 500 (`466234e`)

**What was wrong:** `ingest()` checks "is this timestamp already stored?" and
then inserts, under a `threading.Lock`. The lock only covers one process. Two
workers could both pass the check. The database's unique constraint on
`timestamp` (which already existed) then rejected the second commit with
`IntegrityError`. That surfaced as a 500, or over MQTT as a message that
failed and was never acked.

**What changed:** `ingest()` catches `IntegrityError`, rolls back and checks
again. If the timestamp is now stored, it raises `DuplicateReading` (409), the
same as the normal path. Any other integrity error still propagates rather
than being mislabelled as a duplicate.

**Tests:** a test simulates the race by inserting the same reading from a
second session between the check and the commit, and expects 409.

### 8. CI runs the backend tests on PostgreSQL too (`c0b02e8`)

**What was wrong:** production uses PostgreSQL but CI only tested SQLite.
That's how the psycopg driver crash got through earlier.

**What changed:** the backend CI job is a matrix (SQLite, PostgreSQL) with a
PostgreSQL 17 service container. `conftest.py` uses `TEST_DATABASE_URL` when
set. It deliberately never uses `DATABASE_URL`, because the tests delete every
row, and a developer's real `DATABASE_URL` must never be wiped by `pytest`.

**Note:** the CI job names are now "Backend tests (SQLite)" and "Backend
tests (PostgreSQL)". If branch protection requires "Backend tests", update it.

### 9. Demo mode is opt-in (`faf5974`)

**What was wrong:** `INGEST_MODE` defaulted to `demo`, which deletes every
reading and event at the start of each replay loop. Anyone who pointed the
backend at a real database and forgot `INGEST_MODE` would have it erased. The
old `.env.example` even paired a PostgreSQL URL with `INGEST_MODE=demo`.

**What changed:** the default is `none`. `demo` must be set explicitly, and it
logs a warning each time it clears the tables. `.env.example`, the README and
the docs are updated.

**Tests:** with `INGEST_MODE` unset, the setting is `none`.

### 10. Reuse `Event.add` (`fa1d748`)

`_extend_run` copied `Event.add` field by field to build a newly confirmed
event, so the two could drift apart. `add` now takes `(timestamp, wind_mean,
loss_kwh)` and both places call it. Behaviour is unchanged; the evaluation
still reproduces `metrics.json` exactly.

### 11. Remove unused code (`29700fa`)

Removed `t19.Event.is_active`, the `IceEvent.readings` relationship, the MQTT
feed's `received` counter, `formatTime`, `secondsSince` and Panel's
`className` prop. Each was checked with a search first. `IceEvent.is_active`
in `models.py` stays: the API's `EventOut.is_active` reads it, and the event
log shows it.

### 12. Settings via `Depends` (`ae322b4`)

`POST /api/readings` called `get_settings()` inside the function, so the test
for "HTTP ingest disabled" had to monkeypatch the module and rebuild the
frozen dataclass through `__dict__`. The route now takes `settings: Settings =
Depends(get_settings)`. The test uses FastAPI's `app.dependency_overrides`
and `dataclasses.replace`, which is the standard way.

### 13. One name for "10 minutes" (`df2aceb`)

The demo feed's speed-up divided a literal `600`, and the evaluation defined
its own `timedelta(minutes=10)`. Both now use `t19.SAMPLE_LENGTH`.

### 14. One name for the 24-hour window (`b91956b`)

`144` (24 hours of 10-minute readings) appeared in the dashboard query, the
power timeline and the power curve view. It's now `READINGS_SHOWN` in
`lib/api.ts`.

### 15. Like-for-like baseline (`e10db72`)

**What was wrong:** the README compared the detector's 6 false events with
the zero-output rule's 12. The detector is only scored on readings inside the
reference curve's wind range (190 clean readings). The rule was scored on all
220 clean readings above cut-in, including winds the detector deliberately
skips. On 9 April, for example, the rule fired at 11–17 m/s, where the
detector says "not judged".

**What changed:** `evaluate.py` also scores the rule on only the readings the
detector judged. Result: **10 false events over 5 days**, against the
detector's 6 on 1 day. The detector still does better. Both figures are in
`metrics.json`. The icing-period numbers for the rule are the same either way
(7 events, first alarm after 10 min).

### 16. Docs honesty (`3d67c49`)

- README results table: 10 over 5 days. The "clean days with no false event"
  row was 10 of 11 against 5 of 11, but the detector judged **nothing at
  all** on 3 of those 11 days. Counting only the 8 days with judged readings,
  it's 7 of 8 against 3 of 8. The dashboard's About panel and
  `evaluation/README.md` are updated to match `metrics.json`.
- "Nothing lost while the backend is down" now says what was tested and the
  limits: Mosquitto holds 1,000 queued messages per client by default, and a
  failure other than the database being down is logged and the reading not
  stored.
- Softened "can never disagree" (`ingest.py`), "validation here stops
  malformed data" (`schemas.py`), "the panels always agree", "duplicates are
  harmless" and the opening "Detects ice" (now "Flags likely ice", since
  without temperature data it can't tell ice from other causes). Also noted
  that the write lock covers one process only.

## Not verified

- **GitHub Actions** hadn't run on this branch when this was written. Check
  the PR's checks, especially the new PostgreSQL leg. (The same tests passed
  locally against a `postgres:17` container.)
- **The Render environment.** I can't see whether `INGEST_MODE` is already set
  there. See the note at the top.
- **Python 3.12** locally: everything ran on 3.14.5. CI covers 3.12.
- **Mosquitto's 1,000-message queue limit** comes from its documentation and
  wasn't tested.
- The frontend Docker image wasn't rebuilt. Its `npm ci` now also installs
  Vitest, a dev dependency.

## Found but deliberately not fixed

These are larger or structural, or out of scope for this pass:

1. **Detector state across processes.** The unique timestamp stops a reading
   being stored twice. But two *different* readings handled at the same moment
   by two processes would each load the detector state, and one would
   overwrite the other's update. A real fix is a row lock (`SELECT ... FOR
   UPDATE` on `detector_state`) or a single writer. The backend runs as one
   process today, so this is documented in `docs/decisions.md` rather than
   fixed.
2. **One MQTT client id.** `client_id="icing-backend"` is fixed, so two backend
   replicas would keep disconnecting each other. That's part of the same
   single-process assumption.
3. **Settings and the database engine are created at import time** (`main.py`,
   `database.py`). That's why the tests must set environment variables before
   importing the app. Fixing it needs an app factory, which is a structural
   change.
4. **Route modules import each other.** `routes/status.py` imports
   `recent_readings`/`recent_events` from `routes/readings.py`. These would
   sit better in a service module.
5. **No database migrations.** Tables come from `create_all`, so schema
   changes to an existing database are manual.
6. **Multi-turbine support.** There's one global detector state (`id=1`), and
   the `turbine_id` in each MQTT message is ignored.
7. **The dashboard's queries don't share a snapshot**, so a reading stored
   mid-request can appear in one panel a poll before another. This is now
   documented. It's cosmetic at a 2 s poll.
8. **A one-off non-database failure in the MQTT feed** still loses that
   reading (it's logged). Fixing it properly needs a dead-letter store.
9. **npm audit:** 6 advisories (5 high) in dev-only build tooling (postcss,
   browserslist, nanoid and others). They're already on `main`, with 0 in
   production dependencies. `npm audit fix` is a separate change.
10. **Small warnings:** Starlette's deprecation warning about `httpx` in the
    test client, and Vite's "chunk larger than 500 kB" warning.
11. **The "is it really ice?" detection work** (external temperature data,
    status-9 handling, a rotor-speed cross-check, event merging) is out of
    scope for this pass. Only the wording about it was corrected.
