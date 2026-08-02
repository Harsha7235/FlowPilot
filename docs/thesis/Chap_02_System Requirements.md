# Chapter 2 – System Requirements

## 2.1 Introduction

This chapter defines the functional and non-functional requirements of the FlowPilot platform. These requirements describe the expected behavior, system capabilities, performance objectives, quality attributes, software dependencies, hardware requirements, and design constraints that guide the development of the entire system.

The requirements presented in this chapter establish the foundation for all architectural and implementation decisions described in subsequent chapters.

---

# 2.2 Functional Requirements

The functional requirements describe the operations that FlowPilot must perform in order to achieve its objective of autonomous GNU Radio engineering.

## FR-1 Natural Language Understanding

The system shall accept engineering requirements expressed in natural language.

Examples include:

- Build an FM Receiver using PlutoSDR.
- Design an OFDM Transmitter.
- Create a QPSK Communication System.
- Generate a Spectrum Analyzer.

The system shall extract:

- Project type
- Communication standard
- SDR hardware
- Constraints
- User preferences
- Required outputs

---

## FR-2 Engineering Planning

The system shall analyze user requirements and automatically determine the Digital Signal Processing (DSP) pipeline required to implement the requested communication system.

The planner shall:

- Identify DSP stages.
- Determine required signal transformations.
- Select processing sequence.
- Determine engineering constraints.

---

## FR-3 Knowledge Retrieval

The system shall retrieve GNU Radio engineering knowledge from multiple knowledge sources.

Supported knowledge sources include:

- GNU Radio XML definitions
- GNU Radio YAML definitions
- Python block implementations
- Official documentation
- Example flowgraphs
- Research papers
- User-generated knowledge

The retrieval engine shall support semantic search and capability-based search.

---

## FR-4 Block Selection

The system shall automatically select GNU Radio blocks based on engineering capability instead of fixed block mappings.

The selection process shall consider:

- DSP capability
- Port compatibility
- Parameter compatibility
- Hardware compatibility
- GNU Radio version
- Performance ranking

---

## FR-5 Flowgraph Generation

The system shall automatically generate complete GNU Radio Companion (.grc) projects.

Generated projects shall include:

- Variables
- Blocks
- Connections
- Parameters
- Metadata
- Layout information

---

## FR-6 Flowgraph Validation

Before execution, the generated flowgraph shall be validated.

Validation shall include:

- Port compatibility
- Data type compatibility
- Missing blocks
- Invalid parameters
- Hardware compatibility
- Topology correctness

---

## FR-7 Runtime Execution

The system shall execute generated GNU Radio flowgraphs automatically.

The runtime engine shall:

- Launch GNU Radio
- Monitor execution
- Capture runtime logs
- Detect execution failures
- Collect performance statistics

---

## FR-8 Debugging

The system shall analyze runtime failures and identify possible engineering solutions.

The debugger shall:

- Parse error messages
- Identify faulty blocks
- Detect invalid parameters
- Recommend corrective actions
- Support automatic repair where possible

---

## FR-9 Knowledge Learning

The system shall continuously improve its knowledge base.

Successful projects may be stored as reusable engineering knowledge.

Learning sources include:

- Generated projects
- Execution results
- User feedback
- Research papers
- Documentation updates

---

## FR-10 Explainability

FlowPilot shall explain every engineering decision made during project generation.

Examples include:

- Why a block was selected.
- Why a parameter was chosen.
- Why an alternative was rejected.
- Why validation failed.

---

# 2.3 Non-Functional Requirements

## NFR-1 Performance

- User response time should remain interactive.
- Knowledge retrieval should be efficient.
- Flowgraph generation should complete within reasonable time.
- Validation should occur before runtime execution.

---

## NFR-2 Scalability

The architecture shall support:

- Thousands of GNU Radio blocks.
- Multiple GNU Radio versions.
- Additional SDR hardware.
- Large engineering knowledge bases.
- Future AI models.

---

## NFR-3 Modularity

Each subsystem shall be implemented independently.

Examples:

- Knowledge Engine
- Planner Engine
- Generator Engine
- Runtime Engine
- Debugger Engine

A modification to one engine should not require redesign of unrelated engines.

---

## NFR-4 Extensibility

FlowPilot shall support future extensions including:

- New GNU Radio releases.
- New Out-of-Tree (OOT) modules.
- Additional communication standards.
- Custom plugins.
- New AI models.

---

## NFR-5 Reliability

The system shall perform engineering validation before runtime execution.

Generated projects should minimize runtime failures through automated validation and compatibility checking.

---

## NFR-6 Maintainability

The software architecture shall promote:

- Clean module separation.
- Well-defined APIs.
- Reusable components.
- Comprehensive documentation.
- Unit testing.

---

## NFR-7 Explainability

Engineering decisions produced by AI shall be transparent and traceable.

Users should understand:

- Why decisions were made.
- Which knowledge sources were used.
- Which engineering assumptions were applied.

---

## NFR-8 Portability

FlowPilot should support:

- Windows
- Linux

Future support may include:

- macOS

---

# 2.4 Software Requirements

The recommended software environment includes:

- Python 3.10+
- GNU Radio 3.10+
- FastAPI
- SQLite
- ChromaDB or FAISS
- NetworkX
- Sentence Transformers
- Git
- Docker (future)
- Base44 (Frontend)

---

# 2.5 Hardware Requirements

Development System

- Intel Core i7 or equivalent
- 16 GB RAM (minimum)
- NVIDIA RTX GPU (recommended)
- SSD Storage

Supported SDR Hardware

- PlutoSDR
- RTL-SDR
- HackRF
- USRP

Future hardware support can be added through the plugin architecture.

---

# 2.6 Design Constraints

The FlowPilot architecture shall satisfy the following constraints:

- GNU Radio remains the execution environment.
- AI shall assist engineering decisions rather than replace GNU Radio.
- Components shall communicate through well-defined interfaces.
- The system shall avoid hardcoded GNU Radio block mappings wherever possible.
- Knowledge retrieval shall be capability-driven rather than name-driven.
- Future extensions shall require minimal architectural changes.

---

# 2.7 Assumptions

The following assumptions are made during system design:

- GNU Radio is installed on the target system.
- Required SDR drivers are available.
- Python environment is properly configured.
- Knowledge databases are periodically updated.
- Users provide engineering requirements using natural language.

---

# 2.8 Chapter Summary

This chapter defined the functional and non-functional requirements governing the design of FlowPilot. These requirements establish the expected capabilities, performance objectives, architectural constraints, and engineering goals that guide the development of the Agentic AI SDR Engineering Assistant.