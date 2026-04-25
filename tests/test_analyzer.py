from app.analyzer.rule_analyzer import RuleAnalyzer


def test_rule_analyzer_detects_mechanics_and_2d_signal():
    features = RuleAnalyzer().analyze(
        "Devlog: new stealth update",
        "Added top-down 2d visibility system and drag and drop inventory.",
    )

    keys = {match.key for match in features.mechanics}

    assert "inventory_drag_drop" in keys
    assert "stealth" in keys
    assert features.content_type == "devlog"
    assert features.signals["is_2d_likely"] is True
