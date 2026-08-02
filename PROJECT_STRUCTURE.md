# PROJECT STRUCTURE

> **Official Repository Organization of the FlowPilot Engineering Platform**

Version: 1.0

Status: Frozen

---

# 1. Purpose

This document defines the official repository organization of the FlowPilot platform.

The repository is organized according to engineering responsibilities rather than programming languages. Every top-level directory represents a logical subsystem of the platform.

This structure shall remain stable throughout the lifetime of the project to ensure maintainability, scalability, and consistent collaboration.

---

# 2. Repository Layout

```
FlowPilot/

README.md
INTRODUCTION.md
SYSTEM_OVERVIEW.md
ARCHITECTURE.md
PROJECT_STRUCTURE.md
TECH_STACK.md
DEVELOPMENT_ROADMAP.md
AGENTS.md
WORKFLOWS.md
API_REFERENCE.md
DATABASE_SCHEMA.md
KNOWLEDGE_SYSTEM.md
CONTRIBUTING.md

docs/

flowpilot/

frontend/

datasets/

examples/

tests/

scripts/

docker/

kubernetes/

third_party/

.github/
```

---

# 3. Root Files

## README.md

GitHub landing page.

Contains:

- Overview
- Features
- Installation
- Quick Start
- Documentation Links

---

## INTRODUCTION.md

Project vision.

Mission.

Design philosophy.

Long-term goals.

---

## SYSTEM_OVERVIEW.md

Explains how the entire platform works.

---

## ARCHITECTURE.md

Complete implementation architecture.

---

## PROJECT_STRUCTURE.md

Repository organization.

---

## TECH_STACK.md

Technology selection.

---

## DEVELOPMENT_ROADMAP.md

Development phases.

---

## AGENTS.md

AI agent specifications.

---

## WORKFLOWS.md

Engineering workflows.

---

## API_REFERENCE.md

REST API documentation.

---

## DATABASE_SCHEMA.md

Database documentation.

---

## KNOWLEDGE_SYSTEM.md

Knowledge architecture.

---

## CONTRIBUTING.md

Contribution guide.

---

# 4. Documentation Directory

```
docs/

thesis/

architecture/

api/

diagrams/

developer/

research/
```

---

## docs/thesis/

Contains

Chapter01.md

...

Chapter18.md

Official research documentation.

---

## docs/architecture/

Additional architectural diagrams.

---

## docs/api/

OpenAPI specifications.

REST documentation.

---

## docs/diagrams/

Mermaid

PlantUML

Draw.io

Architecture images

---

## docs/developer/

Developer tutorials.

Coding standards.

Guides.

---

## docs/research/

Research notes.

References.

Publications.

---

# 5. FlowPilot Package

```
flowpilot/

core/

agents/

knowledge/

memory/

planner/

generator/

validator/

runtime/

learning/

conversation/

security/

deployment/

integrations/

api/

database/

services/

schemas/

models/

utils/
```

---

# 6. Core

Contains

- Orchestrator
- Workflow Engine
- Event Bus
- Context Manager
- Service Registry
- Task Scheduler
- Plugin Manager
- State Machine

This is the heart of FlowPilot.

---

# 7. Agents

Contains all engineering agents.

Examples

Planner Agent

Generator Agent

Validator Agent

Runtime Agent

Learning Agent

Knowledge Agent

Deployment Agent

Conversation Agent

Security Agent

---

# 8. Knowledge

Contains

Engineering knowledge.

Knowledge Graph.

Embeddings.

GNU Radio blocks.

Hardware.

Research papers.

Engineering examples.

---

# 9. Memory

Stores

Session memory.

Conversation memory.

Project memory.

Runtime memory.

---

# 10. Planner

Transforms engineering intent into executable engineering plans.

Produces

Planning graphs.

Execution plans.

Dependency graphs.

---

# 11. Generator

Generates

GNU Radio Flowgraphs.

Python.

Configuration.

Documentation.

Templates.

---

# 12. Validator

Engineering validation.

Syntax validation.

Dependency validation.

Hardware validation.

---

# 13. Runtime

Execution.

Monitoring.

Telemetry.

Logging.

Hardware communication.

---

# 14. Learning

Experience database.

Feedback.

Recommendation engine.

Pattern mining.

---

# 15. Conversation

Chat.

Voice (future).

Prompt management.

Context.

History.

---

# 16. Security

Authentication.

Authorization.

Policy management.

Audit logs.

Encryption.

Sandbox.

---

# 17. Deployment

Docker.

Kubernetes.

GitHub Actions.

Monitoring.

Cloud deployment.

---

# 18. Integrations

GNU Radio.

PlutoSDR.

USRP.

RTL-SDR.

HackRF.

LimeSDR.

Future integrations.

---

# 19. API

REST APIs.

WebSockets.

Gateway.

API versioning.

---

# 20. Database

PostgreSQL.

Neo4j.

Redis.

Qdrant.

Migrations.

Repositories.

---

# 21. Services

Shared business logic.

Reusable services.

Cross-module functionality.

---

# 22. Schemas

Pydantic models.

DTOs.

Validation schemas.

---

# 23. Models

Domain models.

Business entities.

Project models.

Workflow models.

---

# 24. Utils

Utility functions.

Helpers.

Logging.

Configuration.

Constants.

---

# 25. Frontend

```
frontend/

app/

components/

pages/

hooks/

services/

assets/

styles/
```

React application.

---

# 26. Datasets

Contains

Research papers.

GNU Radio examples.

Embeddings.

Benchmark datasets.

Engineering metadata.

---

# 27. Examples

Contains

Generated GNU Radio projects.

Reference projects.

Tutorials.

Sample workflows.

---

# 28. Tests

Contains

Unit tests.

Integration tests.

Performance tests.

End-to-end tests.

---

# 29. Scripts

Development utilities.

Migration scripts.

Automation.

Build tools.

---

# 30. Docker

Dockerfiles.

Compose files.

Container configuration.

---

# 31. Kubernetes

Deployment manifests.

Helm charts (future).

Scaling.

Ingress.

---

# 32. Third Party

Contains optional external source code used for study or reference.

Examples

GNU Radio source.

Open-source libraries.

Reference implementations.

Third-party code should not be modified directly unless intentionally forked.

---

# 33. GitHub Directory

Contains

CI/CD workflows.

Issue templates.

Pull request templates.

Automation.

---

# 34. Naming Conventions

Directories

snake_case

Python modules

snake_case

Classes

PascalCase

Functions

snake_case

Constants

UPPER_CASE

---

# 35. Repository Rules

No circular dependencies.

No duplicated business logic.

No direct database access outside repositories.

No service-to-service internal coupling.

Everything communicates through the FlowPilot Core.

---

# 36. Summary

The FlowPilot repository is organized around engineering responsibilities rather than implementation details.

This structure provides:

- Scalability
- Maintainability
- Extensibility
- Clear ownership
- Modular development

Once adopted, this repository organization becomes the official implementation structure for the FlowPilot platform.

---