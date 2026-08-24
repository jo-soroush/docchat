"""Focused V1-C11 checks that developer documentation matches active V1 boundaries."""

from pathlib import Path
from unittest import TestCase

from product.operations import OPERATION_LABELS, ResearchOperation


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


class ProjectDocumentationTests(TestCase):
    def test_readme_documents_active_configuration_and_validation_commands(self) -> None:
        readme = (REPOSITORY_ROOT / "README.md").read_text(encoding="utf-8")
        for required_text in (
            "OLLAMA_BASE_URL",
            "OLLAMA_CHAT_MODEL",
            "OLLAMA_EMBEDDING_MODEL",
            "OLLAMA_EMBEDDING_BATCH_SIZE",
            "OLLAMA_CONTEXT_WINDOW",
            "DOCUMENT_CHUNK_MAX_CHARACTERS",
            "GRADIO_SERVER_PORT",
            "MAX_VERIFICATION_RETRIES",
            "venv/bin/python -m unittest discover -s test -v",
            "venv/bin/python -m evaluation.run_retrieval_evaluation",
            "venv/bin/python -m evaluation.run_answer_verification_evaluation",
        ):
            with self.subTest(required_text=required_text):
                self.assertIn(required_text, readme)

    def test_readme_lists_all_active_product_operations(self) -> None:
        readme = (REPOSITORY_ROOT / "README.md").read_text(encoding="utf-8")
        for operation in ResearchOperation:
            with self.subTest(operation=operation):
                self.assertIn(OPERATION_LABELS[operation], readme)

    def test_architecture_and_provenance_docs_state_active_boundaries(self) -> None:
        architecture = (REPOSITORY_ROOT / "docs" / "ARCHITECTURE.md").read_text(
            encoding="utf-8"
        )
        provenance = (REPOSITORY_ROOT / "docs" / "PROVENANCE_AND_DECISIONS.md").read_text(
            encoding="utf-8"
        )
        for required_text in ("ChatProvider", "EmbeddingProvider", "TerminalOutcome", "RunTrace"):
            with self.subTest(required_text=required_text):
                self.assertIn(required_text, architecture)
        self.assertIn("origin/2-final", provenance)
        self.assertIn("eb9be30", provenance)
        self.assertIn("No `LICENSE*`", provenance)

    def test_demo_document_does_not_claim_clean_room_real_model_execution(self) -> None:
        demos = (REPOSITORY_ROOT / "docs" / "VERIFIED_DEMOS.md").read_text(encoding="utf-8")
        normalized_demos = " ".join(demos.split())
        self.assertIn("not an assertion", normalized_demos)
        self.assertIn("does not create a fresh operating-system image", normalized_demos)
