"""
Evaluation suite for the claims triage agent.
Runs benchmark claims and measures accuracy, latency, and quality.
"""
import json
import time
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass, asdict

from app.core.config import settings
from app.core.logging import logger
from app.services.agent.triage_agent import run_triage
from app.models.schemas import ClaimStatus


@dataclass
class BenchmarkResult:
    """Result for a single benchmark case."""
    test_id: str
    claim_type: str
    claim_amount: float
    expected_status: str
    predicted_status: str
    correct: bool
    confidence: float
    latency_ms: int
    citations_count: int
    error: str = ""


@dataclass
class EvaluationReport:
    """Overall evaluation report."""
    total_tests: int
    correct_decisions: int
    accuracy: float
    avg_latency_ms: float
    avg_confidence: float
    total_citations: int
    results: List[BenchmarkResult]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_tests": self.total_tests,
            "correct_decisions": self.correct_decisions,
            "accuracy": round(self.accuracy, 2),
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "avg_confidence": round(self.avg_confidence, 2),
            "total_citations": self.total_citations,
            "results": [asdict(r) for r in self.results],
        }


# Expected outcomes for each benchmark test
BENCHMARK_CASES = [
    {
        "file": "test_01_low_amount.txt",
        "expected": ClaimStatus.AUTO_APPROVED,
        "reason": "Amount 2500 < 50000",
    },
    {
        "file": "test_02_medium_amount.txt",
        "expected": ClaimStatus.HUMAN_REVIEW,
        "reason": "Amount 85000 between 50K-2L",
    },
    {
        "file": "test_03_high_amount.txt",
        "expected": ClaimStatus.ESCALATED,
        "reason": "Amount 350000 > 2L",
    },
    {
        "file": "test_04_motor_low.txt",
        "expected": ClaimStatus.AUTO_APPROVED,
        "reason": "Amount 8000 < 25000 (motor threshold)",
    },
    {
        "file": "test_05_motor_high.txt",
        "expected": ClaimStatus.ESCALATED,
        "reason": "Amount 150000 > 1L (motor threshold)",
    },
]


async def run_benchmark() -> EvaluationReport:
    """
    Run all benchmark cases through the agent and generate a report.
    """
    benchmark_dir = settings.DATA_DIR / "claims" / "benchmark"
    results: List[BenchmarkResult] = []
    
    for case in BENCHMARK_CASES:
        file_path = benchmark_dir / case["file"]
        
        if not file_path.exists():
            logger.warning(f"Benchmark file not found: {file_path}")
            continue
        
        # Read file
        with open(file_path, "rb") as f:
            file_bytes = f.read()
        
        test_id = case["file"].replace(".txt", "")
        trace_id = f"bench-{test_id}"
        
        logger.info(f"Running benchmark: {test_id}")
        start = time.time()
        
        try:
            result = await run_triage(
                trace_id=trace_id,
                file_bytes=file_bytes,
                filename=case["file"],
                policy_number="BENCH-001",
                claim_type="health" if "health" in case["file"] else "motor",
                incident_date="2024-01-01",
            )
            
            latency = int((time.time() - start) * 1000)
            
            if result.get("error"):
                benchmark_result = BenchmarkResult(
                    test_id=test_id,
                    claim_type="unknown",
                    claim_amount=0,
                    expected_status=case["expected"].value,
                    predicted_status="error",
                    correct=False,
                    confidence=0,
                    latency_ms=latency,
                    citations_count=0,
                    error=result["error"],
                )
            else:
                decision = result["decision"]
                extracted = result["extracted_data"]
                
                benchmark_result = BenchmarkResult(
                    test_id=test_id,
                    claim_type=extracted.claim_type.value,
                    claim_amount=extracted.claim_amount,
                    expected_status=case["expected"].value,
                    predicted_status=decision.status.value,
                    correct=(decision.status == case["expected"]),
                    confidence=decision.confidence,
                    latency_ms=latency,
                    citations_count=len(decision.policy_citations),
                )
                
        except Exception as e:
            latency = int((time.time() - start) * 1000)
            benchmark_result = BenchmarkResult(
                test_id=test_id,
                claim_type="unknown",
                claim_amount=0,
                expected_status=case["expected"].value,
                predicted_status="error",
                correct=False,
                confidence=0,
                latency_ms=latency,
                citations_count=0,
                error=str(e),
            )
        
        results.append(benchmark_result)
        logger.info(
            f"Result: {test_id} | "
            f"Expected: {benchmark_result.expected_status} | "
            f"Got: {benchmark_result.predicted_status} | "
            f"Correct: {benchmark_result.correct}"
        )
    
    # Calculate aggregates
    total = len(results)
    correct = sum(1 for r in results if r.correct)
    accuracy = correct / total if total > 0 else 0
    avg_latency = sum(r.latency_ms for r in results) / total if total > 0 else 0
    avg_confidence = sum(r.confidence for r in results) / total if total > 0 else 0
    total_citations = sum(r.citations_count for r in results)
    
    report = EvaluationReport(
        total_tests=total,
        correct_decisions=correct,
        accuracy=accuracy,
        avg_latency_ms=avg_latency,
        avg_confidence=avg_confidence,
        total_citations=total_citations,
        results=results,
    )
    
    return report