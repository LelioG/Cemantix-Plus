from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from ..utils.text import ascii_key, is_valid_word_shape, letter_count, normalize_word


SECRET_STOPWORDS = {
    "alors",
    "aucun",
    "autre",
    "avec",
    "avoir",
    "comme",
    "comment",
    "contre",
    "dans",
    "depuis",
    "devant",
    "encore",
    "entre",
    "faire",
    "jamais",
    "leurs",
    "même",
    "notre",
    "nous",
    "parce",
    "pendant",
    "personne",
    "plus",
    "pourquoi",
    "quand",
    "quelque",
    "sans",
    "sera",
    "sont",
    "sous",
    "tous",
    "très",
    "votre",
}


@dataclass(frozen=True, slots=True)
class LexiconEntry:
    word: str
    normalized: str
    ascii_alias: str
    frequency: int
    rank: int
    is_secret_candidate: bool


class LexiconService:
    def __init__(self, config: dict[str, object], demo_mode: bool = False) -> None:
        self.config = config
        self.demo_mode = demo_mode
        self.cache_path = Path(str(config["LEXICON_CACHE_PATH"]))
        self.source_path = Path(str(config["LEXICON_SOURCE_PATH"]))
        self.demo_path = Path(str(config["DEMO_LEXICON_PATH"]))
        self.max_size = int(config["MAX_LEXICON_SIZE"])
        self.secret_min_rank = int(config["SECRET_POOL_MIN_RANK"])
        self.secret_max_rank = int(config["SECRET_POOL_MAX_RANK"])
        self.secret_min_length = int(config["SECRET_MIN_LENGTH"])
        self.secret_max_length = int(config["SECRET_MAX_LENGTH"])

        self.entries = self._load_entries()
        self.by_normalized = {entry.normalized: entry for entry in self.entries}
        alias_map: dict[str, list[LexiconEntry]] = {}
        for entry in self.entries:
            alias_map.setdefault(entry.ascii_alias, []).append(entry)
        self.by_ascii = {
            alias: items[0]
            for alias, items in alias_map.items()
            if len(items) == 1 and alias != items[0].normalized
        }
        self.words = [entry.word for entry in self.entries]
        self.secret_words = [entry.word for entry in self.entries if entry.is_secret_candidate]
        if not self.secret_words:
            self.secret_words = self.words[: min(len(self.words), 128)]

    def resolve(self, candidate: str) -> LexiconEntry | None:
        normalized = normalize_word(candidate)
        if not normalized:
            return None
        entry = self.by_normalized.get(normalized)
        if entry:
            return entry
        return self.by_ascii.get(ascii_key(candidate))

    def get(self, word: str) -> LexiconEntry:
        entry = self.resolve(word)
        if entry is None:
            raise KeyError(word)
        return entry

    def frequency_band(self, word: str) -> str:
        entry = self.get(word)
        if entry.rank <= 1500:
            return "très courant"
        if entry.rank <= 5000:
            return "courant"
        if entry.rank <= 12000:
            return "assez courant"
        return "plutôt rare"

    def _load_entries(self) -> list[LexiconEntry]:
        if self.demo_mode:
            return self._load_demo_entries()
        if self.cache_path.exists():
            return self._load_cache_entries(self.cache_path)
        if self.source_path.exists():
            entries = self._load_source_entries(self.source_path)
            self._write_cache(entries)
            return entries
        return self._load_demo_entries()

    def _load_cache_entries(self, path: Path) -> list[LexiconEntry]:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return [LexiconEntry(**item) for item in raw["entries"]]

    def _load_demo_entries(self) -> list[LexiconEntry]:
        raw = json.loads(self.demo_path.read_text(encoding="utf-8"))
        entries: list[LexiconEntry] = []
        for rank, word in enumerate(sorted(raw["vectors"].keys()), start=1):
            normalized = normalize_word(word)
            entries.append(
                LexiconEntry(
                    word=word,
                    normalized=normalized,
                    ascii_alias=ascii_key(word),
                    frequency=max(1, 10_000 - rank),
                    rank=rank,
                    is_secret_candidate=letter_count(word) >= 3,
                )
            )
        return entries

    def _load_source_entries(self, path: Path) -> list[LexiconEntry]:
        dedup: dict[str, LexiconEntry] = {}
        with path.open("r", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for rank, row in enumerate(reader, start=1):
                if len(dedup) >= self.max_size:
                    break
                word = normalize_word(row["word"])
                if not is_valid_word_shape(word):
                    continue
                frequency = int(row["count"])
                if word in dedup:
                    continue
                dedup[word] = LexiconEntry(
                    word=word,
                    normalized=word,
                    ascii_alias=ascii_key(word),
                    frequency=frequency,
                    rank=rank,
                    is_secret_candidate=self._is_secret_candidate(word, rank),
                )
        return list(dedup.values())

    def _is_secret_candidate(self, word: str, rank: int) -> bool:
        if rank < self.secret_min_rank or rank > self.secret_max_rank:
            return False
        if word in SECRET_STOPWORDS:
            return False
        if not word.isalpha():
            return False
        length = letter_count(word)
        if length < self.secret_min_length or length > self.secret_max_length:
            return False
        return len(set(word)) >= 3

    def _write_cache(self, entries: list[LexiconEntry]) -> None:
        payload = {
            "meta": {
                "source": str(self.source_path),
                "count": len(entries),
            },
            "entries": [asdict(entry) for entry in entries],
        }
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
