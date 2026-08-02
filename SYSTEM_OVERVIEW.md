# SYSTEM OVERVIEW

> **Complete System Overview of the FlowPilot Autonomous AI Engineering Platform**

---

# 1. Purpose

FlowPilot is an AI-native engineering platform designed to automate and assist the complete Software Defined Radio (SDR) engineering lifecycle.

Unlike traditional engineering software, FlowPilot is not a single application. It is a distributed engineering platform composed of multiple intelligent services working together under a unified orchestration layer.

The purpose of this document is to provide a high-level understanding of the entire FlowPilot ecosystem before exploring individual modules.

---

# 2. System Vision

FlowPilot is designed as an **Engineering Operating System** rather than a traditional application.

Instead of manually building GNU Radio flowgraphs, searching documentation, debugging runtime errors, and writing repetitive code, engineers interact with FlowPilot using natural language.

FlowPilot transforms engineering intent into executable engineering workflows.

---

# 3. High-Level Architecture

```
                        User
                          │
                          ▼
                 Conversation Interface
                          │
                          ▼
                  FlowPilot Core
                          │
 ┌───────────────┬─────────┴─────────┬──────────────┐
 ▼               ▼                   ▼              ▼
Knowledge      Memory             Planner      Service Registry
 │               │                   │
 └───────────────┴──────────────┬────┘
                                ▼
                          Generator
                                │
                                ▼
                           Validator
                                │
                                ▼
                            Runtime
                                │
                                ▼
                            Learning
                                │
                                ▼
                          Deployment
```

Every engineering workflow begins at the Conversation Interface and is coordinated by the FlowPilot Core.

---

# 4. Core Philosophy

The architecture follows one fundamental rule:

> **Everything communicates through the FlowPilot Core.**

Subsystems never communicate directly with one another.

Instead, all requests are routed through the orchestration layer.

This provides:

- Loose coupling
- Scalability
- Maintainability
- Observability
- Replaceable components

---

# 5. Major Subsystems

The platform consists of the following major subsystems.

---

## 5.1 Conversation System

Responsibilities

- Chat Interface
- Voice Interaction
- Context Tracking
- Prompt Management
- Session Handling

Input

Natural Language

Output

Structured Engineering Requests

---

## 5.2 Core System

The Core coordinates every engineering workflow.

Responsibilities

- Request Routing
- Workflow Management
- Task Scheduling
- Service Discovery
- Event Processing
- Context Management

The Core is the brain of FlowPilot.

---

## 5.3 Knowledge System

Stores engineering knowledge.

Includes

- GNU Radio Blocks
- DSP Algorithms
- SDR Hardware
- RF Concepts
- Engineering Standards
- Research Papers
- Documentation
- Examples

Technologies

- Neo4j
- Qdrant
- Embedding Models

---

## 5.4 Memory System

Maintains

- Conversation Memory
- Engineering Sessions
- User Preferences
- Runtime History
- Previous Projects

Technologies

- Redis
- PostgreSQL

---

## 5.5 Planning System

Transforms engineering intent into executable plans.

Example

User

↓

Build FM Receiver

↓

Planner

↓

1 Source

↓

2 Filter

↓

3 Demodulator

↓

4 Audio Sink

No code is generated here.

Only engineering planning.

---

## 5.6 Generator

Receives the engineering plan.

Produces

- GNU Radio Flowgraphs
- Python
- YAML
- Configurations
- Documentation

---

## 5.7 Validator

Verifies

- Connections
- Parameters
- Compatibility
- Missing Blocks
- Runtime Issues
- Engineering Rules

Produces validation reports.

---

## 5.8 Runtime

Responsible for execution.

Functions

- Run GNU Radio
- Hardware Communication
- Monitor Execution
- Capture Logs
- Collect Telemetry

---

## 5.9 Learning

Continuously improves the platform.

Learns from

- User Feedback
- Runtime Logs
- Successful Projects
- Failed Projects
- Engineering Patterns

Improves future recommendations.

---

## 5.10 Deployment

Responsible for

- Docker
- Kubernetes
- CI/CD
- Monitoring
- Cloud Deployment

---

# 6. Engineering Workflow

Every request follows the same lifecycle.

```
User Request

↓

Conversation

↓

Core

↓

Knowledge

↓

Planner

↓

Generator

↓

Validator

↓

Runtime

↓

Learning

↓

Engineering Response
```

---

# 7. Knowledge Flow

```
GNU Radio

↓

Block Scanner

↓

Parser

↓

Knowledge Graph

↓

Embeddings

↓

Vector Database

↓

Planner

↓

Generator

↓

Engineering Output
```

The knowledge continuously evolves as new GNU Radio releases become available.

---

# 8. Learning Pipeline

```
Engineering Session

↓

Execution

↓

Logs

↓

Feedback

↓

Experience Database

↓

Recommendation Engine

↓

Future Projects
```

The system becomes smarter over time.

---

# 9. Technology Overview

Programming

- Python
- TypeScript

Frontend

- React

Backend

- FastAPI

AI

- GPT
- Qwen
- RAG

Databases

- PostgreSQL
- Neo4j
- Redis
- Qdrant

Infrastructure

- Docker
- Kubernetes

---

# 10. Supported Hardware

Current target hardware includes

- ADALM-Pluto
- USRP
- RTL-SDR
- HackRF
- LimeSDR

Future hardware can be integrated without changing the architecture.

---

# 11. Repository Mapping

```
flowpilot/

core/

agents/

knowledge/

generator/

validator/

runtime/

learning/

conversation/

security/

deployment/

integrations/

frontend/

docs/

datasets/
```

Each directory corresponds directly to one architectural subsystem.

---

# 12. Design Principles

FlowPilot follows these principles:

- Modular
- AI-First
- Explainable
- Extensible
- Secure
- Observable
- Testable
- Cloud Native
- Knowledge Driven
- Human-Centered

---

# 13. Long-Term Evolution

FlowPilot is designed to evolve through multiple generations.

Generation 1

AI-assisted GNU Radio.

↓

Generation 2

Knowledge Graph.

↓

Generation 3

Multi-Agent Engineering.

↓

Generation 4

Engineering Digital Twin.

↓

Generation 5

Autonomous Engineering Platform.

---

# 14. Success Criteria

The platform is considered successful when it can

✓ Understand engineering intent

✓ Plan engineering workflows

✓ Retrieve engineering knowledge

✓ Generate complete GNU Radio projects

✓ Validate engineering correctness

✓ Execute SDR systems

✓ Learn from engineering experience

✓ Improve future recommendations

---

# 15. Relationship to the Thesis

The implementation documented in this repository is based on the complete FlowPilot research documented in:

```
docs/

thesis/

Chapter01.md

...

Chapter18.md
```

The thesis defines the research.

This repository defines the implementation.

Together they form the complete FlowPilot platform.

---

# 16. Summary

FlowPilot is an Engineering Operating System that combines Artificial Intelligence, Engineering Knowledge, Autonomous Planning, GNU Radio Generation, Validation, Runtime Execution, Continuous Learning, and Cloud Infrastructure into one unified platform.

Every subsystem is designed to operate independently while cooperating through the FlowPilot Core.

The result is a scalable, extensible, and intelligent engineering environment capable of transforming natural-language engineering intent into validated Software Defined Radio systems.

---

> **"FlowPilot is not just software. It is an Engineering Intelligence Platform."**