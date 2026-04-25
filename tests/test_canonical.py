from app.dedup.canonical import canonicalize_url


def test_canonicalize_url_removes_tracking_and_fragment():
    url = "https://example.com/game?utm_source=x&id=12&utm_campaign=y#section"

    assert canonicalize_url(url) == "https://example.com/game?id=12"
