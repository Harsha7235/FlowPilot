# FlowPilot

> **An Autonomous AGENTIC AI Engineering Platform for Software Defined Radio (SDR) Development**

# FlowPilot – AI-Powered GNU Radio Companion Engineering Assistant

**FlowPilot** is an AI-assisted engineering research and development extension designed to integrate intelligent assistance directly into **GNU Radio Companion (GRC)**.

It aims to simplify GNU Radio development by combining AI-assisted engineering explanations, research-paper analysis, flowgraph inspection, block validation, troubleshooting, and flowgraph construction support within the GRC environment.

Instead of switching between multiple applications to understand research papers, inspect GNU Radio blocks, or troubleshoot flowgraphs, FlowPilot brings these capabilities into an integrated engineering assistant interface.

---

## Project Overview

GNU Radio Companion is a graphical development environment used to design and implement software-defined radio (SDR) systems through interconnected signal-processing blocks.

FlowPilot extends this workflow by introducing an AI-assisted engineering layer that helps users understand, analyze, validate, and develop GNU Radio flowgraphs.

The system combines:
- AI-assisted engineering support.
- Research-paper analysis.
- GNU Radio block inspection.
- Flowgraph validation.
- Automated design assistance.
- Local language model integration.

The objective is to make SDR development more accessible, structured, and efficient.

---

## Key Features

### 1. AI Engineering Assistant
- Integrated assistant interface inside GNU Radio Companion.
- Supports engineering questions related to GNU Radio and signal processing.
- Uses a configurable language model interface.
- Provides contextual assistance during flowgraph development.

### 2. Research Paper Analysis
- Attach research papers in PDF format.
- Ask questions about the currently loaded paper.
- Retrieve relevant passages from extracted paper text.
- Provide evidence-based responses using matching excerpts.
- Separate paper-supported information from general engineering explanations.

The research assistant uses deterministic keyword and passage-matching logic for paper-based answers rather than presenting unsupported information as facts from the paper.

### 3. Flowgraph Analysis
FlowPilot provides tools to understand the active GNU Radio flowgraph.

Available capabilities include:
- Flowgraph summary.
- Selected block details.
- AI-assisted flowgraph explanation.
- Connection and block inspection.
- Signal-flow understanding.

### 4. GNU Radio Block Inspection
- Inspect installed GNU Radio blocks.
- Examine block parameters and ports.
- Review stream types and connections.
- Inspect OFDM-related blocks in read-only mode.
- Use adapter-based inspection to gather information about the active flowgraph.

### 5. Flowgraph Validation and Troubleshooting
FlowPilot includes validation tools to identify potential configuration problems.

It can help identify:
- Undefined variables in block parameters.
- Invalid parameter expressions.
- Missing or disconnected input ports.
- Potential configuration issues.
- Structural flowgraph errors.
- Warnings that require engineering review.

It can also provide AI-assisted suggestions for resolving detected problems.

### 6. AI-Assisted Flowgraph Design
FlowPilot explores automated flowgraph development through:
- Auto-connecting selected compatible blocks.
- Building flowgraphs from research-paper design plans.
- Suggesting compatible block connections.
- Supporting engineering design workflows.

### 7. Live GRC Operations
FlowPilot includes tools for interacting with the active GRC environment.

These include:
- Live flowgraph inspection.
- Flowgraph validation.
- Block-level analysis.
- Design assistance.
- Controlled graph-operation support.

Graph modifications should be reviewed by the developer before being treated as final.

---

## AI and Model Integration

FlowPilot is designed to work with locally available language models.

### Model Used
- Qwen3 8B

The model is used for AI-assisted engineering explanations, flowgraph understanding, and troubleshooting support.

The system also includes deterministic processing for selected tasks, particularly research-paper passage matching and structural validation.

This combination helps distinguish between:
- Information directly supported by extracted technical documents.
- Results produced by deterministic validation.
- General AI-generated engineering suggestions.

---

## System Architecture

The overall workflow can be represented as:

1. **GNU Radio Companion Interface**
   - Hosts the FlowPilot assistant panel.
   - Provides access to engineering tools.

2. **Flowgraph Inspection Layer**
   - Reads active flowgraph information.
   - Inspects blocks, parameters, ports, and connections.

3. **Research Analysis Layer**
   - Processes uploaded research papers.
   - Extracts relevant text.
   - Retrieves matching passages for questions.

4. **AI Assistance Layer**
   - Uses the configured language model.
   - Explains technical concepts.
   - Supports design and troubleshooting.

5. **Validation Engine**
   - Checks structural conditions.
   - Evaluates block configurations.
   - Reports errors and warnings.

6. **Engineering Operations Layer**
   - Supports compatible block connections.
   - Assists with flowgraph construction.
   - Provides controlled GRC interaction.

---

## Technology Stack

- **GNU Radio Companion (GRC)** – Software-defined radio flowgraph development.
- **Python** – Extension development and engineering logic.
- **Qwen3 8B** – Local AI model integration.
- **Large Language Model (LLM) Integration** – AI-assisted explanations and engineering support.
- **PDF Text Extraction** – Research-paper processing.
- **Flowgraph Inspection** – Block, port, parameter, and connection analysis.
- **Validation Logic** – Configuration checks and error detection.

---

## Demonstrated Capabilities

The current development screenshots demonstrate:

- FlowPilot integrated into the GNU Radio Companion interface.
- Research-paper question answering.
- Local Qwen3 8B model selection.
- Flowgraph summary and block inspection tools.
- OFDM block inspection.
- Flowgraph validation.
- Detection of undefined variables such as `samp_rate`.
- Identification of invalid parameter expressions.
- Reporting of disconnected input ports.
- AI-assisted troubleshooting suggestions.

These demonstrations represent the current development state; individual tools and workflows may require further testing and refinement.

---

## Project Goals

The long-term vision of FlowPilot is to develop an AI-native engineering assistant for software-defined radio and signal-processing development.

Future development directions include:

- More advanced research-paper understanding.
- Improved contextual awareness of complex flowgraphs.
- Enhanced GNU Radio block compatibility analysis.
- Better automated flowgraph generation.
- More comprehensive parameter validation.
- Improved debugging and troubleshooting.
- Expanded support for SDR and DSP engineering workflows.

---

## Why FlowPilot?

Traditional flowgraph development requires users to understand individual blocks, their parameters, signal types, and connection requirements.

FlowPilot aims to reduce this learning and development overhead by combining research assistance, AI explanations, structural inspection, and validation within the engineering environment itself.

**The goal is not to replace the engineer, but to build an intelligent engineering copilot that helps the engineer understand, design, inspect, and improve GNU Radio systems.**

---

## Project Status

**Status:** Active Development / Research Prototype

FlowPilot is an evolving engineering project. Features are being developed and tested within GNU Radio Companion, with ongoing improvements to AI integration, validation, research analysis, and automated design support.

---


---

## Acknowledgement

Developed as an independent engineering project exploring the integration of artificial intelligence into software-defined radio development and research workflows.

**FlowPilot – Bringing AI Assistance into GNU Radio Engineering.**

## Vision

FlowPilot aims to redefine Software Defined Radio (SDR) engineering by combining Artificial Intelligence, Engineering Knowledge, Autonomous Planning, Code Generation, Validation, Runtime Execution, Continuous Learning, and Multi-Agent Collaboration into a unified engineering platform.

Rather than acting as a simple chatbot or code generator, FlowPilot functions as an intelligent engineering operating system capable of understanding engineering intent, planning complex workflows, generating GNU Radio projects, validating designs, executing SDR applications, and continuously improving through accumulated engineering knowledge.

The long-term vision is to create the world's first AI-native engineering platform for SDR development that enables students, researchers, and professionals to design advanced communication systems through natural language interaction while maintaining engineering correctness, transparency, and reproducibility.

---

# What is FlowPilot?

FlowPilot is an AI-powered engineering platform specifically designed for Software Defined Radio (SDR) engineering.

It combines multiple technologies into a single intelligent environment:

- Artificial Intelligence
- Large Language Models (LLMs)
- Engineering Knowledge Graphs
- Retrieval-Augmented Generation (RAG)
- Multi-Agent Systems
- GNU Radio Integration
- SDR Hardware Integration
- Cloud-Native Infrastructure
- Autonomous Engineering Workflows

FlowPilot assists users throughout the complete SDR engineering lifecycle, from requirement analysis to deployment.

---

# Core Capabilities

FlowPilot provides:

- Natural Language Engineering
- Autonomous Project Planning
- GNU Radio Flowgraph Generation
- Python Code Generation
- Engineering Validation
- Runtime Execution
- Knowledge Retrieval
- Engineering Recommendations
- Hardware Integration
- Continuous Learning
- Multi-Agent Collaboration
- Deployment Automation

---

# Supported Technologies

## Artificial Intelligence

- OpenAI GPT
- Qwen
- Embedding Models
- Retrieval-Augmented Generation (RAG)
- Engineering Knowledge Graphs

---

## SDR Frameworks

- GNU Radio
- UHD
- gr-iio
- gr-osmosdr

---

## SDR Hardware

- ADALM-Pluto
- USRP
- RTL-SDR
- HackRF
- LimeSDR

---

## Backend

- Python
- FastAPI
- Pydantic

---

## Frontend

- React
- TypeScript
- TailwindCSS

---

## Databases

- PostgreSQL
- Neo4j
- Qdrant
- Redis

---

## Infrastructure

- Docker
- Kubernetes
- GitHub Actions
- Prometheus
- Grafana

---

# Repository Structure

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
    thesis/
        Chapter01.md
        ...
        Chapter18.md

flowpilot/

frontend/

datasets/

examples/

tests/

docker/

scripts/

third_party/
```

---

# Architecture Overview

```
                 User
                   │
                   ▼
        Conversation Interface
                   │
                   ▼
            FlowPilot Core
                   │
      ┌────────────┼─────────────┐
      ▼            ▼             ▼
 Planner      Knowledge      Memory
      │            │             │
      └────────────┴─────────────┘
                   ▼
             Generator
                   ▼
             Validator
                   ▼
              Runtime
                   ▼
              Learning
                   ▼
            Deployment
```

The FlowPilot Core orchestrates every engineering workflow by coordinating the planning, generation, validation, runtime, learning, and deployment subsystems.

---

# Documentation

Project documentation is organized as follows:

| Document | Purpose |
|----------|---------|
| INTRODUCTION.md | Project vision and philosophy |
| SYSTEM_OVERVIEW.md | High-level system overview |
| ARCHITECTURE.md | Complete software architecture |
| PROJECT_STRUCTURE.md | Repository organization |
| TECH_STACK.md | Technology stack |
| DEVELOPMENT_ROADMAP.md | Development phases |
| AGENTS.md | AI agent specifications |
| WORKFLOWS.md | Engineering workflows |
| API_REFERENCE.md | REST API documentation |
| DATABASE_SCHEMA.md | Database design |
| KNOWLEDGE_SYSTEM.md | Knowledge architecture |
| CONTRIBUTING.md | Contribution guidelines |
| docs/thesis | Complete research thesis |

---

# Development Philosophy

FlowPilot follows the following principles:

- Modular Architecture
- AI-First Design
- Explainable Engineering
- Knowledge-Driven Reasoning
- Human-in-the-Loop Validation
- Cloud-Native Deployment
- Extensibility
- Engineering Reproducibility

---

# Current Development Status

Current implementation roadmap:

- Documentation
- Core Architecture
- Backend Services
- Frontend Interface
- Knowledge System
- Planning Engine
- Generator Engine
- Validation Engine
- Runtime Engine
- Learning Engine
- Deployment Platform

---

# Target Users

FlowPilot is designed for:

- SDR Engineers
- Communication Engineers
- AI Researchers
- GNU Radio Developers
- University Students
- Research Laboratories
- Wireless Communication Researchers
- Industrial Engineering Teams

---

# Long-Term Vision

FlowPilot aims to become the world's most advanced autonomous engineering platform for Software Defined Radio by combining engineering intelligence, artificial intelligence, autonomous workflows, and cloud-native infrastructure into a unified engineering ecosystem.

---

# License

This project is released under the MIT License unless otherwise specified.

---

# Contact

FlowPilot is an active research and engineering project focused on advancing autonomous Software Defined Radio engineering through Artificial Intelligence.

## Author

**Harsha Vardhan Reddy**  
B.Tech – Artificial Intelligence and Data Science  
Specialization: Cyber-Physical Systems and Security  
Amrita Vishwa Vidyapeetham, Coimbatore


---

**"Engineering Intelligence for the Next Generation of Software Defined Radio Systems."**
