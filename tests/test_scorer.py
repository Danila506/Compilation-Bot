from app.analyzer.base import FeatureSet, MechanicMatch
from app.scorer.rule_scorer import RuleScorer


def test_rule_scorer_applies_negative_keywords():
    features = FeatureSet(
        mechanics=[MechanicMatch("crafting", 1.0, "added crafting")],
        content_type="devlog",
        signals={
            "dimension_score": 2.0,
            "is_2d_likely": True,
            "analysis_text": "2d top-down survival crafting battle royale",
        },
    )

    scorer = RuleScorer(threshold=1.0)
    base_profile = {
        "mechanic_weights": {"crafting": 1.0},
        "profile_text": "2d top-down survival crafting",
    }
    score_without_negative = scorer.score(features, base_profile)
    score = scorer.score(
        features,
        {
            **base_profile,
            "negative_keywords": ["battle royale"],
        },
    )

    assert score.breakdown["negative_penalty"] == -1.0
    assert score.total == score_without_negative.total - 1.0
