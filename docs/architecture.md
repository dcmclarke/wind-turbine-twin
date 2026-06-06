# Architecture

## Data Flow

```mermaid
flowchart LR
    A[AV-7 HDF5 Dataset\nETH Zurich] -->|replay.py| B[FastAPI Backend]
    M[MQTT Broker\nMosquitto] -->|subscribe| B
    B -->|writes| C[(PostgreSQL)]
    C -->|reads| B
    B -->|GET /api/telemetry/history\nGET /api/icing/status\nGET /api/icing/history| D[React Dashboard]
    D -->|polls every 2s| B
```

## Components

| Component        | Technology         | Responsibility                                  |
| ---------------- | ------------------ | ----------------------------------------------- |
| Ingestion script | Python + h5py      | Replay AV-7 HDF5 data row by row to API         |
| MQTT subscriber  | Python + paho-mqtt | Accept live sensor data via MQTT protocol       |
| Icing detector   | Python             | IEA T19 power ratio method + temperature gate   |
| API              | FastAPI            | Receive telemetry, run detector, serve readings |
| Database         | PostgreSQL         | Store readings and icing events with timestamps |
| Dashboard        | React + Recharts   | Live power ratio chart, icing alerts, event log |

## API Endpoints

| Method | Endpoint                 | Purpose                        |
| ------ | ------------------------ | ------------------------------ |
| POST   | `/api/telemetry`         | Ingest SCADA reading           |
| GET    | `/api/telemetry/latest`  | Current turbine state          |
| GET    | `/api/telemetry/history` | Last N readings for chart      |
| GET    | `/api/icing/status`      | Current icing detection status |
| GET    | `/api/icing/history`     | Past icing events log          |

## Physics Model

Power ratio = actual_power / expected_power(wind_speed)

Expected power is derived from a parametric curve fitted to the AV-7's
normal operation data in ingestion/explore.ipynb. The IEA Wind Task 19
T19 method defines the detection logic: sustained ratio below threshold
combined with temperature near freezing triggers an icing event.

AV-7 specs: 7kW rated, 12.8m rotor, cut-in 2 m/s, cut-off 14 m/s.
