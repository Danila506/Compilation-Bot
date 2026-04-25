import re

from app.analyzer.base import AnalyzerPlugin, FeatureSet, MechanicMatch
from app.analyzer.mechanic_dictionary import MECHANIC_ALIASES
from app.analyzer.normalize import clean_text


class RuleAnalyzer(AnalyzerPlugin):
    name = "rule_analyzer"

    def analyze(self, title: str, content: str) -> FeatureSet:
        text = clean_text(f"{title} {content}").lower()
        mechanics: list[MechanicMatch] = []
        sentences = [s.strip() for s in re.split(r"[.!?\n]+", text) if s.strip()]
        introduced_markers = [
            "added",
            "introduce",
            "introduced",
            "new",
            "implemented",
            "reworked",
            "overhauled",
            "updated",
            "improved",
            "expanded",
            "changed",
            "balanced",
            "now has",
        ]

        for mechanic_key, aliases in MECHANIC_ALIASES.items():
            hit_alias = next((a for a in aliases if a in text), None)
            if hit_alias:
                evidence_sentence = next((s for s in sentences if hit_alias in s), hit_alias)
                is_introduced = any(
                    (hit_alias in sentence) and any(marker in sentence for marker in introduced_markers)
                    for sentence in sentences
                )
                mechanics.append(
                    MechanicMatch(
                        key=mechanic_key,
                        confidence=0.8,
                        evidence=evidence_sentence[:180],
                        introduced=is_introduced,
                    )
                )

        content_type = "general"
        if "patch notes" in text or "hotfix" in text:
            content_type = "patch_notes"
        elif "devlog" in text or "development update" in text:
            content_type = "devlog"

        two_d_markers = [
            "2d",
            "top-down",
            "top down",
            "isometric",
            "pixel art",
            "sprite",
            "tilemap",
            "tileset",
            "orthographic",
        ]
        dimension_score = sum(1 for marker in two_d_markers if marker in text)
        is_2d_likely = dimension_score > 0

        return FeatureSet(
            mechanics=mechanics,
            content_type=content_type,
            signals={
                "tokens": len(text.split()),
                "dimension_score": float(dimension_score),
                "is_2d_likely": is_2d_likely,
                "analysis_text": text[:8000],
            },
        )
