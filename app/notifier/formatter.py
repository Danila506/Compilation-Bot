def _prettify_mechanic_key(key: str) -> str:
    return key.replace("_", " ")


def format_alert(title: str, url: str, score: float, mechanics: list[dict], document_id: int | None = None) -> str:
    if mechanics:
        detected_lines = [
            f"- {_prettify_mechanic_key(m['key'])} ({m.get('evidence', '')[:70]})"
            for m in mechanics
        ]
    else:
        detected_lines = ["- no mechanic tags"]

    introduced = [m for m in mechanics if m.get("introduced")]
    introduced_lines = [f"- {_prettify_mechanic_key(m['key'])}" for m in introduced] or ["- none"]

    return (
        f"Relevant finding (score={score:.2f})\n"
        f"ID: {document_id if document_id is not None else 'n/a'}\n"
        f"{title}\n"
        f"Detected mechanics:\n" + "\n".join(detected_lines) + "\n"
        f"Introduced mechanics:\n" + "\n".join(introduced_lines) + "\n"
        f"{url}"
    )
