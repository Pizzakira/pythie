"""Dynamic brief composition.

The corpus is STABLE DATA, authored upstream and versioned: primary sources,
their provenance metadata, and the background briefs. It does not change at
runtime and no agent writes into it.

What the model receives is not that whole base. It is a brief COMPOSED for the
claim at hand: the applicable definitions, the traps that apply to them, and
the shortlist of primary sources worth opening.

Two consequences:

  - Context stays constant whatever the corpus size. Adding a hundred domains
    does not lengthen a single prompt.
  - Routing costs no model call. Term matching against the glossary is
    deterministic, instant, and auditable -- you can log exactly why a domain
    was selected, which you cannot do with a model's routing decision.

The composed brief still only ORIENTS. Quotes must come from primary sources;
`retrieval.validate_provenance` enforces that separately.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml

from .retrieval import LocalBase

ROOT = Path(__file__).resolve().parent.parent
GLOSSARY_PATH = ROOT / "corpus" / "glossaire.yaml"


def _flatten(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c)).lower()


@dataclass
class Measure:
    """One way of measuring a term. Several may compete for the same word."""

    key: str
    label: str
    definition: str
    producer: str
    source_url: str
    unit: str = ""


@dataclass
class Term:
    """A glossary entry: one word, several incompatible measures."""

    key: str
    label: str
    measures: List[Measure] = field(default_factory=list)
    warning: str = ""
    triggers: Tuple[str, ...] = ()

    def is_trap(self) -> bool:
        """More than one measure means the word is ambiguous, and ambiguity is
        where wrong verdicts come from."""
        return len(self.measures) > 1


@dataclass
class Glossary:
    version: str
    terms: Dict[str, Term] = field(default_factory=dict)

    def match(self, text: str) -> List[Term]:
        """Terms invoked by a claim. Deterministic word matching, no model."""
        flat = _flatten(text)
        found = []
        for term in self.terms.values():
            if any(re.search(rf"\b{re.escape(t)}", flat) for t in term.triggers):
                found.append(term)
        return found


# Surface forms that route to a glossary key. Written out rather than derived,
# because morphology matters here: "chomeurs" must route to "chomage".
TERM_TRIGGERS: Dict[str, Tuple[str, ...]] = {
    "chomage": ("chomage", "chomeur", "demandeur d'emploi", "demandeurs d'emploi",
                "sans emploi", "categorie a", "france travail", "pole emploi"),
    "inflation": ("inflation", "prix a la consommation", "hausse des prix",
                  "ipc", "ipch", "vie chere"),
    "pib": ("pib", "croissance", "produit interieur brut", "recession"),
    "immigre": ("immigre", "immigration", "etranger", "titre de sejour",
                "asile", "migrant", "naturalisation"),
    "dette_publique": ("dette", "deficit", "maastricht", "endettement"),
    "pauvrete": ("pauvrete", "pauvre", "seuil de pauvrete", "precarite"),
    "pouvoir_achat": ("pouvoir d'achat", "niveau de vie", "revenu disponible",
                      "salaire reel"),
    "delinquance": ("delinquance", "insecurite", "faits constates", "criminalite",
                    "victimation"),
}

# Which local base domain serves a glossary term.
TERM_TO_DOMAIN: Dict[str, str] = {
    "chomage": "emploi",
    "pouvoir_achat": "emploi",
    "inflation": "prix",
    "pib": "economie",
    "dette_publique": "finances-publiques",
    "immigre": "immigration",
    "pauvrete": "social",
    "delinquance": "securite",
}


def load_glossary(path: Path | str = GLOSSARY_PATH) -> Glossary:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    glossary = Glossary(version=str(data.get("version", "unknown")))

    for key, entry in (data.get("termes") or {}).items():
        measures = [
            Measure(
                key=m.get("cle", ""),
                label=m.get("libelle", ""),
                definition=(m.get("definition", "") or "").strip(),
                producer=m.get("producteur", ""),
                source_url=m.get("source", ""),
                unit=m.get("unite", ""),
            )
            for m in (entry.get("mesures") or [])
        ]
        glossary.terms[key] = Term(
            key=key,
            label=entry.get("libelle", key),
            measures=measures,
            warning=(entry.get("alerte", "") or "").strip(),
            triggers=TERM_TRIGGERS.get(key, (key,)),
        )
    return glossary


@dataclass
class Brief:
    """A brief composed for one claim."""

    text: str
    domains: List[str]
    source_keys: List[str]
    terms: List[str]
    trap: bool = False

    def is_empty(self) -> bool:
        return not self.source_keys


def compose(
    claim: str,
    glossary: Glossary,
    base: LocalBase,
    max_sources: int = 3,
) -> Brief:
    """Build the orientation material for a single claim.

    Only what applies is included. A claim about unemployment never sees the
    immigration definitions.
    """
    terms = glossary.match(claim)
    domains: List[str] = []
    for term in terms:
        domain = TERM_TO_DOMAIN.get(term.key)
        if domain and domain in base.domains and domain not in domains:
            domains.append(domain)

    source_keys: List[str] = []
    for domain in domains:
        for key in sorted(base.domains[domain].sources):
            if key not in source_keys and len(source_keys) < max_sources:
                source_keys.append(key)

    sections: List[str] = []

    # 1. Definitions -- sourced, never asserted by the tool itself.
    for term in terms:
        block = [f"TERME : {term.label}"]
        if term.warning:
            block.append(f"ATTENTION : {term.warning}")
        for measure in term.measures:
            block.append(
                f"  - {measure.label}"
                f"{f' [{measure.unit}]' if measure.unit else ''}\n"
                f"      {measure.definition}\n"
                f"      producteur : {measure.producer}\n"
                f"      definition publiee : {measure.source_url}"
            )
        if term.is_trap():
            block.append(
                "  Ces mesures NE SE COMPARENT PAS entre elles. Determine "
                "laquelle le locuteur invoque avant toute comparaison."
            )
        sections.append("\n".join(block))

    # 2. Available primary sources.
    if source_keys:
        inventory = ["SOURCES PRIMAIRES DISPONIBLES :"]
        for domain in domains:
            for key in source_keys:
                source = base.read(domain, key)
                if source:
                    inventory.append(
                        f"  - {key}\n"
                        f"      {source.measure}\n"
                        f"      {source.producer}, {source.vintage} (rang {source.rank})"
                    )
        sections.append("\n".join(inventory))
    else:
        sections.append(
            "SOURCES PRIMAIRES DISPONIBLES : aucune pour ce sujet.\n"
            "  Le verdict devra etre `unverified` : c'est un defaut de notre "
            "base, pas une refutation."
        )

    return Brief(
        text="\n\n".join(sections),
        domains=domains,
        source_keys=source_keys,
        terms=[t.key for t in terms],
        trap=any(t.is_trap() for t in terms),
    )


def routing_report(brief: Brief) -> str:
    """One auditable line per routing decision.

    A model's routing choice cannot be explained after the fact. This one can.
    """
    return (
        f"terms={brief.terms or '-'} domains={brief.domains or '-'} "
        f"sources={brief.source_keys or '-'}"
        f"{' TRAP' if brief.trap else ''}"
    )
