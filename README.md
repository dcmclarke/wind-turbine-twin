<a id="readme-top"></a>

[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![MIT License][license-shield]][license-url]
[![LinkedIn][linkedin-shield]][linkedin-url]
[![CI](https://github.com/dcmclarke/wind-turbine-twin/actions/workflows/evaluate.yml/badge.svg)](https://github.com/dcmclarke/wind-turbine-twin/actions/workflows/evaluate.yml)

<br />
<div align="center">
  <h3 align="center">Wind Turbine Icing Detection — SCADA Digital Twin</h3>
  <p align="center">
    A real-time icing-detection platform built around the IEA Wind Task 19 method, validated against real ETH Zurich SCADA fault data.
  </p>
</div>

---

<details>
  <summary>Table of Contents</summary>
  <ol>
    <li><a href="#about-the-project">About The Project</a></li>
    <li><a href="#results">Results</a></li>
    <li><a href="#built-with">Built With</a></li>
    <li><a href="#key-engineering-decisions">Key Engineering Decisions</a></li>
    <li><a href="#getting-started">Getting Started</a></li>
    <li><a href="#project-status">Project Status</a></li>
    <li><a href="#api-reference">API Reference</a></li>
  </ol>
</details>

---

## About The Project

Icing on turbine blades changes their aerodynamics, so a healthy turbine and an icing turbine produce different power output at the *same* wind speed. This project turns that physical fact into a working detector.

The **IEA Wind Task 19 icing detection method** — comparing actual power output against expected power output at a given wind speed — already existed as a research method. What didn't exist was an open-source, real-time application layer around it: live ingestion, persistent storage, a monitoring dashboard. That's the gap this project fills.

It also does one thing the original method doesn't account for: **the temperature sensor in the real dataset is broken for the entire recording period.** Rather than use corrupted data or silently substitute an unvalidated proxy, the temperature gate was removed and the detector was redesigned to rely on the power-ratio signal alone — then validated quantitatively to confirm that adaptation still works. That adaptation, and the evidence behind it, is the project's own contribution on top of the existing science.

**Core detection logic:**
1. Look up expected power for the current wind speed (from a curve fitted to 873,000+ real "healthy" SCADA readings)
2. Compute `power_ratio = actual_power / expected_power`
3. Track the ratio across a rolling window of the last 10 readings
4. Flag an icing alert only if **7 of the last 10** readings fall below threshold — tolerating sensor noise in both directions without either missing real icing events or false-alarming on single glitchy readings

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## Results

Validated against the full labeled ETH Zurich Aventa AV-7 dataset (1.5M+ readings, including a real recorded Dec 2022 icing event):

| Metric | Value |
|:-------|:------|
| Precision | 0.757 |
| Recall | 1.000 |
| F1 | 0.862 |
| True Positives | 308,110 |
| False Negatives | 9 |
| False Positives | 98,825 |

Recall of 1.000 means every real icing reading in the dataset was caught. The false positives are documented and understood, not swept under the rug: they cluster at low wind speeds where SCADA noise is highest — a known confounding factor in real icing detection (see [Decision 8](docs/decisions.md)). A wind-speed filter to suppress them was tested and rejected, because 75.7% of the actual icing event *also* occurs in that same low-wind band — filtering it out would have gutted recall to fix precision.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## Built With

**Backend**

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)

**Frontend**

![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white)

**Data & Evaluation**

![NumPy](https://img.shields.io/badge/NumPy-013243?style=for-the-badge&logo=numpy&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-150458?style=for-the-badge&logo=pandas&logoColor=white)
![scikit-learn](https://img.shields.io/badge/scikit--learn-F7931E?style=for-the-badge&logo=scikit-learn&logoColor=white)

**Infrastructure**

![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-2088FF?style=for-the-badge&logo=githubactions&logoColor=white)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## Key Engineering Decisions

Full reasoning and tradeoffs for every decision are documented in [`docs/decisions.md`](docs/decisions.md). A few worth highlighting:

- **Data-derived power curve, not a textbook formula** — the expected-power lookup table is fitted directly from 873,000+ real "healthy" readings from this specific turbine, not the Betz equation or manufacturer constants for a different model.
- **Temperature gate removed, not faked** — the dataset's temperature sensor is broken throughout. Rather than use corrupted values or an unvalidated proxy, the gate was removed and the detector redesigned around the power-ratio signal alone.
- **Threshold set from a quantitative sweep, not a guess** — thresholds from 0.1–0.9 were swept against the full labeled dataset; 0.1 maximises precision while keeping recall at 1.000.
- **Persistence filter (7 of 10) over single-reading alerts** — a single noisy reading, in either direction, doesn't trigger or suppress an alert. Requiring all 10/10 was considered and rejected — real sensor data is never that clean, even during genuine icing events.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## Getting Started

### Prerequisites

- **Docker** and **Docker Compose**
- **Python 3.10+** (for the replay/ingestion script)
- The [ETH Zurich Aventa AV-7 dataset](https://zenodo.org/records/8223010) (not included in this repo — see `data/README.md` for setup)

### Installation & Running

```sh
# Clone the repository
git clone https://github.com/dcmclarke/wind-turbine-twin.git
cd wind-turbine-twin

# Start backend + database
docker compose up -d

# In a second terminal — frontend
cd frontend
npm install
npm run dev
# → http://localhost:5173

# In a third terminal — replay real turbine data into the running system
cd ingestion
python replay.py --dataset normal --speed 0      # seed healthy baseline
python replay.py --dataset icing --start 2022-12-17 --end 2022-12-18 --speed 0
```

Backend API: `http://localhost:8000` (interactive docs at `/docs`)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## Project Status

This is an actively developed portfolio project. Being upfront about what's finished and what isn't:

**Complete and validated:**
- Detection algorithm, power curve, and full backend API
- Evaluation against the full labeled dataset (results above)
- CI pipeline running unit tests on every push

**In progress:**
- Frontend visual redesign (functionally complete, styling being reworked)
- MQTT ingestion support
- Cloud deployment

No live demo link yet — clone and run locally with the steps above in the meantime.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## API Reference

| Endpoint | Method | Description |
|:---------|:-------|:-------------|
| `/api/telemetry` | POST | Ingest a new sensor reading |
| `/api/telemetry/latest` | GET | Most recent reading |
| `/api/telemetry/history` | GET | Historical readings (`?limit=N`) |
| `/api/icing/status` | GET | Current detector state |
| `/api/icing/history` | GET | Past icing events |

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- MARKDOWN LINKS & IMAGES -->
[contributors-shield]: https://img.shields.io/github/contributors/dcmclarke/wind-turbine-twin.svg?style=for-the-badge
[contributors-url]: https://github.com/dcmclarke/wind-turbine-twin/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/dcmclarke/wind-turbine-twin.svg?style=for-the-badge
[forks-url]: https://github.com/dcmclarke/wind-turbine-twin/network/members
[stars-shield]: https://img.shields.io/github/stars/dcmclarke/wind-turbine-twin.svg?style=for-the-badge
[stars-url]: https://github.com/dcmclarke/wind-turbine-twin/stargazers
[issues-shield]: https://img.shields.io/github/issues/dcmclarke/wind-turbine-twin.svg?style=for-the-badge
[issues-url]: https://github.com/dcmclarke/wind-turbine-twin/issues
[license-shield]: https://img.shields.io/github/license/dcmclarke/wind-turbine-twin.svg?style=for-the-badge
[license-url]: https://github.com/dcmclarke/wind-turbine-twin/blob/main/LICENSE.txt
[linkedin-shield]: https://img.shields.io/badge/-LinkedIn-black.svg?style=for-the-badge&logo=linkedin&colorB=555
[linkedin-url]: https://www.linkedin.com/in/dc-clarke/
