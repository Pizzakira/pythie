"""Pyramid retrieval over the local document base.

    corpus/base/
      INDEX.md                     level 0 -- which domains exist
      <domain>/
        FICHE.md                   level 1 -- where to find what, which
                                   definitions apply, which traps to avoid
        sources/
          <file>                   level 2 -- THE STORED PRIMARY SOURCE
          <file>.meta.yaml         provenance: origin url, retrieval date,
                                   checksum, rank, measure definition

CARDINAL RULE
-------------
A BRIEF ORIENTS. IT NEVER PROVES.

A brief (FICHE.md) is a synthesis we wrote ourselves; quoting it would be
quoting ourselves. It exists to route the model to the right document.
Every quote kept in a verdict must come from a file under `sources/`.
`validate_provenance()` enforces this and rejects the rest -- a program check,
not a prompt instruction.

Same rule as rank 3 in the web corpus, applied internally.

The model never searches: it walks down the pyramid and reads what we hand it.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "corpus" / "base"


@dataclass
class PrimarySource:
    """A document stored at the bottom of the pyramid. The only thing that proves."""

    path: Path
    origin_url: str          # so the READER can check for themselves
    producer: str
    rank: int
    measure: str             # the exact quantity, with its definition
    vintage: str
    unit: str = ""
    retrieved_on: str = ""
    checksum: str = ""       # sha256: the origin site can change under us

    def text(self, max_chars: int = 40000) -> str:
        return self.path.read_text(encoding="utf-8", errors="replace")[:max_chars]

    def checksum_matches(self) -> Optional[bool]:
        if not self.checksum:
            return None
        return hashlib.sha256(self.path.read_bytes()).hexdigest() == self.checksum


@dataclass
class Domain:
    name: str
    brief: str                                    # FICHE.md content -- ORIENTS ONLY
    sources: Dict[str, PrimarySource] = field(default_factory=dict)


@dataclass
class LocalBase:
    index: str                                    # INDEX.md content
    domains: Dict[str, Domain] = field(default_factory=dict)

    # -- level 0 -----------------------------------------------------------

    def summary(self) -> str:
        """What we show the model so it can pick a domain."""
        lines = [self.index, "", "Available domains:"]
        for name, d in sorted(self.domains.items()):
            lines.append(f"  - {name} ({len(d.sources)} primary source(s))")
        return "\n".join(lines)

    # -- level 1 -----------------------------------------------------------

    def orient(self, domain: str) -> str:
        """The domain brief. Orients the model; proves nothing."""
        d = self.domains.get(domain)
        if not d:
            known = ", ".join(sorted(self.domains)) or "none"
            return f"Unknown domain '{domain}'. Known domains: {known}."
        inventory = "\n".join(
            f"  - {key} -- {s.measure} ({s.producer}, {s.vintage})"
            for key, s in sorted(d.sources.items())
        )
        return f"{d.brief}\n\nPrimary sources in this domain:\n{inventory}"

    # -- level 2 -----------------------------------------------------------

    def read(self, domain: str, key: str) -> Optional[PrimarySource]:
        d = self.domains.get(domain)
        return d.sources.get(key) if d else None

    def all_sources(self) -> List[PrimarySource]:
        return [s for d in self.domains.values() for s in d.sources.values()]


def load(base: Path = BASE) -> LocalBase:
    base = Path(base)
    index_file = base / "INDEX.md"
    result = LocalBase(
        index=index_file.read_text(encoding="utf-8") if index_file.exists() else ""
    )
    if not base.exists():
        return result

    for directory in sorted(p for p in base.iterdir() if p.is_dir()):
        brief_file = directory / "FICHE.md"
        domain = Domain(
            name=directory.name,
            brief=brief_file.read_text(encoding="utf-8") if brief_file.exists() else "",
        )
        sources_dir = directory / "sources"
        if sources_dir.is_dir():
            for meta_file in sorted(sources_dir.glob("*.meta.yaml")):
                stem = meta_file.name[: -len(".meta.yaml")]
                candidates = [
                    c for c in sources_dir.glob(stem + ".*")
                    if not c.name.endswith(".meta.yaml")
                ]
                if not candidates:
                    continue
                meta = yaml.safe_load(meta_file.read_text(encoding="utf-8")) or {}
                domain.sources[stem] = PrimarySource(
                    path=candidates[0],
                    origin_url=meta.get("url_origine", ""),
                    producer=meta.get("producteur", ""),
                    rank=int(meta.get("rang", 1)),
                    measure=meta.get("grandeur", ""),
                    vintage=str(meta.get("millesime", "")),
                    unit=meta.get("unite", ""),
                    retrieved_on=str(meta.get("date_consultation", "")),
                    checksum=meta.get("empreinte", ""),
                )
        result.domains[directory.name] = domain
    return result


# --- provenance control ----------------------------------------------------

# Runs of dots, dashes or underscores are layout, not content. A source laid
# out as "2025 ......... 43,6 % du PIB" cannot be quoted verbatim by any model:
# it writes "2025 : 43,6 % du PIB", and a literal comparison fails on decoration
# the model was right to drop. Collapsing them is what makes the quote check a
# test of fidelity rather than a test of typography.
_DECORATION = re.compile(r"[.\-_·•]{2,}")


def _flatten(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = _DECORATION.sub(" ", text)
    return " ".join(text.lower().split())


def validate_provenance(
    quote: str, base: LocalBase, domain: Optional[str] = None
) -> Tuple[bool, Optional[PrimarySource], str]:
    """Look for the quote in PRIMARY SOURCES only.

    Returns (found, source, reason).

    A quote that appears only in a FICHE.md is REJECTED: the brief is our own
    synthesis, and using it as proof would be circular.
    """
    needle = _flatten(quote)
    if len(needle) < 12:
        return False, None, "quote too short to be verifiable"

    domains = (
        [base.domains[domain]] if domain in base.domains else list(base.domains.values())
    )

    for d in domains:
        for source in d.sources.values():
            if needle in _flatten(source.text()):
                return True, source, "found in a primary source"

    # Diagnostic: is it in a brief? That case deserves its own message.
    for d in domains:
        if needle in _flatten(d.brief):
            return False, None, (
                f"quote found in the '{d.name}' brief and not in a primary "
                "source -- rejected: a brief orients, it does not prove"
            )

    return False, None, "quote not found in any primary source"


def context_for_verification(
    base: LocalBase, domain: str, keys: List[str], max_chars: int = 12000
) -> str:
    """Assemble the excerpts handed to the model.

    The model receives ONLY this. What is not here does not exist for it --
    the hard prohibition, enforced by construction rather than by instruction.
    """
    chunks: List[str] = []
    per_source = max_chars // max(len(keys), 1)
    for key in keys:
        source = base.read(domain, key)
        if not source:
            continue
        chunks.append(
            f"--- PRIMARY SOURCE: {key} ---\n"
            f"producer : {source.producer} (rank {source.rank})\n"
            f"measure  : {source.measure}\n"
            f"vintage  : {source.vintage}{(' ' + source.unit) if source.unit else ''}\n"
            f"url      : {source.origin_url}\n\n"
            f"{source.text(per_source)}\n"
        )
    return "\n".join(chunks) if chunks else "(no primary source supplied)"
