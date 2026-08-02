# Chapter 5 – Engine Architecture

## 5.1 Introduction

The Engine Architecture represents the core implementation layer of the FlowPilot platform. While the Agent Layer is responsible for reasoning, decision-making, and workflow coordination, the Engine Layer performs the deterministic engineering operations required to transform user requirements into executable GNU Radio Companion (GRC) projects.

Each engine is designed as an independent software component responsible for a specific engineering task. This separation ensures modularity, maintainability, scalability, and ease of testing.

Unlike agents, engines do not make autonomous decisions. Instead, they execute well-defined algorithms and expose reusable interfaces that can be invoked by one or more agents.

---

# 5.2 Objectives of the Engine Architecture

The Engine Architecture has been designed with the following objectives:

- Separate engineering logic from AI reasoning.
- Promote reusable software components.
- Support independent development and testing.
- Minimize coupling between subsystems.
- Enable future replacement or extension of engines.
- Maintain deterministic and predictable execution.
- Provide stable APIs for higher-level agents.

---

# 5.3 Engine Overview

FlowPilot consists of multiple specialized engines that together implement the SDR engineering workflow.

The primary engines are:

- AI Core
- Knowledge Engine
- Planner Engine
- Generator Engine
- Validation Engine
- Runtime Engine
- Debugger Engine
- Learning Engine

Each engine performs a dedicated engineering responsibility while communicating through well-defined interfaces.

---

# 5.4 High-Level Engine Architecture

```text
                     Agent Layer
                          │
                          ▼
                 ┌─────────────────────┐
                 │    Engine Layer     │
                 └─────────────────────┘
                          │
     ┌──────────┬──────────┬──────────┬──────────┐
     ▼          ▼          ▼          ▼          ▼
 AI Core   Knowledge   Planner   Generator   Validator
                                      │
                                      ▼
                                  Runtime
                                      │
                                      ▼
                                  Debugger
                                      │
                                      ▼
                                  Learning
```

The engines communicate through service interfaces and shared data models rather than direct implementation dependencies.

---

# 5.5 AI Core

### Purpose

The AI Core provides common infrastructure used by all FlowPilot engines.

### Responsibilities

- Configuration management
- Logging
- Exception handling
- Utility functions
- Shared data models
- Common interfaces
- Environment configuration

The AI Core serves as the foundation upon which all other engines are built.

---

# 5.6 Knowledge Engine

### Purpose

The Knowledge Engine serves as the engineering knowledge repository of FlowPilot.

### Responsibilities

- Parse GNU Radio metadata
- Build searchable indexes
- Capability-based search
- Semantic retrieval
- Ranking
- Knowledge graph management
- Documentation retrieval
- Recommendation generation

The Knowledge Engine does not generate projects directly. Instead, it supplies engineering knowledge to other engines.

---

# 5.7 Planner Engine

### Purpose

The Planner Engine converts user requirements into engineering plans.

### Responsibilities

- Requirement analysis
- DSP pipeline planning
- Engineering stage identification
- Hardware planning
- Constraint analysis
- Project decomposition

The planner focuses on engineering strategy rather than implementation details.

---

# 5.8 Generator Engine

### Purpose

The Generator Engine transforms engineering plans into executable GNU Radio Companion projects.

### Responsibilities

- Variable generation
- Block generation
- Connection generation
- Parameter configuration
- Layout generation
- YAML export

Unlike traditional generators, FlowPilot does not rely on hardcoded GNU Radio block mappings. Instead, it requests engineering knowledge from the Knowledge Engine.

---

# 5.9 Validation Engine

### Purpose

The Validation Engine verifies the correctness of generated flowgraphs before execution.

### Responsibilities

- Port validation
- Parameter validation
- Data type validation
- Version compatibility
- Hardware compatibility
- Structural verification

Validation reduces runtime failures by detecting engineering issues before execution.

---

# 5.10 Runtime Engine

### Purpose

The Runtime Engine executes generated GNU Radio projects.

### Responsibilities

- Launch GNU Radio
- Execute flowgraphs
- Monitor execution
- Capture logs
- Measure performance
- Detect runtime failures

The Runtime Engine acts as the execution bridge between FlowPilot and GNU Radio.

---

# 5.11 Debugger Engine

### Purpose

The Debugger Engine analyzes runtime failures and assists in correcting engineering problems.

### Responsibilities

- Error analysis
- Log interpretation
- Root cause identification
- Repair recommendations
- Automatic recovery (future)

The Debugger Engine improves system reliability by reducing manual troubleshooting.

---

# 5.12 Learning Engine

### Purpose

The Learning Engine enables continuous improvement of the FlowPilot platform.

### Responsibilities

- Store successful engineering solutions
- Update block rankings
- Learn from execution results
- Record user feedback
- Improve future recommendations

The Learning Engine ensures that FlowPilot evolves as additional projects and engineering knowledge become available.

---

# 5.13 Engine Communication

The engines communicate using standardized service interfaces rather than direct implementation dependencies.

Typical communication flow:

1. The Planner Engine requests engineering knowledge.
2. The Knowledge Engine retrieves and ranks candidate solutions.
3. The Generator Engine constructs the flowgraph.
4. The Validation Engine verifies correctness.
5. The Runtime Engine executes the project.
6. The Debugger Engine analyzes failures.
7. The Learning Engine stores useful engineering knowledge.

This communication model simplifies integration and future maintenance.

---

# 5.14 Design Principles

The Engine Architecture follows the following software engineering principles:

- Single Responsibility Principle
- Separation of Concerns
- High Cohesion
- Loose Coupling
- Reusability
- Extensibility
- Maintainability
- Testability

These principles ensure that each engine remains focused on its specific engineering role.

---

# 5.15 Chapter Summary

This chapter presented the Engine Architecture of FlowPilot and described the responsibilities of each engine within the platform. The Engine Layer forms the deterministic implementation foundation of the system, enabling the Agent Layer to perform intelligent reasoning while relying on stable, reusable engineering services.

The next chapter introduces the Knowledge System, which serves as the engineering knowledge foundation for planning, generation, validation, debugging, and continuous learning.