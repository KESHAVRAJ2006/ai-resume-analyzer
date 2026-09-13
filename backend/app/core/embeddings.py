"""The sentence-transformers model and the precomputed role embeddings.

This lives in core/ rather than services/ because it is a resource manager, not
analysis logic - the same category of thing as a database connection pool. The
model is loaded ONCE at application startup and every role vector is computed
once at the same moment; a request only ever encodes the resume in front of it.

Why that matters: all-MiniLM-L6-v2 takes ~2s to load and ~90MB of RAM. Loading
it per request would add two seconds to every analysis and would exhaust a
free-tier dyno the moment two requests overlapped.

PRIVACY: resume text is redacted before it is embedded, so contact details
never reach the model. No personal attribute is encoded, stored or scored.
"""

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from app.services.job_matcher import JobRole, load_job_roles
from app.services.text_cleaner import clean_preserving_lines, redact_contact_info

if TYPE_CHECKING:  # pragma: no cover - import only for type checkers
    from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# all-MiniLM-L6-v2 truncates at 256 word pieces - roughly 180 words. A resume is
# 400-900 words, so embedding it whole would silently discard most of it. We cut
# it into overlapping windows instead and score every window.
CHUNK_WORDS = 80
CHUNK_OVERLAP = 20

# Per role we average the best 3 windows. Taking only the maximum is noisy (one
# lucky line decides the score); averaging everything dilutes the signal with
# education and formatting text. Three is the compromise.
TOP_CHUNKS = 3


@dataclass(frozen=True)
class EmbeddingIndex:
    """A loaded model plus the role vectors, ready to score resumes."""

    model_name: str
    role_ids: tuple[str, ...]
    role_vectors: np.ndarray          # (n_roles, dim), L2-normalised
    model: "SentenceTransformer"

    def score_resume(self, raw_text: str) -> dict[str, float]:
        """Take raw resume text, return {role_id: semantic similarity 0-1}.

        Similarity is cosine between resume windows and role descriptions,
        averaged over each role's best windows.
        """
        chunks = _chunk_resume(raw_text)
        if not chunks:
            return {role_id: 0.0 for role_id in self.role_ids}

        # normalize_embeddings makes every vector unit length, so a dot product
        # IS the cosine similarity - no division, no extra pass.
        chunk_vectors = self.model.encode(
            chunks, normalize_embeddings=True, show_progress_bar=False
        )
        similarities = np.asarray(chunk_vectors) @ self.role_vectors.T  # (chunks, roles)

        top = min(TOP_CHUNKS, similarities.shape[0])
        # Partition is O(n) versus a full sort; we only need the top few.
        best = np.sort(similarities, axis=0)[-top:]
        scores = best.mean(axis=0)

        # Cosine can be slightly negative for unrelated text; the formula expects 0-1.
        return {
            role_id: float(max(0.0, min(1.0, score)))
            for role_id, score in zip(self.role_ids, scores)
        }


def build_embedding_index(
    model_name: str, *, roles_path: str | None = None
) -> EmbeddingIndex:
    """Take a model name, load it and precompute every role vector.

    Called once from the FastAPI lifespan handler. Blocking and slow on first
    run because the model is downloaded from Hugging Face.
    """
    # Imported here, not at module top: sentence-transformers pulls in torch,
    # which costs ~2s of import time we do not want in unrelated test runs.
    from sentence_transformers import SentenceTransformer

    logger.info("Loading embedding model %s ...", model_name)
    model = SentenceTransformer(model_name)

    roles = load_job_roles(roles_path)
    role_ids = tuple(roles)
    documents = [_role_document(roles[role_id]) for role_id in role_ids]

    vectors = np.asarray(
        model.encode(documents, normalize_embeddings=True, show_progress_bar=False)
    )
    logger.info("Precomputed %d role embeddings, dim=%d", len(role_ids), vectors.shape[1])

    return EmbeddingIndex(
        model_name=model_name,
        role_ids=role_ids,
        role_vectors=vectors,
        model=model,
    )


def _role_document(role: JobRole) -> str:
    """Take a role, return the natural-language text used as its embedding.

    Unlike the TF-IDF document this is NOT run through clean_text: a sentence
    transformer was trained on ordinary prose and does better with the
    punctuation and capitalisation left in place.
    """
    skills = ", ".join(skill_id.replace("_", " ") for skill_id in role.weights)
    return f"{role.role_name}. {role.description} Key skills: {skills}."


def _chunk_resume(raw_text: str) -> list[str]:
    """Take raw resume text, return overlapping word windows, contacts removed.

    The overlap stops a skill that straddles a window boundary from being
    weakened in both windows.
    """
    # Light normalisation only - the transformer wants readable English, so we
    # keep case and punctuation and strip just the contact details.
    text = redact_contact_info(clean_preserving_lines(raw_text))
    words = text.split()
    if not words:
        return []

    step = max(1, CHUNK_WORDS - CHUNK_OVERLAP)
    chunks = [
        " ".join(words[start : start + CHUNK_WORDS])
        for start in range(0, len(words), step)
    ]
    # A trailing window shorter than the overlap is already fully contained in
    # the previous one, so it adds cost without adding information.
    if len(chunks) > 1 and len(chunks[-1].split()) <= CHUNK_OVERLAP:
        chunks.pop()
    return chunks
