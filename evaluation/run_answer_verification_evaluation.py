"""Command-line entry point for repeatable V1-C07 workflow evaluation."""

import json

from .answer_verification_fixtures import golden_answer_verification_cases
from .answer_verification_metrics import evaluate_cases
from .run_retrieval_evaluation import run_evaluation as run_retrieval_evaluation


def run_evaluation() -> dict:
    """Measure C06 retrieval and C07 grounded-workflow behavior separately."""
    return {
        "retrieval": run_retrieval_evaluation(),
        "answer_verification": evaluate_cases(golden_answer_verification_cases()).to_dict(),
    }


def main() -> None:
    print(json.dumps(run_evaluation(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
