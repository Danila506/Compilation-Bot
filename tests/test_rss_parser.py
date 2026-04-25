from app.collector.rss_parser import parse_feed_items


def test_parse_feed_items_reads_rss_item():
    feed = """<?xml version="1.0"?>
    <rss>
      <channel>
        <item>
          <title>Devlog update</title>
          <link>https://example.com/devlog</link>
          <guid>devlog-1</guid>
          <description>Added crafting.</description>
          <pubDate>Fri, 10 Apr 2026 12:00:00 GMT</pubDate>
        </item>
      </channel>
    </rss>
    """

    items = parse_feed_items("https://example.com/feed.xml", feed, 10, "rss")

    assert len(items) == 1
    assert items[0].external_id.endswith("devlog-1")
    assert items[0].title == "Devlog update"
    assert items[0].content == "Added crafting."
