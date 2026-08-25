# Real-Time Code Collaboration Platform

[![CI](https://github.com/Khanrukku/realtime-code-collaboration-platform/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Khanrukku/realtime-code-collaboration-platform/actions/workflows/ci.yml)
[![WebSocket Benchmark](https://github.com/Khanrukku/realtime-code-collaboration-platform/actions/workflows/websocket-benchmark.yml/badge.svg)](https://github.com/Khanrukku/realtime-code-collaboration-platform/actions/workflows/websocket-benchmark.yml)
![Python](https://img.shields.io/badge/Python-3.12-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-WebSockets-009688)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED)

A backend-focused real-time collaboration system built with **FastAPI, WebSockets, async Python, versioned operations, deterministic conflict transformation, reconnect synchronization, Redis-ready fan-out, automated tests, Docker, and GitHub Actions**.

The project explores the distributed-systems problems behind collaborative editors: multiple clients modifying shared state concurrently while preserving deterministic document state.

> **Engineering simulation:** This project focuses on collaboration, synchronization, concurrency, and conflict-resolution concepts. It is not presented as a production replacement for Google Docs or other commercial collaborative editors.

---

## Architecture

```text
 Client A ─┐
 Client B ─┼──── WebSocket ────┐
 Client C ─┘                    │
                               ▼
                    ┌──────────────────────┐
                    │       FastAPI        │
                    │ Collaboration Server │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │    Room Manager      │
                    │ Clients + Versions   │
                    └──────────┬───────────┘
                               │
                    ┌──────────┴──────────┐
                    ▼                     ▼
          ┌───────────────────┐   ┌──────────────────┐
          │ Operation         │   │ Redis Pub/Sub    │
          │ Transformation    │   │ Scaling Seam     │
          └─────────┬─────────┘   └──────────────────┘
                    │
                    ▼
          ┌───────────────────┐
          │ Version History   │
          │ + Document State  │
          └───────────────────┘
```

---

## Core Engineering Concepts

| Concept | Implementation |
|---|---|
| **Real-time communication** | Persistent FastAPI WebSocket connections |
| **Concurrent clients** | Multiple clients can participate in the same collaboration room |
| **Versioned operations** | Every edit references the document version on which it was created |
| **Conflict transformation** | Stale operations are transformed against newer committed operations |
| **Deterministic ordering** | Concurrent edits are resolved using deterministic transformation rules |
| **Synchronization** | Room-level `asyncio.Lock` protects shared document mutation |
| **Reconnect recovery** | Reconnecting clients receive the latest document snapshot and version |
| **Client cleanup** | Failed/disconnected WebSockets are removed from active room membership |
| **Operation history** | Committed operations are retained for stale-operation transformation |
| **Horizontal-scaling seam** | Redis Pub/Sub adapter provides a path toward multi-instance fan-out |
| **Regression testing** | Unit and WebSocket integration tests exercise collaboration behavior |
| **Performance testing** | Reproducible WebSocket benchmark runs through GitHub Actions |

---

## Collaboration Flow

```text
Client operation
      │
      ▼
Read base_version
      │
      ▼
Is client version stale?
      │
   ┌──┴──┐
   │     │
  No    Yes
   │     │
   │     ▼
   │  Transform against
   │  committed operations
   │     │
   └──┬──┘
      ▼
Apply operation
      │
      ▼
Increment document version
      │
      ▼
Store operation in history
      │
      ▼
Broadcast committed operation
      │
      ▼
ACK originating client
```

This prevents a stale client from blindly overwriting newer shared state.

---

## Operation Model

### Insert

```json
{
  "type": "insert",
  "position": 5,
  "text": "hello",
  "base_version": 3,
  "operation_id": "op-123"
}
```

### Delete

```json
{
  "type": "delete",
  "position": 5,
  "length": 2,
  "base_version": 3,
  "operation_id": "op-124"
}
```

`base_version` represents the document version known to the client when the operation was created.

If the server has already committed newer operations, the incoming operation is treated as stale and transformed against the relevant operation history before being committed.

---

## Concurrent Editing Example

Assume two clients begin from the same document version:

```text
Document version: 4

Client A
└── inserts text at position 4

Client B
└── submits another operation based on version 4

Server
├── commits Client A's operation
├── document becomes version 5
├── receives Client B's stale operation
├── transforms it against the operation committed at version 5
└── commits the transformed operation deterministically
```

This is fundamentally different from a last-write-wins implementation where one client's work could simply overwrite another's.

---

## Reconnect Synchronization

WebSocket clients can temporarily disconnect while other users continue editing.

When a client reconnects, the server sends a fresh snapshot containing the current document and server version:

```text
Client A connected
Document version = 1
        │
        ▼
Client A disconnects
        │
        ▼
Client B continues editing
Document version = 2
        │
        ▼
Client A reconnects
        │
        ▼
Server snapshot
text = latest document
version = 2
```

This behavior is covered by automated WebSocket integration tests.

---

## API

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/v1/health` | Service health check |
| `POST` | `/api/v1/rooms/{room_id}` | Create or retrieve a collaboration room |
| `GET` | `/api/v1/rooms/{room_id}` | Retrieve the current room snapshot |
| `WS` | `/ws/{room_id}/{client_id}` | Join a real-time collaborative editing session |

---

## Automated Test Coverage

The test suite validates key collaboration and concurrency behavior, including:

- WebSocket connection and initial synchronization
- Operation broadcast and acknowledgement
- Multi-client operation delivery
- Concurrent inserts at the same position
- Deterministic conflict resolution
- Stale-version operation transformation
- Insert/delete interaction
- Invalid future-version rejection
- Client disconnect and reconnect synchronization

Run the test suite with:

```bash
pip install -r requirements.txt
pytest -q
```

Every push is validated automatically through **GitHub Actions CI**.

---

## WebSocket Performance Benchmark

The repository includes a reproducible asynchronous WebSocket benchmark:

```text
benchmarks/websocket_benchmark.py
```

A dedicated GitHub Actions workflow starts the FastAPI server and runs the benchmark against it.

### Latest measured run

| Metric | Result |
|---|---:|
| Concurrent clients | **20** |
| Operations per client | **10** |
| Total operations | **200** |
| Total duration | **0.078 s** |
| Operation throughput | **2,557.49 ops/sec** |
| Average round-trip latency | **2.06 ms** |
| Median round-trip latency | **1.87 ms** |
| P95 latency | **2.68 ms** |
| P99 latency | **2.99 ms** |

### Benchmark scenario

```text
20 concurrent WebSocket clients
        ×
10 sequential operations/client
        =
200 measured operations
```

Each measured operation includes sending an edit and waiting for both the committed-operation broadcast and acknowledgement.

> **Benchmark scope:** These results were measured on a GitHub-hosted Actions runner against a single local FastAPI process. They demonstrate reproducible behavior under this synthetic workload and should not be interpreted as production capacity or a distributed multi-node performance guarantee.

The benchmark can be reproduced from:

```text
GitHub → Actions → WebSocket Benchmark → Run workflow
```

---

## Quick Start

### Docker

```bash
git clone https://github.com/Khanrukku/realtime-code-collaboration-platform.git
cd realtime-code-collaboration-platform

cp .env.example .env

docker compose up --build
```

The FastAPI service is then available at:

```text
http://localhost:8000
```

Swagger/OpenAPI documentation:

```text
http://localhost:8000/docs
```

---

## Project Structure

```text
realtime-code-collaboration-platform/
│
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── websocket-benchmark.yml
│
├── app/
│   ├── api/
│   ├── collab/
│   │   ├── document.py
│   │   ├── manager.py
│   │   └── models.py
│   ├── core/
│   └── main.py
│
├── benchmarks/
│   └── websocket_benchmark.py
│
├── tests/
│   ├── test_api.py
│   └── test_websocket.py
│
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## Technology Stack

| Technology | Purpose |
|---|---|
| **Python 3.12** | Core language and asynchronous runtime |
| **FastAPI** | HTTP API and WebSocket server |
| **WebSockets** | Bidirectional real-time client communication |
| **asyncio** | Concurrent connection and operation handling |
| **Pydantic** | Operation and snapshot validation |
| **Redis** | Pub/Sub scaling seam for multi-instance architecture |
| **pytest** | Automated testing |
| **FastAPI TestClient** | WebSocket integration testing |
| **Docker / Compose** | Reproducible containerized environment |
| **GitHub Actions** | CI and reproducible performance benchmarking |

---

## Engineering Trade-offs

This project deliberately implements a compact transformation model rather than claiming complete production Operational Transformation or CRDT semantics.

The current architecture prioritizes demonstrating:

1. explicit document versioning,
2. deterministic concurrent-operation handling,
3. stale-client reconciliation,
4. synchronization of shared mutable state,
5. real-time WebSocket fan-out,
6. reconnect recovery,
7. automated concurrency testing, and
8. reproducible performance measurement.

A production collaborative editor would require substantially stronger distributed consistency, persistence, security, observability, and recovery guarantees.

---

## Future Hardening

Potential production-oriented extensions include:

- Full Operational Transformation inclusion/exclusion rules
- CRDT implementation and OT-vs-CRDT comparison
- Persistent operation log
- Durable document snapshots
- Redis Streams or another ordered distributed event log
- Multi-instance WebSocket fan-out
- Presence and cursor synchronization
- Authentication and room-level authorization
- History compaction
- Backpressure and per-client rate limiting
- OpenTelemetry tracing and metrics
- Multi-node load testing
- Network-partition and chaos testing

---

## What This Project Demonstrates

This repository is primarily a **distributed-systems and backend-engineering project**, rather than a UI-focused collaborative editor.

It demonstrates reasoning about:

**concurrency → ordering → shared state → stale clients → conflict transformation → synchronization → reconnect recovery → real-time communication → performance measurement**

The objective is to make those engineering decisions explicit, testable, and reproducible.

---

## Author

**Rukaiya Khan**

- GitHub: [@Khanrukku](https://github.com/Khanrukku)
- LinkedIn: [linkedin.com/in/rukaiyakhan](https://linkedin.com/in/rukaiyakhan)
