"""Executable deterministic V1-C06 retrieval evaluation runner."""

import json
from tempfile import TemporaryDirectory

from config.settings import Settings
from retriever.builder import RetrieverBuilder

from .retrieval_fixtures import (
    DeterministicKeywordEmbedding,
    golden_cases,
    golden_documents,
)
from .retrieval_metrics import evaluate_modes, validate_golden_fixtures


EVALUATION_K = 3


def run_evaluation() -> dict:
    documents = golden_documents()
    cases = golden_cases()
    validate_golden_fixtures(cases, documents)
    with TemporaryDirectory() as directory:
        config = Settings(_env_file=None, CHROMA_DB_PATH=directory, VECTOR_SEARCH_K=EVALUATION_K)
        modes = RetrieverBuilder(DeterministicKeywordEmbedding(), config).build_evaluation_modes(
            documents, EVALUATION_K
        )
        results = evaluate_modes(modes, cases, EVALUATION_K)
    return {mode: result.to_dict() for mode, result in results.items()}


if __name__ == "__main__":
    print(json.dumps(run_evaluation(), indent=2, sort_keys=True))
