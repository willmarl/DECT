# DECT — Don’t Enjoy Creating Tests?

DECT is a QA automation project that takes functional requirements (PDFs)
and generates test artifacts step by step using LangChain + LangGraph.

---

## 🔹 Goal of the Project

Automate the boring parts of QA test design:

- Break requirements into atomic blocks.
- Generate equivalence partitions & boundary values.
- Produce concrete test data & organized test sets.
- Output executable test cases in Markdown/CSV.

---

## 🔹 Vision / Example

1. upload pdf files to give context to LLM
2. tell it what FR to do "You are tasked to do FR-1 and FR-3"

DECT will produce:

- Atomic breakdown
- Partition tables
- Boundary values
- Concrete test data
- Deduped test list
- Organized equivalence classes
- Final test cases (ready for Jira/TestRail)

```mermaid
flowchart TD

    subgraph UI["Gradio Web UI"]
        A[Upload PDF]
        B[Select FR tasks: e.g. FR-1, FR-3]
        C[Show live progress for each step]
        D["Download final outputs (tables, test cases)"]
    end

    A -->|Send PDF| P1[Preprocess.py]

    subgraph Preprocess
        P1 --> P2["Extract full text (global_requirements.txt)"]
        P1 --> P3["Split by FR (fr1.txt, fr2.txt...)"]
        P1 --> P4["(Optional) Embed chunks into Vector DB (Chroma)"]
    end

    B -->|Task FR-1| G1[LangGraph Pipeline for FR-1]
    B -->|Task FR-3| G2[LangGraph Pipeline for FR-3]

    subgraph LangGraph Pipeline
        direction LR
        S1[Step 1: Atomic Blocks] --> S2[Step 2: Partitions]
        S2 --> S3[Step 3: Boundaries]
        S3 --> S4[Step 4: Test Values]
        S4 --> S5[Step 5: Unified List]
        S5 --> S6[Step 6: Deduped List]
        S6 --> S7[Step 7: Organized Data]
        S7 --> S8[Step 8: Test Cases]
    end

    %% Context injection
    P2 -->|Global Context| G1
    P3 -->|Local FR text| G1
    P4 -->|"Relevant Chunks (if needed)"| G1

    P2 -->|Global Context| G2
    P3 -->|Local FR text| G2
    P4 -->|"Relevant Chunks (if needed)"| G2

    G1 -->|Save step files| O1[output/fr1/]
    G2 -->|Save step files| O2[output/fr3/]

    O1 --> C
    O2 --> C
    C --> D

```

---

## 🔹 Tech Stack

- Python 3.13+
- [LangChain](https://python.langchain.com/)
- [LangGraph](https://github.com/langchain-ai/langgraph)
- [Gradio](https://www.gradio.app/) — simple local UI for running steps
- [Ollama](https://ollama.ai/) — local LLM support (planned)
- OpenAI GPT

---

## 🔹 Current State

- [x] PDF preprocessing script
- [ ] LangGraph pipeline (steps 1–8)
- [ ] File outputs by FR/step
- [ ] Example test cases for FR-1

---

## 🔹 Features that be cool to add

- [ ] Jira integration (auto-create tickets)
- [ ] HITL review nodes
- [ ] Retry generating starting from specific steps
