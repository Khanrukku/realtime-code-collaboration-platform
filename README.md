# Real-Time Code Collaboration Platform

[![CI](https://github.com/Khanrukku/realtime-code-collaboration-platform/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Khanrukku/realtime-code-collaboration-platform/actions/workflows/ci.yml)

A real-time collaboration backend built with **FastAPI, WebSockets, versioned operations, deterministic conflict transformation, Redis-ready fan-out, tests, Docker, and CI**.

> This is an engineering simulation focused on the concurrency problems behind collaborative editors. It is not presented as a production-grade Google Docs replacement.

## Architecture

```text
Client A ─┐
Client B ─┼── WebSocket ──> FastAPI Collaboration Server
Client C ─┘                         |
                                    v
                           Room / Version Manager
                                    |
                         ┌──────────┴──────────┐
                         v                     v
                 Operation Transform      Redis Pub/Sub
                  + Version History       scaling seam
                         |
                         v
                    Document State
```

## Core engineering concepts

- Persistent WebSocket connections
- Multi-client room membership
- Versioned text operations
- Deterministic insert/delete transformation
- Handling stale client operations
- Ordered operation history
- Connection cleanup
- Async concurrency
- Redis Pub/Sub adapter for future multi-instance fan-out
- Unit + WebSocket tests
- GitHub Actions CI
- Docker Compose

## Operation model

Insert:

```json
{
  "type": "insert",
  "position": 5,
  "text": "hello",
  "base_version": 3,
  "operation_id": "op-123"
}
```

Delete:

```json
{
  "type": "delete",
  "position": 5,
  "length": 2,
  "base_version": 3,
  "operation_id": "op-124"
}
```

If an operation was created against an older version, the server transforms it against operations committed since that version before applying it.

## API

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/v1/health` | Health check |
| POST | `/api/v1/rooms/{room_id}` | Create/get a room |
| GET | `/api/v1/rooms/{room_id}` | Read room snapshot |
| WS | `/ws/{room_id}/{client_id}` | Join a collaborative session |

## Quick start

```bash
cp .env.example .env
docker compose up --build
```

Swagger: `http://localhost:8000/docs`

## Tests

```bash
pip install -r requirements.txt
pytest -q
```

## Why this project matters

The interesting engineering problem is concurrent editing:

```text
Client A inserts at position 4
Client B deletes at position 2
Both started from the same document version
```

The server must transform and order operations deterministically rather than silently overwrite one client's work.

## Future hardening

- Full OT inclusion/exclusion rules
- CRDT implementation and comparison benchmark
- Persistent operation log
- Redis Streams for multi-instance ordering
- Presence/cursor channels
- Authentication and room authorization
- Snapshotting/history compaction
- OpenTelemetry tracing
- Multi-instance load and chaos tests
