"""
Deterministic Entity Resolution Engine
Resolves messy, variant startup and product company names into canonical entities.
Maps entities against a verified seed list of known AI enterprises and maintains
a comprehensive mapping audit log.
"""

from __future__ import annotations

import difflib
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


# Seed database of 50+ canonical AI startups and enterprises
CANONICAL_AI_ENTITIES = [
    {"id": "ai-001", "name": "OpenAI", "aliases": ["Open AI", "OpenAI, Inc.", "OpenAI Inc", "OpenAI LLC", "OpenAI Global"]},
    {"id": "ai-002", "name": "Anthropic", "aliases": ["Anthropic, PBC", "Anthropic PBC", "Anthropic AI", "Anthropic Inc"]},
    {"id": "ai-003", "name": "Mistral AI", "aliases": ["Mistral", "Mistral AI SAS", "Mistral.ai", "MistralAI"]},
    {"id": "ai-004", "name": "Cohere", "aliases": ["Cohere Inc.", "Cohere AI", "Cohere Inc"]},
    {"id": "ai-005", "name": "Perplexity AI", "aliases": ["Perplexity", "Perplexity.ai", "Perplexity Inc", "Perplexity AI, Inc."]},
    {"id": "ai-006", "name": "Scale AI", "aliases": ["Scale", "Scale.com", "Scale AI, Inc.", "Scale Labs"]},
    {"id": "ai-007", "name": "Hugging Face", "aliases": ["HuggingFace", "Hugging Face Inc.", "HuggingFace Inc", "HF"]},
    {"id": "ai-008", "name": "Runway", "aliases": ["RunwayML", "Runway ML", "Runway AI, Inc.", "Runway AI"]},
    {"id": "ai-009", "name": "Midjourney", "aliases": ["Midjourney Inc.", "Midjourney, Inc.", "Midjourney AI"]},
    {"id": "ai-010", "name": "Stability AI", "aliases": ["Stability", "Stability.ai", "Stability AI Ltd", "Stability AI Ltd."]},
    {"id": "ai-011", "name": "xAI", "aliases": ["x.ai", "xAI Corp", "xAI Corp."]},
    {"id": "ai-012", "name": "Databricks", "aliases": ["Databricks, Inc.", "Databricks Inc"]},
    {"id": "ai-013", "name": "Character.ai", "aliases": ["Character AI", "Character Technologies Inc.", "Character AI Inc."]},
    {"id": "ai-014", "name": "Jasper", "aliases": ["Jasper AI", "Jasper.ai", "Jasper AI, Inc."]},
    {"id": "ai-015", "name": "ElevenLabs", "aliases": ["Eleven Labs", "ElevenLabs Inc.", "ElevenLabs, Inc."]},
    {"id": "ai-016", "name": "Adept", "aliases": ["Adept AI", "Adept AI Labs", "Adept AI Labs Inc."]},
    {"id": "ai-017", "name": "Cursor", "aliases": ["Anysphere", "Anysphere, Inc.", "Cursor AI", "Cursor Editor"]},
    {"id": "ai-018", "name": "Glean", "aliases": ["Glean Technologies", "Glean, Inc.", "Glean AI"]},
    {"id": "ai-019", "name": "Poolside", "aliases": ["Poolside AI", "Poolside SAS", "Poolside, Inc."]},
    {"id": "ai-020", "name": "Harvey", "aliases": ["Harvey AI", "Harvey, Inc.", "Counsel AI Corp"]},
    {"id": "ai-021", "name": "Synthesia", "aliases": ["Synthesia Ltd", "Synthesia Ltd.", "Synthesia AI"]},
    {"id": "ai-022", "name": "Together AI", "aliases": ["Together", "Together.xyz", "Together Computer Inc."]},
    {"id": "ai-023", "name": "Groq", "aliases": ["Groq Inc.", "Groq, Inc.", "Groq AI"]},
    {"id": "ai-024", "name": "Fireworks AI", "aliases": ["Fireworks", "Fireworks.ai", "Fireworks AI, Inc."]},
    {"id": "ai-025", "name": "Pinecone", "aliases": ["Pinecone Systems", "Pinecone Systems, Inc.", "Pinecone Inc."]},
    {"id": "ai-026", "name": "Weaviate", "aliases": ["Weaviate B.V.", "Weaviate Inc.", "SeMI Technologies"]},
    {"id": "ai-027", "name": "Qdrant", "aliases": ["Qdrant Solutions", "Qdrant Solutions GmbH"]},
    {"id": "ai-028", "name": "Chroma", "aliases": ["Chroma DB", "ChromaDB", "Chroma Inc."]},
    {"id": "ai-029", "name": "LangChain", "aliases": ["LangChain, Inc.", "LangChain Inc", "LangChain AI"]},
    {"id": "ai-030", "name": "LlamaIndex", "aliases": ["Llama Index", "LlamaIndex Inc.", "Run Llama"]},
    {"id": "ai-031", "name": "Baseten", "aliases": ["Baseten, Inc.", "Baseten Labs"]},
    {"id": "ai-032", "name": "Modal", "aliases": ["Modal Labs", "Modal Labs Inc.", "Modal Inc."]},
    {"id": "ai-033", "name": "Replicate", "aliases": ["Replicate, Inc.", "Replicate Inc"]},
    {"id": "ai-034", "name": "OctoAI", "aliases": ["OctoML", "OctoML, Inc.", "OctoAI Inc."]},
    {"id": "ai-035", "name": "Weights & Biases", "aliases": ["WandB", "W&B", "Weights and Biases", "Weights & Biases, Inc."]},
    {"id": "ai-036", "name": "DeepL", "aliases": ["DeepL SE", "DeepL GmbH", "DeepL Pro"]},
    {"id": "ai-037", "name": "Writer", "aliases": ["Writer Inc.", "Writer.com", "Writer AI"]},
    {"id": "ai-038", "name": "Covariant", "aliases": ["Covariant.ai", "Covariant AI", "Covariant, Inc."]},
    {"id": "ai-039", "name": "Figure", "aliases": ["Figure AI", "Figure AI, Inc."]},
    {"id": "ai-040", "name": "Physical Intelligence", "aliases": ["pi", "Physical Intelligence, Inc.", "pi.ai/corp"]},
    {"id": "ai-041", "name": "Shield AI", "aliases": ["Shield AI, Inc.", "Shield AI Inc"]},
    {"id": "ai-042", "name": "Helsing", "aliases": ["Helsing AI", "Helsing GmbH", "Helsing Ltd"]},
    {"id": "ai-043", "name": "Sarvam AI", "aliases": ["Sarvam", "Sarvam.ai"]},
    {"id": "ai-044", "name": "Sakana AI", "aliases": ["Sakana", "Sakana AI K.K."]},
    {"id": "ai-045", "name": "Krea AI", "aliases": ["Krea", "Krea.ai"]},
    {"id": "ai-046", "name": "Suno", "aliases": ["Suno AI", "Suno, Inc."]},
    {"id": "ai-047", "name": "Udio", "aliases": ["Udio AI", "Uncharted Labs", "Uncharted Labs, Inc."]},
    {"id": "ai-048", "name": "Pika", "aliases": ["Pika Labs", "Pika Art", "Pika Labs, Inc."]},
    {"id": "ai-049", "name": "Inflection AI", "aliases": ["Inflection", "Inflection AI, Inc.", "Pi AI"]},
    {"id": "ai-050", "name": "Lambda Labs", "aliases": ["Lambda", "Lambda, Inc.", "Lambda GPU"]},
    {"id": "ai-051", "name": "Google DeepMind", "aliases": ["DeepMind", "Google AI", "DeepMind Technologies"]},
    {"id": "ai-052", "name": "Microsoft", "aliases": ["Microsoft Corp", "Microsoft Corporation", "Microsoft AI"]},
    {"id": "ai-053", "name": "Meta AI", "aliases": ["Meta", "Meta Platforms", "Facebook AI Research", "FAIR"]},
    {"id": "ai-054", "name": "NVIDIA", "aliases": ["Nvidia", "Nvidia Corp", "NVIDIA Corporation"]},
]

# Suffixes to strip during normalization
LEGAL_AND_CORP_SUFFIXES = [
    r"\binc\.?\b",
    r"\bincorporated\b",
    r"\bllc\.?\b",
    r"\bltd\.?\b",
    r"\blimited\b",
    r"\bcorp\.?\b",
    r"\bcorporation\b",
    r"\bco\.?\b",
    r"\bcompany\b",
    r"\bgmbh\b",
    r"\bsas\b",
    r"\bpbc\b",
    r"\btechnologies\b",
    r"\btechnology\b",
    r"\btech\b",
    r"\blabs\b",
    r"\blab\b",
    r"\bsolutions\b",
    r"\bsystems\b",
    r"\bglobal\b",
    r"\bai\b",
    r"\bapp\b",
    r"\bhq\b",
]


class EntityResolver:
    """
    Deterministic Entity Resolution Engine.
    Canonicalizes organization, startup, and maker names across data sources.
    """

    def __init__(self, seed_entities: Optional[List[Dict[str, Any]]] = None):
        self.seed_entities = seed_entities or CANONICAL_AI_ENTITIES
        self._exact_map: Dict[str, str] = {}
        self._normalized_map: Dict[str, str] = {}
        self._seed_ids: Dict[str, str] = {}
        self.mapping_log: List[Dict[str, Any]] = []

        self._build_indexes()

    def _build_indexes(self) -> None:
        """Construct exact and normalized lookup tables for high-speed deterministic matching."""
        for entity in self.seed_entities:
            canonical_name = entity["name"]
            entity_id = entity["id"]
            self._seed_ids[canonical_name] = entity_id

            # Exact name index
            self._exact_map[canonical_name.casefold()] = canonical_name
            self._normalized_map[self.normalize_entity_name(canonical_name)] = canonical_name

            # Alias indices
            for alias in entity.get("aliases", []):
                self._exact_map[alias.casefold()] = canonical_name
                self._normalized_map[self.normalize_entity_name(alias)] = canonical_name

    @staticmethod
    def normalize_entity_name(name: str) -> str:
        """
        Normalize an entity name by stripping punctuation, corporate suffixes,
        whitespace, and folding case.
        """
        if not name:
            return ""

        # Lowercase
        normalized = name.lower().strip()

        # Remove domain extensions (.ai, .com, .io, .co, .org, .xyz)
        normalized = re.sub(r"\.(ai|com|io|co|org|xyz|net|app|dev|sh)\b", "", normalized)

        # Remove punctuation except alphanumeric and space
        normalized = re.sub(r"[^\w\s]", " ", normalized)

        # Remove corporate/legal suffixes
        for suffix_pat in LEGAL_AND_CORP_SUFFIXES:
            normalized = re.sub(suffix_pat, " ", normalized, flags=re.IGNORECASE)

        # Collapse whitespace
        normalized = re.sub(r"\s+", " ", normalized).strip()

        return normalized

    def resolve(
        self,
        raw_name: str,
        entity_type: str = "ORGANIZATION",
        log: bool = True,
    ) -> Tuple[str, str, float]:
        """
        Resolve a raw entity name into its canonical name.

        Returns:
            Tuple[canonical_name, resolution_method, confidence_score]
        """
        if not raw_name or not raw_name.strip():
            return "", "EMPTY", 0.0

        raw_trimmed = raw_name.strip()
        casefolded = raw_trimmed.casefold()

        # Step 1: Direct Exact Match in seed database
        if casefolded in self._exact_map:
            canonical = self._exact_map[casefolded]
            self._record_log(raw_trimmed, canonical, entity_type, "EXACT_SEED", 1.0, is_seed=True, log=log)
            return canonical, "EXACT_SEED", 1.0

        # Step 2: Normalized Rule Match
        norm_key = self.normalize_entity_name(raw_trimmed)
        if norm_key in self._normalized_map:
            canonical = self._normalized_map[norm_key]
            self._record_log(raw_trimmed, canonical, entity_type, "RULE_NORMALIZED", 0.98, is_seed=True, log=log)
            return canonical, "RULE_NORMALIZED", 0.98

        # Step 3: Fuzzy Match against normalized seed names (Threshold >= 0.85)
        best_match = None
        best_ratio = 0.0

        if norm_key and len(norm_key) >= 3:
            for seed_norm, canonical in self._normalized_map.items():
                if not seed_norm:
                    continue
                ratio = difflib.SequenceMatcher(None, norm_key, seed_norm).ratio()
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_match = canonical

        if best_match and best_ratio >= 0.85:
            self._record_log(raw_trimmed, best_match, entity_type, "FUZZY_MATCH", round(best_ratio, 3), is_seed=True, log=log)
            return best_match, "FUZZY_MATCH", round(best_ratio, 3)

        # Step 4: Deterministic fallback for non-seed entities (Standardized Title Case)
        # Strip trailing noise (Inc., LLC, etc.)
        cleaned = raw_trimmed
        for suffix_pat in LEGAL_AND_CORP_SUFFIXES:
            cleaned = re.sub(suffix_pat, "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"[,\.]+$", "", cleaned).strip()

        # If stripping leaves an empty string, revert to raw trimmed
        if not cleaned:
            cleaned = raw_trimmed

        # Standardize spacing
        canonical = " ".join(cleaned.split())

        self._record_log(raw_trimmed, canonical, entity_type, "NEW_CANONICAL", 0.80, is_seed=False, log=log)
        return canonical, "NEW_CANONICAL", 0.80

    def _record_log(
        self,
        raw_name: str,
        canonical_name: str,
        entity_type: str,
        method: str,
        confidence: float,
        is_seed: bool,
        log: bool,
    ) -> None:
        """Append transformation to internal mapping audit trail."""
        if not log:
            return

        matched_seed_id = self._seed_ids.get(canonical_name, "") if is_seed else ""

        entry = {
            "raw_name": raw_name,
            "canonical_name": canonical_name,
            "entity_type": entity_type,
            "resolution_method": method,
            "confidence_score": confidence,
            "is_seed_match": is_seed,
            "matched_seed_id": matched_seed_id,
            "resolved_at": datetime.now(timezone.utc).isoformat(),
        }
        self.mapping_log.append(entry)

    def get_mapping_log(self) -> List[Dict[str, Any]]:
        """Return the complete entity mapping log."""
        return self.mapping_log

    def clear_log(self) -> None:
        """Clear recorded mapping log."""
        self.mapping_log.clear()


# Global default resolver singleton
default_entity_resolver = EntityResolver()


def resolve_entity(name: str, entity_type: str = "ORGANIZATION") -> str:
    """Convenience helper returning the canonical entity name."""
    canonical, _, _ = default_entity_resolver.resolve(name, entity_type=entity_type)
    return canonical
