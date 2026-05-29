from __future__ import annotations

import hashlib
import json
import random
from collections import OrderedDict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np

from ..utils.text import letter_count, mask_word, normalize_word, reveal_pattern
from .lexicon import LexiconService

try:
    import fasttext
except ImportError:  # pragma: no cover
    fasttext = None


@dataclass(frozen=True, slots=True)
class SecretProfile:
    similarities: np.ndarray
    ranks: np.ndarray
    neighbors: list[str]


class SemanticService:
    def __init__(self, config: dict[str, object], lexicon: LexiconService) -> None:
        self.config = config
        self.lexicon = lexicon
        self.demo_mode = lexicon.demo_mode
        self._profile_cache: OrderedDict[str, SecretProfile] = OrderedDict()
        self._profile_cache_limit = 48

        if self.demo_mode:
            self.engine_name = "demo"
            self.model = None
            self._demo_vectors = self._load_demo_vectors(Path(str(config["DEMO_LEXICON_PATH"])))
            self.vector_matrix = self._build_demo_matrix()
        else:
            model_path = self._resolve_model_path()
            self.engine_name = "fasttext"
            if fasttext is None:
                raise RuntimeError("Le module fasttext est requis pour le moteur sémantique.")
            self.model = fasttext.load_model(str(model_path))
            self._demo_vectors = {}
            self.vector_matrix = self._build_fasttext_matrix()

        norms = np.linalg.norm(self.vector_matrix, axis=1, keepdims=True)
        self.normalized_matrix = self.vector_matrix / np.clip(norms, 1e-12, None)
        self.word_to_index = {word: index for index, word in enumerate(self.lexicon.words)}

    def _resolve_model_path(self) -> Path:
        primary = Path(str(self.config["FASTTEXT_MODEL_PATH"]))
        fallback = Path(str(self.config["FASTTEXT_MODEL_FALLBACK_PATH"]))
        if primary.exists():
            return primary
        if fallback.exists():
            return fallback
        raise FileNotFoundError("Aucun modèle fastText français n'a été trouvé.")

    def _load_demo_vectors(self, path: Path) -> dict[str, np.ndarray]:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return {
            normalize_word(word): np.array(vector, dtype=np.float32)
            for word, vector in raw["vectors"].items()
        }

    def _build_demo_matrix(self) -> np.ndarray:
        vectors = [self._demo_vectors[word] for word in self.lexicon.words]
        return np.vstack(vectors).astype(np.float32)

    def _build_fasttext_matrix(self) -> np.ndarray:
        return np.vstack(
            [self.model.get_word_vector(word).astype(np.float32) for word in self.lexicon.words]
        )

    def choose_daily_secret(self, for_date: date) -> str:
        words = self.lexicon.secret_words
        digest = hashlib.sha256(for_date.isoformat().encode("utf-8")).hexdigest()
        return words[int(digest, 16) % len(words)]

    def choose_random_secret(self) -> str:
        return random.choice(self.lexicon.secret_words)

    def validate_custom_secret(self, candidate: str) -> str | None:
        entry = self.lexicon.resolve(candidate)
        if entry is None:
            return None
        if letter_count(entry.word) < max(3, int(self.config["SECRET_MIN_LENGTH"]) - 1):
            return None
        return entry.word

    def score_guess(self, guess_word: str, secret_word: str) -> dict[str, Any]:
        guess = self.lexicon.get(guess_word).word
        secret = self.lexicon.get(secret_word).word
        profile = self._get_secret_profile(secret)
        index = self.word_to_index[guess]
        similarity = float(profile.similarities[index])
        rank = int(profile.ranks[index])
        percentile = round(((len(self.lexicon.words) - rank + 1) / len(self.lexicon.words)) * 100, 2)
        exact = guess == secret
        score = 1000 if exact else int(round(max(0.0, similarity) * 1000))
        return {
            "word": guess,
            "score": score,
            "similarity": round(similarity, 4),
            "semantic_rank": rank,
            "percentile": percentile,
            "temperature": self.temperature_label(rank, exact),
            "exact": exact,
        }

    def temperature_label(self, rank: int, exact: bool = False) -> str:
        if exact:
            return "Trouvé"
        if rank <= 25:
            return "Brûlant"
        if rank <= 150:
            return "Très chaud"
        if rank <= 750:
            return "Chaud"
        if rank <= 2500:
            return "Tiède"
        if rank <= 7000:
            return "Froid"
        return "Glacial"

    def build_hint_sequence(self, secret_word: str) -> list[tuple[str, str]]:
        secret = self.lexicon.get(secret_word).word
        profile = self._get_secret_profile(secret)
        length = letter_count(secret)
        neighbor = profile.neighbors[0] if profile.neighbors else None
        hints = [
            ("frequency", f"Le mot secret est {self.lexicon.frequency_band(secret)}."),
            ("length", f"Le mot contient {length} lettres."),
            ("initial", f"Il commence par « {secret[0].upper()} »."),
            ("pattern", f"Motif partiel : {reveal_pattern(secret)}."),
        ]
        if neighbor:
            hints.append(("neighbor", f"Voisin sémantique utile : « {neighbor} »."))
        else:
            hints.append(("ending", f"Il se termine par « {secret[-1].upper()} »."))
        return hints

    def mask_secret(self, secret_word: str) -> str:
        return mask_word(secret_word)

    def engine_meta(self) -> dict[str, Any]:
        return {
            "name": self.engine_name,
            "word_count": len(self.lexicon.words),
            "secret_pool_size": len(self.lexicon.secret_words),
        }

    def _get_secret_profile(self, secret_word: str) -> SecretProfile:
        secret = self.lexicon.get(secret_word).word
        cached = self._profile_cache.get(secret)
        if cached is not None:
            self._profile_cache.move_to_end(secret)
            return cached

        vector = self._secret_vector(secret)
        similarities = self.normalized_matrix @ vector
        order = np.argsort(similarities)[::-1]
        ranks = np.empty(len(self.lexicon.words), dtype=np.int32)
        ranks[order] = np.arange(1, len(order) + 1)
        neighbors = [
            self.lexicon.words[index]
            for index in order
            if self.lexicon.words[index] != secret
        ][:12]
        profile = SecretProfile(similarities=similarities, ranks=ranks, neighbors=neighbors)
        self._profile_cache[secret] = profile
        self._profile_cache.move_to_end(secret)
        if len(self._profile_cache) > self._profile_cache_limit:
            self._profile_cache.popitem(last=False)
        return profile

    def _secret_vector(self, secret_word: str) -> np.ndarray:
        secret = normalize_word(secret_word)
        if self.demo_mode:
            vector = self._demo_vectors[secret]
        else:
            vector = self.model.get_word_vector(secret).astype(np.float32)
        norm = np.linalg.norm(vector)
        return vector / max(norm, 1e-12)
