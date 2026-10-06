from sales_os.store import Store


def test_store_defaults_and_content(tmp_path):
    store = Store(tmp_path / "test.db")
    assert store.get_int("weekly_sales_target") == 100
    content_id = store.queue_content({
        "platform": "facebook",
        "theme": "test",
        "text": "hello",
        "scheduled_for": "2026-10-06T12:00:00+00:00",
    })
    assert content_id > 0
    row = store.content_queue(1)[0]
    assert row["platform"] == "facebook"
    store.update_content(content_id, status="published")
    assert store.content_queue(1)[0]["status"] == "published"
