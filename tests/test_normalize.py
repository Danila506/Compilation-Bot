from app.analyzer.normalize import clean_text


def test_clean_text_strips_html_and_bbcode():
    text = clean_text("<p>Added <b>grid inventory</b></p>[img]x[/img]\nNew crafting.")

    assert "grid inventory" in text
    assert "New crafting" in text
    assert "<" not in text
    assert "[img]" not in text
