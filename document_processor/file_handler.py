import os
import hashlib
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from typing import List
from docling.document_converter import DocumentConverter
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from config import constants
from config.settings import settings
from utils.logging import logger


class DocumentProcessingError(ValueError):
    """Safe document-ingestion failure suitable for UI presentation."""

class DocumentProcessor:
    def __init__(self, config=settings):
        self.headers = [("#", "Header 1"), ("##", "Header 2")]
        self.config = config
        self.cache_dir = Path(self.config.CACHE_DIR)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._subchunk_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.config.DOCUMENT_CHUNK_MAX_CHARACTERS,
            chunk_overlap=0,
            length_function=len,
        )
        
    def validate_files(self, files: List) -> None:
        """Validate the total size of the uploaded files."""
        if not files:
            raise DocumentProcessingError("No documents were provided.")
        total_size = 0
        for file in files:
            try:
                total_size += os.path.getsize(file.name)
            except OSError:
                # A later per-file processing step records the controlled
                # failure while permitting another uploaded file to succeed.
                logger.error("An uploaded file was unavailable for validation.")
        if total_size > constants.MAX_TOTAL_SIZE:
            raise ValueError(f"Total size exceeds {constants.MAX_TOTAL_SIZE//1024//1024}MB limit")

    def process(self, files: List) -> List:
        """Process files with caching for subsequent queries"""
        self.validate_files(files)
        all_chunks = []
        seen_hashes = set()
        
        for file in files:
            try:
                # Generate content-based hash for caching
                with open(file.name, "rb") as f:
                    file_hash = self._generate_hash(f.read())
                
                cache_path = self.cache_dir / f"{file_hash}.pkl"
                
                if self._is_cache_valid(cache_path):
                    try:
                        logger.info(f"Loading from cache: {file.name}")
                        chunks = self._load_from_cache(cache_path)
                        chunks, migrated = self._bound_chunk_size(chunks)
                        if migrated:
                            logger.info("Migrating cached document chunks to the bounded representation.")
                            self._save_to_cache(chunks, cache_path)
                    except (OSError, pickle.UnpicklingError, KeyError, TypeError):
                        logger.warning("Invalid document cache; rebuilding from source.")
                        cache_path.unlink(missing_ok=True)
                        chunks = self._process_file(file)
                        self._save_to_cache(chunks, cache_path)
                else:
                    logger.info(f"Processing and caching: {file.name}")
                    chunks = self._process_file(file)
                    self._save_to_cache(chunks, cache_path)

                self._attach_provenance(chunks, file_hash, Path(file.name).name)
                
                # Deduplicate chunks across files
                for chunk in chunks:
                    chunk_hash = self._generate_hash(chunk.page_content.encode())
                    if chunk_hash not in seen_hashes:
                        all_chunks.append(chunk)
                        seen_hashes.add(chunk_hash)
                        
            except (OSError, ValueError, pickle.UnpicklingError):
                logger.error("Failed to process an uploaded document.")
                continue
                
        logger.info(f"Total unique chunks: {len(all_chunks)}")
        if not all_chunks:
            raise DocumentProcessingError("No usable document content could be extracted.")
        return all_chunks

    def _process_file(self, file) -> List:
        """Original processing logic with Docling"""
        if not file.name.endswith(('.pdf', '.docx', '.txt', '.md')):
            logger.warning(f"Skipping unsupported file type: {file.name}")
            return []

        try:
            converter = DocumentConverter()
            markdown = converter.convert(file.name).document.export_to_markdown()
        except Exception as exc:
            # Docling is an external parser boundary.  Do not expose its raw
            # errors to the workflow or UI; the caller decides whether another
            # uploaded file can still be used.
            raise DocumentProcessingError(
                "Document content could not be extracted."
            ) from exc
        splitter = MarkdownHeaderTextSplitter(self.headers)
        chunks, _ = self._bound_chunk_size(splitter.split_text(markdown))
        return chunks

    def _bound_chunk_size(self, chunks: List) -> tuple[List, bool]:
        """Split only oversized header chunks before they reach embeddings.

        Header metadata stays with every derived chunk. Provenance is attached
        afterwards, so each deterministic derived position receives its own
        stable C05 chunk identity on fresh and cached processing alike.
        """
        bounded_chunks = []
        migrated = False
        for chunk in chunks:
            if len(chunk.page_content) <= self.config.DOCUMENT_CHUNK_MAX_CHARACTERS:
                bounded_chunks.append(chunk)
                continue
            derived_chunks = self._subchunk_splitter.split_documents([chunk])
            if not derived_chunks or any(
                len(derived.page_content) > self.config.DOCUMENT_CHUNK_MAX_CHARACTERS
                for derived in derived_chunks
            ):
                raise DocumentProcessingError("Document content could not be bounded safely.")
            bounded_chunks.extend(derived_chunks)
            migrated = True
        return bounded_chunks, migrated

    @staticmethod
    def _attach_provenance(chunks: List, document_id: str, source_name: str) -> None:
        """Attach stable local provenance after fresh or cached chunk loading."""
        for index, chunk in enumerate(chunks):
            metadata = dict(chunk.metadata or {})
            chunk_id_material = f"{document_id}:{index}:{chunk.page_content}".encode()
            metadata.update(
                {
                    "document_id": document_id,
                    "chunk_id": hashlib.sha256(chunk_id_material).hexdigest(),
                    "source_name": source_name,
                }
            )
            section = metadata.get("Header 2") or metadata.get("Header 1")
            if isinstance(section, str) and section:
                metadata["section"] = section
            chunk.metadata = metadata

    def _generate_hash(self, content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

    def _save_to_cache(self, chunks: List, cache_path: Path):
        with open(cache_path, "wb") as f:
            pickle.dump({
                "timestamp": datetime.now().timestamp(),
                "chunks": chunks
            }, f)

    def _load_from_cache(self, cache_path: Path) -> List:
        with open(cache_path, "rb") as f:
            data = pickle.load(f)
        return data["chunks"]

    def _is_cache_valid(self, cache_path: Path) -> bool:
        if not cache_path.exists():
            return False
            
        cache_age = datetime.now() - datetime.fromtimestamp(cache_path.stat().st_mtime)
        return cache_age < timedelta(days=settings.CACHE_EXPIRE_DAYS)
