# Chapter 3 – Overall System Architecture

## 3.1 Introduction

The Overall System Architecture defines the high-level organization of the FlowPilot platform and explains how the major software components collaborate to transform a user's natural language request into a fully functional GNU Radio Companion (GRC) project.

FlowPilot follows a modular, layered, and agent-oriented architecture. Instead of relying on a single monolithic program, the system is divided into multiple independent components, each responsible for a specific engineering task. This design improves scalability, maintainability, testing, and future extensibility while allowing new technologies, communication standards, and AI models to be integrated with minimal changes to the existing architecture.

The architecture separates user interaction, intelligent reasoning, engineering knowledge, project generation, validation, execution, and learning into dedicated modules. Each module communicates with other modules through clearly defined interfaces, ensuring loose coupling and high cohesion.

---

# 3.2 Architectural Goals

The architecture of FlowPilot has been designed to achieve the following objectives:

- Provide an intuitive natural language interface for SDR engineering.
- Separate AI reasoning from deterministic engineering logic.
- Support multiple GNU Radio versions and SDR hardware platforms.
- Enable modular development and independent testing of subsystems.
- Minimize hardcoded engineering knowledge.
- Support continuous learning through accumulated engineering knowledge.
- Provide explainable engineering decisions.
- Allow future integration with additional AI models and plugins.

---

# 3.3 Architectural Style

FlowPilot adopts a layered architecture combined with an agent-oriented design.

The layered architecture separates responsibilities into independent levels, while the agent-oriented approach assigns specialized engineering tasks to autonomous software agents.

The architecture consists of the following layers:

1. User Interface Layer
2. Application Layer
3. Agent Layer
4. Engine Layer
5. Knowledge Layer
6. Runtime Layer
7. Data Layer

Each layer communicates only through well-defined interfaces, reducing dependencies between components.

---

# 3.4 High-Level System Architecture

The overall FlowPilot architecture is illustrated below.

```text
                           USER
                             │
                             ▼
                     Base44 / Web Interface
                             │
                             ▼
                     FastAPI Backend Server
                             │
                             ▼
                  Conversation Interface
                             │
                             ▼
                  Conversation Agent
                             │
                             ▼
                    Task Manager Agent
                             │
       ┌─────────────────────┼─────────────────────┐
       ▼                     ▼                     ▼
 Planning Agent      Knowledge Agent       Memory Agent
       │                     │                     │
       └─────────────────────┼─────────────────────┘
                             ▼
                   Knowledge Service Layer
                             │
     ┌───────────────┬───────────────┬───────────────┐
     ▼               ▼               ▼
Capability Search  Semantic Search  Knowledge Graph
     │               │               │
     └───────────────┴───────────────┘
                     │
                     ▼
               Ranking Engine
                     │
                     ▼
              Reasoning Engine
                     │
                     ▼
             Generator Engine
                     │
                     ▼
             Validation Engine
                     │
                     ▼
               Runtime Engine
                     │
                     ▼
              Debugger Engine
                     │
                     ▼
              Learning Engine
                     │
                     ▼
            Knowledge Database
```

---

# 3.5 Major System Components

The FlowPilot platform consists of several major subsystems.

## User Interface

The User Interface provides the primary interaction point between the user and FlowPilot. Users communicate with the system using natural language rather than manually constructing GNU Radio flowgraphs.

Future implementations may include a web application, desktop interface, and conversational assistant.

---

## FastAPI Backend

The backend exposes REST APIs that connect the user interface with the internal AI system.

Responsibilities include:

- Request management
- Session handling
- Authentication (future)
- API communication
- Response generation

---

## Conversation Agent

The Conversation Agent interprets user requests and converts natural language into structured engineering tasks.

Example:

User Input:

> Build an FM Receiver using PlutoSDR.

Structured Task:

- Communication Type: FM Receiver
- Hardware: PlutoSDR
- Output: GNU Radio Flowgraph

---

## Planning Agent

The Planning Agent determines the Digital Signal Processing pipeline required to implement the requested communication system.

Rather than selecting blocks directly, the planner identifies engineering stages such as signal acquisition, filtering, demodulation, synchronization, decoding, and output generation.

---

## Knowledge Agent

The Knowledge Agent provides engineering knowledge required by the planner, generator, validator, debugger, and runtime components.

Instead of relying on hardcoded block mappings, the Knowledge Agent retrieves information from the FlowPilot Knowledge Base using semantic and capability-based search.

---

## Generator Engine

The Generator Engine converts engineering plans into executable GNU Radio Companion projects.

Its responsibilities include:

- Block selection
- Variable generation
- Connection generation
- Parameter assignment
- Layout generation
- YAML export

---

## Validation Engine

The Validation Engine analyzes the generated flowgraph before execution.

Validation includes:

- Port compatibility
- Data type compatibility
- Missing parameters
- Invalid connections
- Hardware compatibility
- GNU Radio version compatibility

---

## Runtime Engine

The Runtime Engine executes the generated GNU Radio project and monitors system behavior.

Responsibilities include:

- Project execution
- Runtime monitoring
- Log collection
- Performance analysis
- Error detection

---

## Debugger Engine

The Debugger Engine analyzes execution failures and recommends engineering corrections.

Future versions may support automatic repair and regeneration of invalid flowgraphs.

---

## Learning Engine

The Learning Engine enables FlowPilot to improve over time.

Successful projects, execution results, user feedback, and validated engineering knowledge may be incorporated into the knowledge base to improve future recommendations.

---

# 3.6 Design Principles

The architecture of FlowPilot follows the following engineering principles:

### Modularity

Each subsystem performs one primary responsibility and can be developed independently.

### Scalability

The architecture supports future GNU Radio releases, additional SDR hardware, and larger engineering knowledge bases without requiring major redesign.

### Extensibility

New AI models, plugins, communication standards, and GNU Radio modules can be integrated through well-defined interfaces.

### Explainability

Engineering decisions produced by the AI should be transparent and understandable to users.

### Maintainability

Clear separation between agents, engines, and data allows individual components to be updated without affecting the overall system.

---

# 3.7 Architectural Workflow

The complete FlowPilot workflow is summarized below.

1. The user submits an engineering request in natural language.
2. The Conversation Agent interprets the request.
3. The Planning Agent determines the required DSP processing stages.
4. The Knowledge Agent retrieves relevant GNU Radio engineering knowledge.
5. The Generator Engine constructs the GNU Radio flowgraph.
6. The Validation Engine verifies the generated project.
7. The Runtime Engine executes the flowgraph.
8. The Debugger Engine analyzes any runtime failures.
9. The Learning Engine stores useful engineering knowledge for future use.

---

# 3.8 Chapter Summary

This chapter presented the overall architecture of the FlowPilot platform and described the responsibilities of its primary software components. The modular, layered, and agent-oriented architecture provides a scalable foundation for autonomous GNU Radio engineering while supporting future expansion through plugins, additional AI models, and continuous knowledge evolution.

The following chapter introduces the Agent Architecture, describing the responsibilities, interactions, and communication mechanisms of each autonomous agent within the FlowPilot platform.