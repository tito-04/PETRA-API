# PETRA — Path Energy Traffic Ratio API

A prototype implementation of the **PETRA** API as specified in
[draft-petra-green-api](draft-petra-green-api-03.txt), developed within the scope of the
IETF [GREEN Working Group](https://datatracker.ietf.org/wg/green/).

PETRA queries the energy consumption of the network path between two IP addresses and
returns a **watts-per-gigabit** metric, along with the accuracy classification of that
measurement, using the identity hierarchy defined in `ietf-power-and-energy.yang`.

---

## Architecture

```
┌──────────────────────────────────────┐
│          PETRA Server  :8000         │  ← POST /restconf/operations/energy/query
│  src/petra/server.py                 │
│  ┌───────────────┐ ┌───────────────┐ │
│  │ path_resolver │ │device_client  │ │
│  │ (NetworkX)    │ │ (httpx async) │ │
│  └───────────────┘ └──────┬────────┘ │
└─────────────────────────── │ ────────┘
                             │ RESTCONF GET (per router on path)
┌────────────────────────────▼─────────┐
│        Mock Device Server  :8002     │  ← GET /restconf/data/ietf-power-and-energy:...
│  src/mock/device_server.py           │
│  Simulates 6 routers (R1–R6)         │
│  Returns YANG-compliant energy data  │
└──────────────────────────────────────┘
```

### Component overview

| File | Responsibility |
|---|---|
| `src/mock/topology.py` | Defines the 6-router grid topology (NetworkX graph, IP prefixes, energy attributes) |
| `src/mock/device_server.py` | Mock RESTCONF server — returns `ietf-power-and-energy` data per device |
| `src/petra/path_resolver.py` | Resolves src/dst IP addresses to a list of router IDs (shortest path) |
| `src/petra/device_client.py` | Async HTTP client — fetches live energy readings from the mock device server |
| `src/petra/energy_calculator.py` | Aggregates per-device readings into the watts-per-gigabit metric |
| `src/petra/server.py` | Main PETRA API server |

### Network topology (mock)

```
R1 (10.0.1.0/24) --- R2 (10.0.2.0/24) --- R3 (10.0.3.0/24)
|                         |                         |
R4 (10.0.4.0/24) --- R5 (10.0.5.0/24) --- R6 (10.0.6.0/24)
```

### YANG modules used

| Module | Role |
|---|---|
| `ietf-petra.yang` | Defines the PETRA query action, input/output schema |
| `ietf-power-and-energy.yang` | Defines the energy object data model and accuracy identity hierarchy |
| `ietf-iana-power-and-energy.yang` | IANA-defined certification types (e.g. ENERGY STAR) |

---

## Requirements

- Python 3.12+
- All dependencies listed in `requirements.txt`

---

## Setup

### 1. Clone / enter the project directory

```bash
cd /path/to/PETRA
```

### 2. Create and activate the virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## Running

Both servers must be running simultaneously. Open **two terminals**.

### Terminal 1 — Mock Device Server (port 8002)

```bash
source .venv/bin/activate
python -m src.mock.device_server
```

### Terminal 2 — PETRA API Server (port 8000)

```bash
source .venv/bin/activate
python -m src.petra.server
```

---

## Testing the API

### Swagger UI (recommended)

Open [http://localhost:8000/docs](http://localhost:8000/docs) in a browser.
Use the `POST /restconf/operations/energy/query` endpoint with the form provided.

Example request body:
```json
{
  "input": {
    "src-ip": "10.0.1.1",
    "dst-ip": "10.0.6.1",
    "throughput": 10.0
  }
}
```

### curl

```bash
curl -s -X POST http://localhost:8000/restconf/operations/energy/query \
  -H "Content-Type: application/yang-data+json" \
  -d '{"input": {"src-ip": "10.0.1.1", "dst-ip": "10.0.6.1", "throughput": 10.0}}' \
  | python3 -m json.tool
```

Example response (live data from mock device server):
```json
{
  "output": {
    "success": {
      "watts-per-gigabit": 42.317,
      "data-source-accuracy": "ietf-power-and-energy:accuracy-measured-bronze",
      "path": ["R1", "R2", "R5", "R6"],
      "data-source": "live"
    }
  }
}
```

If the mock device server is not running, the PETRA server falls back to the topology
model and returns `"data-source": "topology-model"`.

### Invalid address

```bash
curl -s -X POST http://localhost:8000/restconf/operations/energy/query \
  -H "Content-Type: application/yang-data+json" \
  -d '{"input": {"src-ip": "1.2.3.4", "dst-ip": "10.0.6.1", "throughput": 10.0}}'
```

Response:
```json
{"output": {"invalid-address": {}}}
```

### Health checks

```bash
curl http://localhost:8000/health   # PETRA server
curl http://localhost:8002/health   # Mock device server
```

---

## Running the tests

With the virtual environment active (device server does **not** need to be running —
tests use mocks internally):

```bash
python -m pytest tests/ -v
```

Expected: **48 passed**.

---

## YANG conformance notes

| Field | YANG type | Implementation |
|---|---|---|
| `instantaneous-power` | `int32` | `int(round(watts))` ✅ |
| `total-energy-consumed` | `uint64` | `int(round(wh))` ✅ |
| `watts-per-gigabit` | `decimal64 {fraction-digits 3}` | `round(wpg, 3)` ✅ |
| `data-source-accuracy` | `identityref` (least accurate on path) | `_accuracy_rank()` picks worst ✅ |

> **Known deviations (low priority, intentional for the mock):**
> - `source-component-id` is a free string instead of a leafref to `ietf-hardware`
> - `path` and `data-source` fields in the success response are extensions not present in the YANG schema (useful for debugging)
> - Accuracy levels are limited to bronze/silver/gold (red and ones not used in the mock topology)
