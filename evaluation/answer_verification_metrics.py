"""Deterministic V1-C07 measurement without parsing human-readable reports."""

from dataclasses import asdict, dataclass

from agents.workflow import AgentWorkflow
from config.settings import Settings

from .answer_verification_fixtures import (
    FixtureChatProvider,
    FixtureRetriever,
    GoldenAnswerVerificationCase,
)


REQUIRED_CATEGORIES = frozenset(
    {
        "answerable",
        "partial",
        "out_of_scope",
        "numerical_error",
        "unsupported_claim",
        "contradiction",
        "multi_chunk",
        "multi_document",
        "correction_success",
        "retry_exhaustion",
    }
)


@dataclass(frozen=True)
class AnswerVerificationCaseResult:
    case_id: str
    category: str
    retrieved_chunk_ids: tuple[str, ...]
    retrieval_precondition_passed: bool | None
    answer_passed: bool
    citation_grounding_passed: bool | None
    verification_decision_passed: bool | None
    routing_passed: bool
    verification_passed: bool
    terminal_outcome: str
    verification_retries: int
    passed: bool
    failures: tuple[str, ...]


@dataclass(frozen=True)
class AnswerVerificationMetrics:
    total_cases: int
    passed_cases: int
    retrieval_scored_cases: int
    retrieval_precondition_passed_cases: int
    answer_passed_cases: int
    citation_scored_cases: int
    citation_grounding_passed_cases: int
    verification_scored_cases: int
    verification_decision_passed_cases: int
    routing_passed_cases: int
    verification_passed_cases: int
    cases: tuple[AnswerVerificationCaseResult, ...]

    def to_dict(self) -> dict:
        return asdict(self)


def validate_golden_answer_verification_cases(cases: list[GoldenAnswerVerificationCase]) -> None:
    """Reject incomplete, duplicate, or ambiguous golden workflow fixtures."""
    case_ids = [case.case_id for case in cases]
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("Golden answer/verification case IDs must be unique.")
    categories = {case.category for case in cases}
    if categories != REQUIRED_CATEGORIES:
        raise ValueError("Golden cases must cover every V1-C07 required category exactly once.")
    for case in cases:
        document_ids = [document.metadata.get("chunk_id") for document in case.documents]
        if any(not isinstance(chunk_id, str) or not chunk_id for chunk_id in document_ids):
            raise ValueError(f"Golden case {case.case_id} has a document without a stable chunk_id.")
        known_chunk_ids = set(document_ids)
        if case.out_of_scope != (not case.expected_chunk_ids):
            raise ValueError("Out-of-scope cases must have no expected retrieved chunk IDs.")
        if not case.expected_chunk_ids <= known_chunk_ids:
            raise ValueError(f"Golden case {case.case_id} references unknown retrieval evidence.")
        if not case.expected_citation_chunk_ids <= known_chunk_ids:
            raise ValueError(f"Golden case {case.case_id} references unknown citation evidence.")


def evaluate_case(case: GoldenAnswerVerificationCase) -> AnswerVerificationCaseResult:
    """Run one fixed model/retrieval scenario through the real bounded workflow."""
    provider = FixtureChatProvider(case.responses)
    retriever = FixtureRetriever(case.documents)
    workflow = AgentWorkflow(
        provider,
        Settings(_env_file=None, MAX_VERIFICATION_RETRIES=2),
    )
    result = workflow.full_pipeline(case.question, retriever)

    retrieved_chunk_ids = tuple(
        document.metadata["chunk_id"] for document in retriever.documents
    )
    failures: list[str] = []
    retrieval_precondition_passed: bool | None = None
    if not case.out_of_scope:
        retrieval_precondition_passed = case.expected_chunk_ids <= set(retrieved_chunk_ids)
        if not retrieval_precondition_passed:
            failures.append("expected retrieval evidence was absent")

    answer_passed = result["draft_answer"] == case.expected_answer
    if not answer_passed:
        failures.append("final answer did not match the golden expected answer")

    citation_grounding_passed: bool | None = None
    if case.expected_citation_chunk_ids:
        available_citation_ids = {
            citation["chunk_id"]
            for citation in result["citations"]
            if citation["available"] and citation["chunk_id"] is not None
        }
        citation_grounding_passed = case.expected_citation_chunk_ids <= available_citation_ids
        if not citation_grounding_passed:
            failures.append("expected citations were not resolved from retrieved chunks")

    verification_decision_passed: bool | None = None
    verification_result = result["verification_result"]
    if case.expected_supported is not None:
        verification_decision_passed = (
            verification_result is not None
            and verification_result["supported"] is case.expected_supported
        )
        if not verification_decision_passed:
            failures.append("final typed verification support decision differed")
    elif verification_result is not None:
        failures.append("out-of-scope case unexpectedly reached verification")

    routing_passed = (
        result["terminal_outcome"] == case.expected_terminal_outcome
        and result["verification_retries"] == case.expected_retries
    )
    if not routing_passed:
        failures.append("typed verification terminal state or retry count differed")

    verification_passed = verification_decision_passed is not False and routing_passed

    passed = not failures
    return AnswerVerificationCaseResult(
        case_id=case.case_id,
        category=case.category,
        retrieved_chunk_ids=retrieved_chunk_ids,
        retrieval_precondition_passed=retrieval_precondition_passed,
        answer_passed=answer_passed,
        citation_grounding_passed=citation_grounding_passed,
        verification_decision_passed=verification_decision_passed,
        routing_passed=routing_passed,
        verification_passed=verification_passed,
        terminal_outcome=result["terminal_outcome"],
        verification_retries=result["verification_retries"],
        passed=passed,
        failures=tuple(failures),
    )


def evaluate_cases(cases: list[GoldenAnswerVerificationCase]) -> AnswerVerificationMetrics:
    """Evaluate all V1-C07 golden cases and summarize distinct quality boundaries."""
    validate_golden_answer_verification_cases(cases)
    results = tuple(evaluate_case(case) for case in cases)
    return AnswerVerificationMetrics(
        total_cases=len(results),
        passed_cases=sum(result.passed for result in results),
        retrieval_scored_cases=sum(result.retrieval_precondition_passed is not None for result in results),
        retrieval_precondition_passed_cases=sum(
            result.retrieval_precondition_passed is True for result in results
        ),
        answer_passed_cases=sum(result.answer_passed for result in results),
        citation_scored_cases=sum(result.citation_grounding_passed is not None for result in results),
        citation_grounding_passed_cases=sum(
            result.citation_grounding_passed is True for result in results
        ),
        verification_scored_cases=sum(
            result.verification_decision_passed is not None for result in results
        ),
        verification_decision_passed_cases=sum(
            result.verification_decision_passed is True for result in results
        ),
        routing_passed_cases=sum(result.routing_passed for result in results),
        verification_passed_cases=sum(result.verification_passed for result in results),
        cases=results,
    )
