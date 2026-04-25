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


def test_rule_scorer_rejects_semantic_match_without_mechanics():
    features = FeatureSet(
        mechanics=[],
        content_type="general",
        signals={
            "dimension_score": 3.0,
            "is_2d_likely": True,
            "analysis_text": "2d top-down survival zombie crafting",
        },
    )

    score = RuleScorer(threshold=1.0).score(
        features,
        {
            "mechanic_weights": {"crafting": 1.0},
            "profile_text": "2d top-down survival zombie crafting",
        },
    )

    assert score.total >= 1.0
    assert score.is_relevant is False
