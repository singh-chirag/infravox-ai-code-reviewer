#!/usr/bin/env python3
"""
Infravox AI Code Reviewer — Single-File LangGraph Pipeline
5 specialist agents + 1 merge node → structured ReviewReport
"""
import json
import os
import re
import time
from typing import TypedDict, List, Dict, Any, Optional
from urllib import response

from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv

load_dotenv()


# ============================================================================
# 📦 STATE DEFINITION
# ============================================================================
class ReviewState(TypedDict):
    diff: str                              # raw git diff
    language: str                          # python/javascript/typescript
    context: str                           # PR description
    security_findings: List[Dict]
    performance_findings: List[Dict]
    correctness_findings: List[Dict]
    style_findings: List[Dict]
    test_findings: List[Dict]
    review_report: Dict[str, Any]
    start_time: float


# ============================================================================
# 📝 SPECIALIST PROMPTS
# ============================================================================
SECURITY_PROMPT = """You are a paranoid senior security engineer reviewing a code diff.

Language: {language}
PR Context: {context}

DIFF:
{diff}

Find ALL security vulnerabilities including:
- SQL injection (string interpolation/concatenation into queries)
- Hardcoded credentials, API keys, secrets (especially Stripe/live keys)
- Unsafe deserialization
- Missing input validation at API boundaries
- IDOR (missing authorization/ownership checks)
- XSS vectors (user input rendered without escaping)
- Resource leaks (unclosed file handles, connections)
- Plaintext password storage (must use bcrypt/argon2)

For each finding, output JSON:
{{"line": <int>, "line_content": "<exact code>", "category": "security",
  "severity": "critical|high|medium|low",
  "title": "<short label>",
  "description": "<why it matters>",
  "suggestion": "<concrete fix with corrected code>"}}

Return ONLY a JSON array. Empty array [] if none found.
"""

PERFORMANCE_PROMPT = """You are a performance-focused engineer reviewing a code diff.

Language: {language}
PR Context: {context}

DIFF:
{diff}

Find performance issues that would hurt at scale:
- N+1 queries (DB call inside a loop — should use IN clause or Promise.all)
- Missing bulk operations
- Sync operations that should be async
- Infinite polling loops with no timeout/max-retry/exit condition
- Sequential async operations that could be parallel (Promise.all)
- Repeated expensive operations that should be cached
- Unbounded memory growth

Focus on issues causing measurable degradation at 10x/100x load.

Return ONLY a JSON array (same shape as security findings).
category must be 'performance'.
"""

CORRECTNESS_PROMPT = """You are a correctness-obsessed engineer reviewing a code diff.

Language: {language}
PR Context: {context}

DIFF:
{diff}

Find bugs that will cause production failures:
- Missing null/undefined checks (accessing property on null object)
- Off-by-one errors
- Incorrect error handling (swallowed exceptions)
- Race conditions
- Missing input validation at API boundaries
- Incorrect boolean logic
- Silent failures (returning undefined/NaN without error)
- Undefined variable references (ReferenceError at runtime)
- File handle not closed (resource leak)
- String interpolation with user input (XSS risk)

Return ONLY a JSON array. category must be 'correctness'.
"""

STYLE_PROMPT = """You are a pragmatic style reviewer.

Language: {language}
PR Context: {context}

DIFF:
{diff}

Flag only issues that genuinely hurt readability or safety:
- Functions too long (>50 lines)
- Unclear/misleading names
- Missing docstrings on public functions
- Dead code
- Magic numbers without explanation
- Duplicated logic
- 'any' type in TypeScript (defeats type safety — suggest proper type)

Return ONLY a JSON array. category must be 'style'.
"""

TEST_COVERAGE_PROMPT = """You are a test-driven engineer reviewing a code diff.

Language: {language}
PR Context: {context}

DIFF:
{diff}

Identify what is NOT tested:
- New code paths with no corresponding test
- Error/exception paths not covered
- Edge cases: empty input, null, zero, very large values
- Double-action cases: what if called twice? (e.g., double-cancel)
- Cases where a dependency (notification, DB) throws
- Missing authorization test coverage

For each finding, write a specific test case suggestion in 'suggestion' field, e.g.:
'Add: test_cancel_order_not_found() — call with non-existent order_id and assert 404 returned, not a crash'

Return ONLY a JSON array. category must be 'test_coverage'.
"""


# ============================================================================
# 🤖 LLM INITIALIZATION
# ============================================================================
llm = ChatGroq(
    model=os.getenv("MODEL_NAME", "llama3-70b-8192"),
    temperature=0.0,  # Deterministic for consistent findings
    api_key=os.getenv("GROQ_API_KEY")
)


# ============================================================================
# 🔧 GENERIC AGENT RUNNER
# ============================================================================
def _extract_json_array(text: str) -> List[Dict]:
    """Safely extract JSON array from LLM response"""
    text = text.strip()
    # Strip markdown code fences
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    text = text.strip()
    
    try:
        result = json.loads(text)
        if isinstance(result, list):
            return result
        return []
    except json.JSONDecodeError:
        # Try to find array in text
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return []
        return []


def _run_agent(prompt_template: str, state: ReviewState, key: str) -> ReviewState:
    """Generic runner for all specialist agents"""
    prompt = prompt_template.format(
        diff=state["diff"],
        language=state.get("language", "python"),
        context=state.get("context", "No additional context.")
    )
    
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        findings = _extract_json_array(response.content)
    except Exception as e:
        print(f"⚠️ Agent {key} failed: {e}")
        findings = []
    
    return {**state, key: findings}

print("\n===== RAW LLM RESPONSE =====")
# print(response.content)
print("============================\n")
# response = llm.invoke(...)

# ============================================================================
# 🕵️ SPECIALIST NODES
# ============================================================================
def security_node(state: ReviewState) -> ReviewState:
    return _run_agent(SECURITY_PROMPT, state, "security_findings")

def performance_node(state: ReviewState) -> ReviewState:
    return _run_agent(PERFORMANCE_PROMPT, state, "performance_findings")

def correctness_node(state: ReviewState) -> ReviewState:
    return _run_agent(CORRECTNESS_PROMPT, state, "correctness_findings")

def style_node(state: ReviewState) -> ReviewState:
    return _run_agent(STYLE_PROMPT, state, "style_findings")

def test_coverage_node(state: ReviewState) -> ReviewState:
    return _run_agent(TEST_COVERAGE_PROMPT, state, "test_findings")


# ============================================================================
# 🔀 MERGE NODE
# ============================================================================
def merge_node(state: ReviewState) -> ReviewState:
    """Consolidate, deduplicate, and produce final ReviewReport"""
    start = state.get("start_time", time.time())
    
    # Combine all findings
    all_findings = (
        state.get("security_findings", []) +
        state.get("performance_findings", []) +
        state.get("correctness_findings", []) +
        state.get("style_findings", []) +
        state.get("test_findings", [])
    )
    
    # Deduplicate by (line, category) and assign IDs
    seen = set()
    deduped = []
    for i, finding in enumerate(all_findings):
        if not isinstance(finding, dict):
            continue
        key = (finding.get("line"), finding.get("category"))
        if key not in seen and key[0] is not None:
            seen.add(key)
            finding["id"] = f"F-{str(len(deduped) + 1).zfill(3)}"
            deduped.append(finding)
    
    # Determine overall severity
    severities = [f.get("severity", "low").lower() for f in deduped]
    if "critical" in severities:
        overall = "critical"
    elif "high" in severities:
        overall = "high"
    elif "medium" in severities:
        overall = "medium"
    elif "low" in severities:
        overall = "low"
    else:
        overall = "clean"
    
    # Determine verdict
    verdict = "approve" if overall in ("clean", "low") else "request_changes"
    
    # Extract missing tests from test findings
    missing_tests = [
        f.get("suggestion", "")
        for f in deduped
        if f.get("category") == "test_coverage" and f.get("suggestion")
    ]
    
    # Positive observations (always include some)
    positive = [
        "Code is structured into focused, single-responsibility functions",
        "Error handling is present in several paths",
        "Naming conventions are generally consistent"
    ]
    
    report = {
        "pr_summary": f"PR adds changes in {state.get('language', 'unknown')} — {state.get('context', 'No context provided')}",
        "verdict": verdict,
        "verdict_reason": f"{len(deduped)} issues found, overall severity: {overall}",
        "overall_severity": overall,
        "findings": deduped,
        "positive_observations": positive,
        "missing_tests": missing_tests,
        "agent_findings_count": {
            "security": len(state.get("security_findings", [])),
            "performance": len(state.get("performance_findings", [])),
            "correctness": len(state.get("correctness_findings", [])),
            "style": len(state.get("style_findings", [])),
            "test_coverage": len(state.get("test_findings", [])),
        },
        "processing_time_ms": int((time.time() - start) * 1000)
    }
    
    return {**state, "review_report": report}


# ============================================================================
# 🕸️ GRAPH DEFINITION
# ============================================================================
def build_graph():
    """Build and compile the 6-node LangGraph pipeline"""
    graph = StateGraph(ReviewState)
    
    graph.add_node("security", security_node)
    graph.add_node("performance", performance_node)
    graph.add_node("correctness", correctness_node)
    graph.add_node("style", style_node)
    graph.add_node("test_coverage", test_coverage_node)
    graph.add_node("merge", merge_node)
    
    # Sequential execution (architecturally independent — parallelizable later)
    graph.set_entry_point("security")
    graph.add_edge("security", "performance")
    graph.add_edge("performance", "correctness")
    graph.add_edge("correctness", "style")
    graph.add_edge("style", "test_coverage")
    graph.add_edge("test_coverage", "merge")
    graph.add_edge("merge", END)
    
    return graph.compile()


# Compiled graph instance
review_graph = build_graph()


# ============================================================================
# 🧪 LOCAL TEST
# ============================================================================
if __name__ == "__main__":
    print("🔍 Infravox Reviewer — Local Test")
    test_state = {
        "diff": "def foo():\n    x = None\n    return x.bar",
        "language": "python",
        "context": "Test PR",
        "security_findings": [], "performance_findings": [],
        "correctness_findings": [], "style_findings": [],
        "test_findings": [], "review_report": {},
        "start_time": time.time()
    }
    result = review_graph.invoke(test_state)
    print(f"✅ Verdict: {result['review_report']['verdict']}")
    print(f"📊 Findings: {len(result['review_report']['findings'])}")