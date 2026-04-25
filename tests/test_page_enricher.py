from app.collector.page_enricher import extract_page_info


def test_extract_page_info_reads_open_graph_and_article():
    html = """
    <html>
      <head>
        <meta property="og:title" content="Devlog">
        <meta property="og:description" content="Added stealth and noise systems.">
        <meta property="og:image" content="/cover.jpg">
      </head>
      <body><article>New grid inventory and crafting workbench.</article></body>
    </html>
    """

    info = extract_page_info(html, "https://example.com/post")

    assert info["title"] == "Devlog"
    assert "grid inventory" in info["text"]
    assert info["image_url"] == "https://example.com/cover.jpg"
