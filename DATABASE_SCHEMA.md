# DATABASE SCHEMA

> **Official Database Architecture of the FlowPilot Engineering Platform**

Version: 1.0

Status: Frozen

---

# 1. Purpose

This document defines the official database architecture of FlowPilot.

Unlike traditional applications that rely on a single database, FlowPilot follows a **polyglot persistence** strategy, where multiple databases are used according to their strengths.

Each database has a single responsibility.

---

# 2. Database Philosophy

FlowPilot separates data into four major categories:

- Relational Data
- Graph Data
- Vector Data
- Cache & Runtime Data

No database attempts to solve every problem.

---

# 3. Database Architecture

```
                   FlowPilot

                      │

      ┌───────────────┼───────────────┐

      ▼               ▼               ▼

 PostgreSQL        Neo4j          Qdrant

      │               │               │

      └───────────────┼───────────────┘

                      ▼

                   Redis
```

---

# 4. Database Responsibilities

| Database | Purpose |
|-----------|----------|
| PostgreSQL | Structured business data |
| Neo4j | Engineering knowledge graph |
| Qdrant | Vector embeddings |
| Redis | Cache and runtime memory |

---

# 5. PostgreSQL

Purpose

Stores structured application data.

---

## Main Tables

### Users

Stores

- User profile
- Authentication
- Preferences

---

### Projects

Stores

- Project metadata
- Project owner
- Status
- Creation date

---

### Sessions

Stores

- Conversation sessions
- Runtime sessions
- Active workflows

---

### Workflows

Stores

- Workflow ID
- Status
- Current step
- Progress

---

### Runtime Logs

Stores

- Execution history
- Runtime metrics
- Performance statistics

---

### Configurations

Stores

- User settings
- Platform configuration
- Feature flags

---

# 6. Neo4j Knowledge Graph

Purpose

Represents engineering knowledge using nodes and relationships.

---

## Main Node Types

- GNU Radio Block
- Hardware Device
- Protocol
- Algorithm
- Parameter
- Research Paper
- Example Project
- User Knowledge

---

## Relationships

```
BLOCK

↓

USES

↓

PARAMETER
```

```
BLOCK

↓

CONNECTS_TO

↓

BLOCK
```

```
PROJECT

↓

IMPLEMENTS

↓

PROTOCOL
```

```
PAPER

↓

DESCRIBES

↓

ALGORITHM
```

---

## Example

```
FM Demod

↓

CONNECTS_TO

↓

Audio Sink
```

---

# 7. Qdrant Vector Database

Purpose

Semantic search.

Stores

- Research paper embeddings
- Documentation embeddings
- Example embeddings
- GNU Radio documentation
- Hardware manuals

---

## Collections

EngineeringDocs

ResearchPapers

Examples

GNUBlocks

HardwareDocs

---

# 8. Redis

Purpose

High-speed runtime storage.

Stores

- Session cache
- Conversation cache
- Runtime state
- Temporary context
- Event queue (future)

---

# 9. Entity Relationships

```
User

↓

Projects

↓

Workflow

↓

Runtime

↓

Logs
```

---

# 10. Project Entity

```
Project

├── ID

├── Name

├── Description

├── Owner

├── Status

├── Version

├── Created

├── Updated

└── Metadata
```

---

# 11. Workflow Entity

```
Workflow

├── ID

├── Type

├── Current State

├── Started

├── Finished

├── Status

└── Result
```

---

# 12. Knowledge Entity

```
Knowledge Item

├── ID

├── Category

├── Source

├── Title

├── Description

├── Metadata

├── Embedding

└── Relationships
```

---

# 13. Agent Entity

```
Agent

├── Name

├── Version

├── Status

├── Supported Tasks

├── Last Execution

└── Metrics
```

---

# 14. Runtime Entity

```
Runtime

├── Session

├── Hardware

├── Status

├── CPU

├── Memory

├── Errors

└── Logs
```

---

# 15. Engineering Knowledge Model

```
Research Paper

↓

Algorithm

↓

GNU Block

↓

Flowgraph

↓

Hardware

↓

Example
```

This enables engineering reasoning through graph traversal.

---

# 16. Indexing Strategy

PostgreSQL

- Primary Keys
- Foreign Keys
- Indexed Search Fields

---

Neo4j

- Node Labels
- Relationship Indexes

---

Qdrant

- Vector Similarity
- Metadata Filtering

---

Redis

- Key-based lookup
- Expiration policies

---

# 17. Backup Strategy

PostgreSQL

Daily backup

---

Neo4j

Weekly graph snapshot

---

Qdrant

Embedding backup

---

Redis

Ephemeral

No permanent backup required

---

# 18. Scaling Strategy

PostgreSQL

Read replicas

---

Neo4j

Cluster mode

---

Qdrant

Distributed collections

---

Redis

Cluster mode

---

# 19. Security

Every database connection must use:

- TLS
- Authentication
- Authorization
- Connection pooling
- Audit logging

Secrets are stored outside the source code.

---

# 20. Future Extensions

Future databases may include:

- Time-series database
- Object storage
- Message queue
- Analytics warehouse

The current architecture allows new databases to be integrated without redesigning the platform.

---

# 21. Summary

FlowPilot uses a multi-database architecture to separate business data, engineering knowledge, semantic embeddings, and runtime state.

This approach provides:

- Scalability
- Performance
- Maintainability
- Explainable engineering
- Efficient AI retrieval
- Production readiness

Together, PostgreSQL, Neo4j, Qdrant, and Redis form the persistent data layer of the FlowPilot Engineering Platform.

---
