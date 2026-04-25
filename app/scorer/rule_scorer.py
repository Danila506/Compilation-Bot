from app.scorer.base import ScoreResult, ScorerPlugin
from app.scorer.embeddings import cosine_similarity


class RuleScorer(ScorerPlugin):
    name = "rule_scorer"

    def __init__(self, threshold: float, prefer_2d_only: bool = True, min_2d_signal_score: float = 1.0):
        self.threshold = threshold
        self.prefer_2d_only = prefer_2d_only
        self.min_2d_signal_score = min_2d_signal_score

    def score(self, features, profile: dict) -> ScoreResult:
        weights = profile.get("mechanic_weights", {})
        negative_keywords = profile.get("negative_keywords", [])
        mechanic_score = 0.0

        for match in features.mechanics:
            mechanic_score += weights.get(match.key, 0.0) * match.confidence

        novelty = 0.2 if len(features.mechanics) >= 2 else 0.0
        content_bonus = 0.25 if features.content_type in {"devlog", "patch_notes"} else 0.0
        dimension_score = float(features.signals.get("dimension_score", 0.0))
        is_2d_likely = bool(features.signals.get("is_2d_likely", False))
        two_d_bonus = min(1.5, dimension_score * 0.5)
        non_2d_penalty = -0.75 if dimension_score <= 0 else 0.0
        profile_text = profile.get("profile_text", "")
        analysis_text = str(features.signals.get("analysis_text", ""))
        semantic_similarity = cosine_similarity(analysis_text, profile_text) if profile_text and analysis_text else 0.0
        semantic_bonus = max(0.0, semantic_similarity) * 1.2
        negative_penalty = -1.0 if any(keyword in analysis_text for keyword in negative_keywords) else 0.0

        total = mechanic_score + novelty + content_bonus + two_d_bonus + non_2d_penalty + semantic_bonus + negative_penalty
        pass_2d_gate = (not self.prefer_2d_only) or is_2d_likely or (dimension_score >= self.min_2d_signal_score)
        pass_mechanic_gate = len(features.mechanics) > 0 and mechanic_score > 0

        return ScoreResult(
            total=total,
            breakdown={
                "mechanic_score": mechanic_score,
                "novelty": novelty,
                "content_bonus": content_bonus,
                "two_d_bonus": two_d_bonus,
                "non_2d_penalty": non_2d_penalty,
                "dimension_score": dimension_score,
                "semantic_similarity": semantic_similarity,
                "semantic_bonus": semantic_bonus,
                "negative_penalty": negative_penalty,
                "pass_mechanic_gate": pass_mechanic_gate,
            },
            is_relevant=(total >= self.threshold) and pass_2d_gate and pass_mechanic_gate,
        )
