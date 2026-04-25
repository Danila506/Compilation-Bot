from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class MechanicMatch:
    key: str
    confidence: float
    evidence: str
    introduced: bool = False


@dataclass(slots=True)
class FeatureSet:
    mechanics: list[MechanicMatch] = field(default_factory=list)
    content_type: str = "unknown"
    signals: dict = field(default_factory=dict)


class AnalyzerPlugin:
    name: str = "base"

    def analyze(self, title: str, content: str) -> FeatureSet:
        raise NotImplementedError
