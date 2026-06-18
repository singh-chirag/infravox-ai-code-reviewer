#!/usr/bin/env python3
"""Infravox AI Code Reviewer — FastAPI Backend"""
import time
import uuid
from typing import Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agent import review_graph, ReviewState
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="Infravox AI Code Reviewer",
    description="Multi-agent code review powered by LangGraph",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage
reviews_store: Dict[str, dict] = {}


# ============================================================================
# 📦 REQUEST/RESPONSE MODELS
# ============================================================================
class ReviewRequest(BaseModel):
    diff: str = Field(..., description="Raw git diff text")
    language: str = Field(default="python", description="python/javascript/typescript")
    context: str = Field(default="", description="PR description / context")


from typing import Optional

class Finding(BaseModel):
    id: Optional[str] = None
    title: Optional[str] = None
    severity: Optional[str] = None
    line_content: Optional[str] = None
    suggestion: Optional[str] = None

    category: Optional[str] = None
    description: Optional[str] = None
    recommendation: Optional[str] = None
    line: Optional[int] = None


class ReviewReport(BaseModel):
    review_id: str
    pr_summary: str
    verdict: str
    verdict_reason: str
    overall_severity: str
    findings: List[Finding]
    positive_observations: List[str]
    missing_tests: List[str]
    agent_findings_count: Dict[str, int]
    processing_time_ms: int


# ============================================================================
# 🚀 ENDPOINTS
# ============================================================================
@app.post("/review", response_model=ReviewReport)
async def create_review(req: ReviewRequest):
    """Run the 6-node review pipeline on a diff"""
    review_id = str(uuid.uuid4())[:8]
    
    initial_state: ReviewState = {
        "diff": req.diff,
        "language": req.language.lower(),
        "context": req.context or "No additional context.",
        "start_time": time.time(),
        "security_findings": [],
        "performance_findings": [],
        "correctness_findings": [],
        "style_findings": [],
        "test_findings": [],
        "review_report": {}
    }
    
    try:
        result = review_graph.invoke(initial_state)
        report = result["review_report"]
        report["review_id"] = review_id
        reviews_store[review_id] = report
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Review failed: {str(e)}")


@app.get("/review/{review_id}")
async def get_review(review_id: str):
    """Retrieve a specific review by ID"""
    if review_id not in reviews_store:
        raise HTTPException(status_code=404, detail="Review not found")
    return reviews_store[review_id]


@app.get("/reviews")
async def list_reviews():
    """List all reviews (summary only)"""
    return [
        {
            "review_id": k,
            "pr_summary": v.get("pr_summary", ""),
            "verdict": v.get("verdict", ""),
            "overall_severity": v.get("overall_severity", "")
        }
        for k, v in reviews_store.items()
    ]


@app.get("/health")
async def health():
    """Health check"""
    return {"status": "ok", "service": "infravox-reviewer", "groq": "connected"}


@app.get("/")
async def root():
    return {
        "service": "Infravox AI Code Reviewer",
        "docs": "/docs",
        "endpoints": {
            "POST /review": "Submit a diff for review",
            "GET /review/{id}": "Get a specific review",
            "GET /reviews": "List all reviews",
            "GET /health": "Health check"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)