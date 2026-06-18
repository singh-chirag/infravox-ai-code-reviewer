# Infravox AI Code Reviewer

An AI-powered multi-agent code review system that analyzes pull request diffs and generates structured review feedback across multiple dimensions including Security, Performance, Correctness, Style, and Test Coverage.

## Overview

This project was developed as part of the Infravox AI Internship Technical Assessment.

The system accepts code diffs from pull requests and uses a multi-agent workflow powered by LangGraph and Groq LLMs to identify potential issues, classify severity, and generate actionable recommendations.

Supported languages:

* Python
* JavaScript
* TypeScript

---

## Features

### Multi-Agent Review Pipeline

The reviewer consists of specialized agents:

| Agent               | Responsibility                                                          |
| ------------------- | ----------------------------------------------------------------------- |
| Security Agent      | Detects vulnerabilities, secrets, injection risks, authorization issues |
| Performance Agent   | Identifies inefficiencies, N+1 queries, resource usage concerns         |
| Correctness Agent   | Finds logical bugs, validation issues, edge cases                       |
| Style Agent         | Reviews maintainability and code quality                                |
| Test Coverage Agent | Detects missing test scenarios                                          |

---

### Structured Review Output

Each review contains:

* Review ID
* Pull Request Summary
* Severity Assessment
* Review Verdict
* Findings
* Recommendations
* Missing Tests
* Processing Metrics

Example Verdicts:

* approve
* request_changes

Severity Levels:

* low
* medium
* high
* critical

---

## Architecture

```text
Input Diff
    │
    ▼
LangGraph Workflow
    │
    ├── Security Agent
    ├── Performance Agent
    ├── Correctness Agent
    ├── Style Agent
    └── Test Coverage Agent
    │
    ▼
Merge Findings
    │
    ▼
Generate Verdict
    │
    ▼
Structured JSON Review
```

---

## Tech Stack

### Backend

* FastAPI
* Python 3.13

### AI Framework

* LangGraph
* LangChain

### LLM

* Groq API
* Llama 3.3 70B Versatile

### Utilities

* Pydantic
* Uvicorn

---

## Project Structure

```text
infravox-ai-code-reviewer/
│
├── agent.py
├── main.py
├── run_reviews.py
├── requirement.txt
│
├── diffs/
│   ├── diff1_python.txt
│   ├── diff2_javascript.txt
│   └── diff3_typescript.txt
│
├── reviews/
│   ├── diff1_python_review.json
│   ├── diff2_javascript_review.json
│   └── diff3_typescript_review.json
│
└── README.md
```

---

## Setup

### Clone Repository

```bash
git clone https://github.com/singh-chirag/infravox-ai-code-reviewer.git
cd infravox-ai-code-reviewer
```

### Create Virtual Environment

```bash
python -m venv venv
```

Windows:

```bash
venv\Scripts\activate
```

Linux/Mac:

```bash
source venv/bin/activate
```

### Install Dependencies

```bash
pip install -r requirement.txt
```

### Configure Environment Variables

Create a `.env` file:

```env
GROQ_API_KEY=your_api_key
MODEL_NAME=llama-3.3-70b-versatile
```

---

## Running the Application

Start the API server:

```bash
uvicorn main:app --reload
```

Server:

```text
http://localhost:8000
```

API Docs:

```text
http://localhost:8000/docs
```

---

## Running Reviews

Execute all provided sample diffs:

```bash
python run_reviews.py
```

Generated reports will be stored inside:

```text
reviews/
```

---

## Sample Findings

Example issues detected:

### Security

* SQL Injection
* Hardcoded Secrets
* Missing Authorization Checks
* Missing Input Validation

### Performance

* N+1 Query Patterns
* Infinite Polling Loops
* Resource Leaks

### Correctness

* Missing Null Checks
* Race Conditions
* Error Handling Issues

---

## Example Output

```json
{
  "verdict": "request_changes",
  "overall_severity": "critical",
  "findings": [
    {
      "title": "SQL Injection Vulnerability",
      "severity": "critical"
    }
  ]
}
```

---

## Design Decisions

### Why LangGraph?

LangGraph provides:

* Explicit workflow orchestration
* Agent state management
* Modular architecture
* Easy extensibility

### Why Multi-Agent Reviews?

Separating responsibilities allows each agent to focus on a specific review dimension, improving maintainability and making future enhancements easier.

---

## Future Improvements

* Parallel agent execution
* Confidence scoring
* Deduplication of findings
* Static analysis integration
* Support for additional languages
* Reviewer feedback loop
* Severity calibration using historical reviews

---

## Author

Chirag Kumar Singh

* BCA, Srinath University
* GitHub: https://github.com/singh-chirag

---

## Assignment Context

This project was developed for the Infravox AI Internship Technical Assessment to demonstrate agentic AI workflows, LLM-powered code analysis, structured review generation, and backend API development.
