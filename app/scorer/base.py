from __future__ import annotations

from dataclasses import dataclass, field

from app.analyzer.base import FeatureSet


@dataclass(slots=True)
class ScoreResult:
    total: float
    breakdown: dict = field(default_factory=dict)
    is_relevant: bool = False


class ScorerPlugin:
    name: str = "base"

    def score(self, features: FeatureSet, profile: dict) -> ScoreResult:
        raise NotImplementedError

