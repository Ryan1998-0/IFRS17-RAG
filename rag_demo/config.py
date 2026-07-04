import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional


@dataclass(frozen=True)
class RagConfig:
    top_k: int = 5
    chunk_size: int = 1200
    chunk_stride: int = 600
    retrieval_candidate_k: int = 50
    keyword_weight: float = 0.3
    embedding_weight: float = 0.7
    metadata_boost_max: float = 0.18
    verifier_auto_accept_enabled: bool = False
    verifier_auto_accept_score: float = 0.52
    verifier_auto_reject_score: float = 0.15
    verifier_min_keyword_score: float = 8.0
    verifier_min_embedding_score: float = 0.35
    verifier_context_chars: int = 600

    @classmethod
    def from_env(cls, env: Optional[Mapping[str, str]] = None) -> "RagConfig":
        values = env or os.environ
        return cls(
            top_k=_int_value(values, "RAG_TOP_K", cls.top_k),
            chunk_size=_int_value(values, "RAG_CHUNK_SIZE", cls.chunk_size),
            chunk_stride=_int_value(values, "RAG_CHUNK_STRIDE", cls.chunk_stride),
            retrieval_candidate_k=_int_value(
                values,
                "RAG_RETRIEVAL_CANDIDATE_K",
                cls.retrieval_candidate_k,
            ),
            keyword_weight=_float_value(values, "RAG_KEYWORD_WEIGHT", cls.keyword_weight),
            embedding_weight=_float_value(values, "RAG_EMBEDDING_WEIGHT", cls.embedding_weight),
            metadata_boost_max=_float_value(values, "RAG_METADATA_BOOST_MAX", cls.metadata_boost_max),
            verifier_auto_accept_enabled=_bool_value(
                values,
                "RAG_VERIFIER_AUTO_ACCEPT_ENABLED",
                cls.verifier_auto_accept_enabled,
            ),
            verifier_auto_accept_score=_float_value(
                values,
                "RAG_VERIFIER_AUTO_ACCEPT_SCORE",
                cls.verifier_auto_accept_score,
            ),
            verifier_auto_reject_score=_float_value(
                values,
                "RAG_VERIFIER_AUTO_REJECT_SCORE",
                cls.verifier_auto_reject_score,
            ),
            verifier_min_keyword_score=_float_value(
                values,
                "RAG_VERIFIER_MIN_KEYWORD_SCORE",
                cls.verifier_min_keyword_score,
            ),
            verifier_min_embedding_score=_float_value(
                values,
                "RAG_VERIFIER_MIN_EMBEDDING_SCORE",
                cls.verifier_min_embedding_score,
            ),
            verifier_context_chars=_int_value(
                values,
                "RAG_VERIFIER_CONTEXT_CHARS",
                cls.verifier_context_chars,
            ),
        ).normalized()

    def normalized(self) -> "RagConfig":
        chunk_size = max(100, int(self.chunk_size))
        chunk_stride = min(max(1, int(self.chunk_stride)), chunk_size)
        keyword_weight = max(0.0, float(self.keyword_weight))
        embedding_weight = max(0.0, float(self.embedding_weight))
        total = keyword_weight + embedding_weight
        if total <= 0:
            keyword_weight, embedding_weight = 0.3, 0.7
        else:
            keyword_weight = keyword_weight / total
            embedding_weight = embedding_weight / total
        return RagConfig(
            top_k=max(1, int(self.top_k)),
            chunk_size=chunk_size,
            chunk_stride=chunk_stride,
            retrieval_candidate_k=max(1, int(self.retrieval_candidate_k)),
            keyword_weight=keyword_weight,
            embedding_weight=embedding_weight,
            metadata_boost_max=max(0.0, float(self.metadata_boost_max)),
            verifier_auto_accept_enabled=bool(self.verifier_auto_accept_enabled),
            verifier_auto_accept_score=max(0.0, float(self.verifier_auto_accept_score)),
            verifier_auto_reject_score=max(0.0, float(self.verifier_auto_reject_score)),
            verifier_min_keyword_score=max(0.0, float(self.verifier_min_keyword_score)),
            verifier_min_embedding_score=max(0.0, float(self.verifier_min_embedding_score)),
            verifier_context_chars=max(100, int(self.verifier_context_chars)),
        )


def _int_value(values: Mapping[str, str], key: str, default: int) -> int:
    try:
        return int(values.get(key, str(default)))
    except (TypeError, ValueError):
        return default


def _float_value(values: Mapping[str, str], key: str, default: float) -> float:
    try:
        return float(values.get(key, str(default)))
    except (TypeError, ValueError):
        return default


def _bool_value(values: Mapping[str, str], key: str, default: bool) -> bool:
    value = values.get(key)
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def resolve_project_path(
    env_key: str,
    default_relative_path: str,
    env: Optional[Mapping[str, str]] = None,
    project_root: Optional[Path] = None,
) -> Path:
    values = env or os.environ
    configured = values.get(env_key)
    if configured:
        return Path(configured).expanduser()

    root = project_root or Path(__file__).resolve().parents[1]
    return root / default_relative_path


def resolve_profile_path(
    env_key: str,
    default_relative_path: str,
    profile_relative_path: str,
    env: Optional[Mapping[str, str]] = None,
    project_root: Optional[Path] = None,
) -> Path:
    values = env or os.environ
    configured = values.get(env_key)
    if configured:
        return Path(configured).expanduser()

    root = project_root or Path(__file__).resolve().parents[1]
    profile = values.get("RAG_PROFILE")
    if profile:
        return root / "profiles" / profile / profile_relative_path

    return root / default_relative_path
