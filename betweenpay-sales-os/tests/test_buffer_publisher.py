from sales_os.connectors import BufferPublisher
from sales_os.store import Store


class CapturingBuffer(BufferPublisher):
    def __init__(self, store):
        super().__init__(store)
        self.variables = None

    def _channel(self, platform):
        return {"id": "channel-123", "service": "facebook"}

    def graphql(self, query, variables=None):
        self.variables = variables
        return {
            "createPost": {
                "post": {
                    "id": "post-123",
                    "status": "sent",
                    "dueAt": None,
                    "channelId": "channel-123",
                }
            }
        }


def test_facebook_post_includes_required_type_metadata(tmp_path):
    store = Store(tmp_path / "test.db")
    publisher = CapturingBuffer(store)
    post = publisher.create_post({
        "platform": "facebook",
        "post_type": "post",
        "text": "Test",
        "asset_url": "https://example.com/test.png",
        "destination": "https://betweenpay.tasklaneco.com/",
    })
    assert post["id"] == "post-123"
    payload = publisher.variables["input"]
    assert payload["metadata"]["facebook"]["type"] == "post"
