# Chapter 4 – Agent AI Architecture

## 4.1 Introduction

FlowPilot adopts an Agentic Artificial Intelligence architecture in which the overall engineering workflow is divided among multiple specialized software agents. Each agent is responsible for a specific engineering function and collaborates with other agents to transform a user's natural language request into a validated GNU Radio Companion (GRC) project.

Unlike monolithic AI systems that attempt to solve every problem using a single model, the FlowPilot architecture separates reasoning into multiple autonomous agents. Each agent focuses on a well-defined responsibility, improving modularity, explainability, maintainability, and scalability.

The agent architecture allows FlowPilot to emulate the workflow of a team of SDR engineers, where each engineer specializes in planning, knowledge retrieval, implementation, validation, debugging, or learning.

---

# 4.2 Objectives of the Agent Architecture

The primary objectives of the agent architecture are:

- Divide complex engineering tasks into manageable responsibilities.
- Enable independent development and testing of each subsystem.
- Improve explainability by separating engineering decisions.
- Support future expansion through additional specialized agents.
- Allow integration of multiple AI models and external tools.
- Reduce coupling between software components.
- Improve maintainability and scalability.

---

# 4.3 Agent Classification

The agents within FlowPilot are organized into three categories.

## Control Agents

Control Agents coordinate the complete engineering workflow.

These agents are responsible for:

- Managing user interaction.
- Breaking complex requests into engineering tasks.
- Coordinating communication between engineering agents.
- Maintaining workflow state.

Current Control Agents include:

- Conversation Agent
- Task Manager Agent

---

## Engineering Agents

Engineering Agents perform SDR-specific reasoning and implementation.

Current Engineering Agents include:

- Planning Agent
- Knowledge Agent
- Generator Agent
- Validation Agent
- Runtime Agent
- Debugger Agent

These agents collaborate to design, validate, execute, and improve GNU Radio systems.

---

## Learning Agents

Learning Agents maintain long-term knowledge and improve system performance over time.

Current Learning Agents include:

- Memory Agent
- Learning Agent

These agents store engineering knowledge, project history, user preferences, execution results, and validated solutions.

---

# 4.4 High-Level Agent Architecture

The interaction between FlowPilot agents is illustrated below.

```text
                        USER
                          │
                          ▼
                 Conversation Agent
                          │
                          ▼
                  Task Manager Agent
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
 Planning Agent    Knowledge Agent    Memory Agent
        │                 │                 │
        └─────────────────┼─────────────────┘
                          ▼
                  Generator Agent
                          │
                          ▼
                  Validation Agent
                          │
                          ▼
                   Runtime Agent
                          │
                          ▼
                  Debugger Agent
                          │
                          ▼
                  Learning Agent
```

---

# 4.5 Conversation Agent

### Purpose

The Conversation Agent serves as the primary interface between the user and FlowPilot.

### Responsibilities

- Accept natural language requests.
- Maintain conversational context.
- Clarify ambiguous requirements.
- Forward structured tasks to the Task Manager.

### Inputs

- User prompts
- Follow-up questions
- Project updates

### Outputs

- Structured engineering requests

---

# 4.6 Task Manager Agent

### Purpose

The Task Manager coordinates all engineering activities performed by FlowPilot.

### Responsibilities

- Receive structured tasks.
- Decompose complex requests.
- Assign tasks to appropriate engineering agents.
- Monitor workflow progress.
- Collect intermediate results.

---

# 4.7 Planning Agent

### Purpose

The Planning Agent determines the engineering strategy required to satisfy the user's request.

### Responsibilities

- Identify communication systems.
- Design DSP pipelines.
- Determine processing stages.
- Generate engineering plans.

The Planning Agent does not select GNU Radio blocks directly. Instead, it defines engineering capabilities required for implementation.

---

# 4.8 Knowledge Agent

### Purpose

The Knowledge Agent provides engineering knowledge required by all other agents.

### Responsibilities

- Capability search.
- Semantic search.
- Documentation retrieval.
- Knowledge graph traversal.
- Engineering reasoning.
- Ranking candidate blocks.

Unlike conventional search systems, the Knowledge Agent searches by engineering capability rather than block names.

---

# 4.9 Generator Agent

### Purpose

The Generator Agent transforms engineering plans into executable GNU Radio flowgraphs.

### Responsibilities

- Request GNU Radio blocks from the Knowledge Agent.
- Generate variables.
- Generate blocks.
- Generate connections.
- Configure parameters.
- Export GNU Radio Companion projects.

The Generator Agent does not contain hardcoded GNU Radio block mappings.

---

# 4.10 Validation Agent

### Purpose

The Validation Agent verifies engineering correctness before runtime execution.

### Responsibilities

- Verify topology.
- Check port compatibility.
- Validate parameters.
- Detect missing components.
- Identify incompatible GNU Radio versions.

---

# 4.11 Runtime Agent

### Purpose

The Runtime Agent executes generated GNU Radio projects.

### Responsibilities

- Launch GNU Radio.
- Monitor execution.
- Capture runtime logs.
- Detect runtime failures.
- Measure execution performance.

---

# 4.12 Debugger Agent

### Purpose

The Debugger Agent analyzes engineering failures.

### Responsibilities

- Parse runtime errors.
- Identify faulty blocks.
- Recommend engineering corrections.
- Support automatic repair.

Future versions will support autonomous regeneration of failed flowgraphs.

---

# 4.13 Memory Agent

### Purpose

The Memory Agent maintains project knowledge across conversations and engineering sessions.

### Responsibilities

- Store project history.
- Maintain conversation context.
- Record engineering decisions.
- Preserve user preferences.

---

# 4.14 Learning Agent

### Purpose

The Learning Agent continuously improves the engineering capabilities of FlowPilot.

### Responsibilities

- Store successful projects.
- Analyze execution statistics.
- Improve block rankings.
- Update engineering knowledge.
- Learn from user feedback.

---

# 4.15 Agent Communication

Agents communicate using structured requests and responses rather than direct implementation dependencies.

This design ensures that individual agents can be upgraded or replaced without affecting the overall architecture.

Each agent exposes a well-defined interface consisting of:

- Input specification
- Output specification
- Status reporting
- Error reporting

This standardized communication model simplifies integration and testing.

---

# 4.16 Design Principles

The FlowPilot agent architecture follows the following principles:

- Single Responsibility Principle
- Loose Coupling
- High Cohesion
- Explainability
- Extensibility
- Fault Isolation
- Reusability

These principles ensure that the system remains scalable as new engineering capabilities are introduced.

---

# 4.17 Chapter Summary

This chapter introduced the Agent Architecture used by FlowPilot. The architecture divides complex SDR engineering tasks among specialized autonomous agents, enabling modular development, explainable AI reasoning, scalable system design, and future expansion through additional engineering capabilities.

The next chapter describes the Engine Architecture, explaining how each software engine provides the deterministic implementation required by the autonomous agents.