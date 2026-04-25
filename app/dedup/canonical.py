from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


def canonicalize_url(url: str) -> str:
    parsed = urlparse(url)
    filtered_query = [
        (k, v)
        for k, v in parse_qsl(parsed.query, keep_blank_values=True)
        if not k.startswith("utm_")
    ]
    normalized = parsed._replace(query=urlencode(filtered_query), fragment="")
    return urlunparse(normalized)

