#!/usr/bin/env python3
"""
Infravox Reviewer — Batch ingestion script
Reads each diff, POSTs to /review, saves JSON output
"""
import os
import json
import requests

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
DIFFS_DIR = "diffs"
REVIEWS_DIR = "reviews"

os.makedirs(REVIEWS_DIR, exist_ok=True)

# The 3 planted diffs with context
DIFFS = [
    ("diff1_python.txt", "python", "Add refund endpoint and fix transaction lookup"),
    ("diff2_javascript.txt", "javascript", "Add bulk fetch and fix password reset"),
    ("diff3_typescript.txt", "typescript", "Add order cancellation and status polling"),
]


def main():
    print(f"🚀 Infravox Reviewer — Batch Processing")
    print(f"📡 Backend: {BASE_URL}")
    print(f"📁 Diffs dir: {DIFFS_DIR}")
    print("-" * 60)
    
    for filename, language, context in DIFFS:
        filepath = os.path.join(DIFFS_DIR, filename)
        
        if not os.path.exists(filepath):
            print(f"⚠️  Skipping {filename} (not found)")
            continue
        
        with open(filepath, "r") as f:
            diff_text = f.read()
        
        print(f"\n📝 Reviewing {filename}...")
        print(f"   Language: {language}")
        print(f"   Context: {context}")
        
        try:
            response = requests.post(
                f"{BASE_URL}/review",
                json={
                    "diff": diff_text,
                    "language": language,
                    "context": context
                },
                timeout=180
            )
            response.raise_for_status()
            report = response.json()
            
            # Save output
            out_name = filename.replace(".txt", "_review.json")
            out_path = os.path.join(REVIEWS_DIR, out_name)
            with open(out_path, "w") as f:
                json.dump(report, f, indent=2)
            
            # Summary
            print(f"   ✅ Verdict: {report['verdict']}")
            print(f"   🎯 Severity: {report['overall_severity']}")
            print(f"   🔍 Findings: {len(report['findings'])}")
            print(f"   📊 By agent: {report['agent_findings_count']}")
            print(f"   ⏱️  Time: {report['processing_time_ms']}ms")
            print(f"   💾 Saved: {out_path}")
            
        except requests.exceptions.ConnectionError:
            print(f"   ❌ Cannot connect to backend at {BASE_URL}")
            print(f"      Start server: uvicorn main:app --reload")
            break
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print("\n" + "=" * 60)
    print(f"✅ Done. Reviews saved to /{REVIEWS_DIR}/")


if __name__ == "__main__":
    main()