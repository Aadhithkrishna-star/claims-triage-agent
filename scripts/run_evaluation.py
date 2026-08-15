"""
Standalone script to run the evaluation suite.
Usage: python scripts/run_evaluation.py
"""
import asyncio
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.evaluation.benchmark import run_benchmark


async def main():
    print("=" * 60)
    print("CLAIMS TRIAGE AGENT - EVALUATION SUITE")
    print("=" * 60)
    
    report = await run_benchmark()
    
    print(f"\nTotal Tests: {report.total_tests}")
    print(f"Correct Decisions: {report.correct_decisions}/{report.total_tests}")
    print(f"Accuracy: {report.accuracy * 100:.1f}%")
    print(f"Avg Latency: {report.avg_latency_ms:.0f} ms")
    print(f"Avg Confidence: {report.avg_confidence:.2f}")
    print(f"Total Citations Retrieved: {report.total_citations}")
    
    print("\n" + "-" * 60)
    print("DETAILED RESULTS:")
    print("-" * 60)
    
    for r in report.results:
        status = "✅ PASS" if r.correct else "❌ FAIL"
        print(f"\n{r.test_id}: {status}")
        print(f"  Amount: Rs. {r.claim_amount}")
        print(f"  Expected: {r.expected_status}")
        print(f"  Predicted: {r.predicted_status}")
        print(f"  Confidence: {r.confidence}")
        print(f"  Latency: {r.latency_ms} ms")
        print(f"  Citations: {r.citations_count}")
        if r.error:
            print(f"  Error: {r.error}")
    
    # Save report to file
    report_path = Path("data/evaluation_report.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w") as f:
        json.dump(report.to_dict(), f, indent=2)
    
    print(f"\n{'=' * 60}")
    print(f"Report saved to: {report_path}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())