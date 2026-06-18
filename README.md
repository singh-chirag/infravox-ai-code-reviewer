# Infravox AI Code Reviewer

> Multi-agent code review system. 5 specialist LangGraph agents + 1 merge node.
> Catches security, performance, correctness, style, and test coverage issues with line-level precision.

[![Python 3.10](https://img.shields.io/badge/python-3.10-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green.svg)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.0.30-purple.svg)](https://langchain-ai.github.io/langgraph/)

---

## 🎯 What It Does

Accepts a raw GitHub PR diff and produces a **structured, line-level code review**:
- Specific findings with line numbers and exact code quotes
- Severity ratings (critical/high/medium/low)
- Categorized by: security, performance, correctness, style, test coverage
- Overall verdict: `approve` / `request_changes` / `needs_discussion`
- Deduplicated findings across all 5 agents
- Processing time metrics

---

## 🏗️ Architecture

### 6-Node LangGraph Pipeline
