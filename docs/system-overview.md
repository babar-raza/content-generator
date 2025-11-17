# UCOP System Overview (Living Document)

---

## 1. Purpose of the System

UCOP is a **multi-agent content generation system** whose primary goal is to produce:

* High-quality technical content with **C# code snippets**
* For multiple content types:

  * Knowledge base articles
  * Product / feature documentation
  * Tutorials and how-to guides
  * API-reference-driven articles

The system outputs content using **structured templates**, usually made of:

* Frontmatter (metadata)
* Main body
* Code example(s)
* Code steps / narrative walkthrough
* FAQ
* Learn more / related links

All of this is driven by **30+ cooperating agents**, orchestrated in different modes.

---

## 2. High-Level Architecture

At a high level, the system looks like this:

```text
User (CLI / Web UI)
        │
        ▼
 Orchestration Layer (workflows, mesh, visual graph)
        │
        ▼
  Agent Mesh (30+ agents with contracts)
        │
        ▼
  Services & Engines (templates, validation, vector store, dup check)
        │
        ▼
   LLMs + Storage (Ollama / cloud LLMs, file system, embeddings)
```

Key properties:

* **Multi-agent**: each agent has a narrow responsibility and a clear contract.
* **Multi-mode orchestration**: workflows, mesh-like interactions, and a visual graph mode.
* **Multi-source ingestion**: user can provide one or more directories for KB, docs, blogs, tutorials, API reference, etc.
* **Multi-LLM capability**: local models (e.g. Ollama) plus external providers when needed.

---

## 3. Agents and Contracts

### 3.1 Agent Set

* There are **30+ agents** in the system (roughly a few dozen).
* They cover:

  * Content generation (outline → sections → conclusion → extras)
  * SEO and metadata
  * Code snippet generation and validation
  * Ingestion and indexing
  * Duplication and similarity checking
  * Quality and completeness gating
  * Publishing (frontmatter, slug, file writing)

### 3.2 Agent Contracts

Each agent is defined by a **contract**, which specifies:

* **Inputs**
  What the agent expects (topic, outline, text, embeddings, config, etc.).
* **Outputs**
  What it returns (sections of content, code snippets, diagnostics, links, etc.).
* **Assumptions / Preconditions**
  For example:

  * Requires ingested API reference context
  * Requires that a topic has already been identified
  * Requires a previous agent’s output

Because agents can be orchestrated in many ways, the contract is the stable boundary that keeps the system composable.

> **Invariant:**
> An agent’s behavior and contract must be consistent regardless of orchestration mode (workflow, mesh, visual graph).

---

## 4. Orchestration Modes

Agents can work together in three main modes.

### 4.1 Predefined Workflow Mode

* Workflows define a **fixed path** of agents:

  * “Ingest → Analyze → Plan → Generate → Validate → Publish”
* Typical use:

  * Standard KB article generation
  * Standard tutorial generation
  * Standard API-driven code snippet article

Characteristics:

* Predictable and repeatable
* Easier to test end-to-end
* Good for production pipelines

### 4.2 Mesh Mode

In mesh mode, the system behaves more like a **network of peers**:

* Agents can request data from other agents as needed (directly or through shared stores).
* Data flows are **demand-driven** instead of purely pre-wired.
* Useful for:

  * Research tasks
  * Complex, multi-step reasoning
  * Adaptive content refinement

This matches your requirement that agents can “ask for needed data from fellow agents” while still respecting contracts.

### 4.3 Visual Workflow Mode

A visual mode allows agents to be wired **on a graph / canvas**, then executed:

* Nodes = agents
* Edges = data or control flow
* The visual graph can be:

  * Designed, edited, and saved by the user
  * Executed to run a job
  * Observed to see which agent is doing what

This is effectively a visual frontend over the same orchestration engine, aligned with LangChain / LangGraph style workflows.

---

## 5. Jobs and Execution

### 5.1 Jobs

A **job** is the unit of work in the system. Typically:

* Inputs:

  * One or more ingestion directories (KB/docs/blog/tutorial/API ref)
  * Generation options (content type, templates, tone, target product, etc.)
* Outputs:

  * One or more content artifacts (e.g., a Markdown file with C# code)

Every job must:

* End in a clear state:

  * Succeeded
  * Failed
  * Retrying
  * Deleted / archived
* Produce either:

  * A valid, written output artifact, **or**
  * A structured error that can be inspected and retried

### 5.2 Job Lifecycle

Conceptually:

1. **Queued / Pending**
2. **Running**
3. **Succeeded** (output written, logs and metrics attached)
4. **Failed** (error captured, state recorded)
5. **Retryable / Retried** (can restart from a checkpoint or from scratch)
6. **Deleted / Archived** (cleaned up from the active set)

> **Design requirement:**
> If a job errors, it must be either **retryable** or **deletable**; there should be no stuck or ghost jobs.

---

## 6. Content Model and Templates

Generated content is **template-driven**. A typical template includes:

1. **Frontmatter**

   * Title, slug, tags, product, category, language, etc.
2. **Body**

   * Introduction, main sections, conclusion.
3. **Code Example(s)**

   * C# snippets derived from API reference and/or other sources.
4. **Code Steps**

   * Human-readable walkthrough of the code.
5. **FAQ**

   * Commonly asked questions and answers.
6. **Learn More / Links**

   * Links back to KB, docs, tutorials, and API reference.

Multiple agents cooperate to populate these sections:

* Planning / outline agents
* Section writers
* Code generation / validation agents
* SEO / metadata agents
* Duplication and link-back agents
* Final assembly / publishing agents

---

## 7. Ingestion Model and Rules

Users can provide **one, two, or many directories** as ingestion sources. These are generally of the following types:

* API reference
* Blog
* KB (knowledge base)
* Product docs
* Tutorials

Your rules for how these are used are critical to the system’s behavior.

### 7.1 API Reference Ingestion

**Rule 1 – API Reference is code-centric**

* API Reference ingestion is **only** used to create **code snippets** and code-related understanding.
* It powers:

  * C# code examples
  * Code correctness and API usage
  * Parameter and return-type awareness
* It is **not** used as the main source for:

  * Topic discovery
  * Non-code narrative content (intro/body/FAQ etc.)

API reference is effectively the **ground truth** for the code section.

### 7.2 Non-API Ingestion (Blog, KB, Docs, Tutorials)

**Rule 2 – Topic discovery**

* All **non-API** ingestion sources (blog, KB, docs, tutorials) can be used to **discover or hint topics** to generate content about.

  * Example:

    * Blog posts or KB articles suggest emerging topics or gaps.
    * Docs can suggest related tasks users need guides for.

**Rule 3 – Content sources for all sections**

* These same **non-API** sources may be used to generate content for **any subsection** of the output template, including:

  * Frontmatter (title, tags, categories)
  * Main body sections
  * FAQ content
  * “Learn more” supporting text
* They can supply:

  * Terminology
  * Best practices
  * Narrative structure
  * Examples and edge cases (non-code)

In short: **non-API sources feed both topic selection and rich narrative content.**

### 7.3 Linking and Cross-References

**Rule 4 – Link-back from all ingestions**

* **All ingestion types** (API reference, blogs, KB, docs, tutorials) can be used to **link back** in the final output.

  * For example:

    * “Learn more” links to existing KB or docs.
    * Inline links in body content referencing original docs.
    * Code samples linking to the originating API reference page.

This ensures generated content is **anchored back** to your existing knowledge assets.

### 7.4 Duplication Check and Output Section Target

**Rule 5 – Output section option for duplication checks**

* The system must allow an **“output section option”** that controls how **DuplicationCheckAgent** operates.
* Behavior:

  * The user (or workflow config) can choose which **output section(s)** to compare for duplication against already ingested content:

    * Entire article
    * Title only
    * Intro/body only
    * FAQ only
    * A combination (e.g., title + headings)
  * DuplicationCheckAgent then:

    * Uses embeddings / similarity search on the chosen section(s).
    * Checks against ingested non-API sources (blog/KB/docs/tutorial) and/or previous outputs.
    * Flags:

      * Exact duplicates
      * Near duplicates
      * Strongly overlapping topics

This ties ingestion, topic discovery, and duplication into a coherent flow:

1. Non-API ingestion: **suggests topics**
2. System proposes outputs (with selected output section option)
3. DuplicationCheckAgent: checks new topics/output sections against:

   * The newly discovered topics
   * Existing artifacts in the ingested sources
4. Output: either green-lit content or flagged as too similar

---

## 8. Communication and MCP

All agent coordination and job management is intended to flow through **MCP-style interfaces**:

* Agents are invoked via a consistent protocol.
* Job, workflow, checkpoint, and config operations are exposed via MCP endpoints.
* CLI and Web UI should both talk to the same MCP layer (or a compatible façade).

Design goals:

* A single communication layer for:

  * Agents
  * Workflows
  * Jobs
  * Checkpoints
  * Monitoring / health
* Easy plugin / tool integration (other systems can trigger jobs or query agents via MCP).

---

## 9. Monitoring, Health, and Observability

### 9.1 Agent Health

For each agent, the system should be able to surface:

* Current status:

  * Idle / running / degraded / failing
* Recent activity:

  * Last inputs (sanitized)
  * Last outputs (or summaries)
  * Error details if any

There is (or should be):

* A **visual way** to monitor agent activity.
* An **Agents page** that lists all agents and shows:

  * Which agents are active in current jobs
  * Their recent history and health

### 9.2 Job and Workflow Monitoring

* Job dashboards showing:

  * Status, duration, agents used, errors.
* Workflow / graph view:

  * Which agents ran in which order
  * Where any failure occurred
* Logs and metrics aligned:

  * Makes debugging and performance tuning possible.

---

## 10. Configuration and Extensibility

Configuration should capture:

* **Ingestion sources**

  * Directories per type: API ref, blog, KB, docs, tutorials.
* **Orchestration mode**

  * Which workflow or visual graph to run.
* **Template and output options**

  * Which sections are required
  * “Output section option” for duplication checking.
* **LLM and provider settings**

  * Model names, timeouts, fallbacks.
* **Agent toggles**

  * Enable/disable certain agents for specific workflows.

Extending the system typically means:

* Adding a new agent with a clear contract.
* Registering it in a workflow (or wiring it into the mesh).
* Updating configs to expose it via CLI/Web/MCP.

---

## 11. Invariants and Design Intent

To keep the system coherent:

1. **Agent behavior is contract-driven**
   Same contract, regardless of orchestration mode.

2. **Jobs are never “mysteriously stuck”**
   They always end in a traceable state and are retryable or deletable.

3. **Ingestion rules are respected**

   * API reference → code only.
   * Non-API → topic discovery + narrative content.
   * All ingestions → link-back candidates.

4. **Duplication is intentional, not accidental**
   The duplication check is explicitly configured via the **output section option** and runs against the right sources.

5. **Monitoring is first-class**
   Agents, jobs, and workflows must be observable through the visual UI and via structured logs/metrics.
