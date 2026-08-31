"""Web source corpus: ranks and the hard prohibition.

Central rule: a source's RANK caps the strength of the verdict it can support.

  rank 1 -> any verdict, FALSE included
  rank 2 -> EXACT at best
  rank 3 -> no verdict at all; orients, never proves
  none   -> UNVERIFIED, never a fallback verdict

When a hosted web-search tool is used, ranks 1 and 2 are passed as
`allowed_domains` so the prohibition is enforced server-side. With a local
model there is no hosted search, and the prohibition is enforced more strongly
still: the model only ever sees the excerpts we hand it (see retrieval.py).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import yaml

ROOT = Path(__file__).resolve().parent.parent
CORPUS_PATH = ROOT / "corpus" / "sources.yaml"


@dataclass
class Corpus:
    version: str
    rank1: List[str]
    rank2: List[str]
    rank3: List[str]
    speech_rank: List[str]
    definition_traps: List[dict] = field(default_factory=list)
    prohibited: List[dict] = field(default_factory=list)

    # -- domains handed to a hosted search tool ----------------------------

    def fact_check_domains(self) -> List[str]:
        """Ranks 1 and 2 only.

        Rank 3 (already-published fact checks) is deliberately EXCLUDED: using
        it would republish someone else's verdict instead of going back to the
        primary source.
        """
        return sorted(set(self.rank1) | set(self.rank2))

    def coherence_domains(self) -> List[str]:
        """Manifestos, dated statements, recorded votes. Nothing else."""
        return sorted(set(self.speech_rank))

    # -- rank resolution ---------------------------------------------------

    def rank_of_domain(self, domain: str) -> Optional[int]:
        """Rank of a source, or None when it is outside the corpus.

        A path-qualified entry ("lemonde.fr/les-decodeurs") counts ONLY for that
        path: the bare domain stays outside the corpus, like all general press.
        Without this distinction, listing one fact-checking desk would pull in
        the entire newspaper.
        """
        ref = domain.lower().removeprefix("https://").removeprefix("http://")
        ref = ref.removeprefix("www.").rstrip("/")
        host = ref.split("/")[0]

        for rank, entries in ((1, self.rank1), (2, self.rank2), (3, self.rank3)):
            for entry in entries:
                e = entry.lower().removeprefix("www.").rstrip("/")
                if "/" in e:
                    if ref == e or ref.startswith(e + "/"):
                        return rank
                elif host == e or host.endswith("." + e):
                    return rank
        return None

    def best_rank(self, domains: List[str]) -> Optional[int]:
        ranks = [r for r in (self.rank_of_domain(d) for d in domains) if r is not None]
        return min(ranks) if ranks else None

    def definition_traps_text(self) -> str:
        """Definition traps, formatted for a prompt.

        The most common error in French fact-checking: two rank 1 sources, two
        correct figures, two incompatible definitions.
        """
        lines = []
        for trap in self.definition_traps:
            measures = "\n".join(f"    - {m}" for m in trap.get("mesures", []))
            lines.append(f"  {trap['sujet']}:\n{measures}")
            if trap.get("note"):
                lines.append(f"    -> {trap['note']}")
        return "\n".join(lines)


def load(path: Path | str = CORPUS_PATH) -> Corpus:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))

    def domains(key: str) -> List[str]:
        return list(data.get(key, {}).get("domaines", []))

    return Corpus(
        version=str(data.get("version", "unknown")),
        rank1=domains("rang1"),
        rank2=domains("rang2"),
        rank3=domains("rang3"),
        speech_rank=domains("rang_parole"),
        definition_traps=list(data.get("pieges_definition", [])),
        prohibited=list(data.get("interdits", [])),
    )


def verdict_allowed(verdict: str, rank: Optional[int]) -> bool:
    """A FALSE requires a rank 1 source. Mechanical, not discretionary."""
    if verdict == "false":
        return rank == 1
    if verdict == "exact":
        return rank in (1, 2)
    # too_vague, conflicting_sources, unverified, out_of_scope are abstention
    # states: they depend on no source.
    return True
