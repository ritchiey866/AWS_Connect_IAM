from fastapi.testclient import TestClient

import app.main as main_module
from app.models import ContactRecord, QueueRecord


class FakeService:
    def ensure_table_exists(self) -> None:
        return None

    def list_queues_paginated(self, *, limit: int, offset: int, name_contains: str | None = None):
        queues = [
            QueueRecord(queue_id="q1", name="demo-queue-1"),
            QueueRecord(queue_id="q2", name="sales"),
        ]
        if name_contains:
            queues = [q for q in queues if name_contains.lower() in q.name.lower()]
        return queues[offset : offset + limit], len(queues)

    def list_contacts_paginated(
        self,
        *,
        limit: int,
        offset: int,
        channel: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
    ):
        contacts = [
            ContactRecord(
                contact_id="c1",
                channel="VOICE",
                initiated_timestamp="2026-03-10T12:00:00+00:00",
            )
        ]
        if channel:
            contacts = [c for c in contacts if c.channel == channel]
        return contacts[offset : offset + limit], len(contacts)

    def list_queues(self):
        return [QueueRecord(queue_id="q1", name="demo-queue-1")]

    def persist_queues(self, queues):
        return None

    def list_demo_contact_ids(self):
        return ["c1"]

    def get_contact_details(self, cid: str):
        return ContactRecord(contact_id=cid, channel="VOICE")

    def persist_contacts(self, contacts):
        return None

    def create_demo_queue(self, queue_name: str):
        return f"id-{queue_name}"

    def start_demo_contact(self):
        return "demo-contact-1"

    def list_demo_queue_ids(self):
        return ["q1", "q2"]

    def delete_queue(self, queue_id: str):
        return None

    def delete_demo_contact_marker(self, contact_id: str):
        return None

    def save_demo_contact_marker(self, contact_id: str):
        return None

    def query_entities_from_dynamodb(self, *, entity_pk: str, limit: int, start_sk: str | None = None):
        items = [{"pk": entity_pk, "sk": "1"}]
        return items[:limit], None


def make_client() -> TestClient:
    main_module.service = FakeService()
    return TestClient(main_module.app)


def test_get_connect_queues() -> None:
    client = make_client()
    response = client.get("/connect/queues", params={"limit": 10, "offset": 0, "name_contains": "demo"})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["name"] == "demo-queue-1"


def test_get_connect_contacts_with_filters() -> None:
    client = make_client()
    response = client.get(
        "/connect/contacts",
        params={
            "limit": 10,
            "offset": 0,
            "channel": "VOICE",
            "from_date": "2026-03-01T00:00:00Z",
            "to_date": "2026-03-31T23:59:59Z",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["contact_id"] == "c1"


def test_demo_cleanup() -> None:
    client = make_client()
    response = client.delete("/demo/cleanup")
    assert response.status_code == 200
    body = response.json()
    assert body["deleted_queue_ids"] == ["q1", "q2"]
    assert body["deleted_contact_markers"] == ["c1"]


def test_demo_seed() -> None:
    client = make_client()
    response = client.post("/demo/seed")
    assert response.status_code == 200
    body = response.json()
    assert len(body["created_queue_ids"]) == 2
    assert body["created_contact_ids"] == ["demo-contact-1"]


def test_data_endpoints() -> None:
    client = make_client()
    queue_response = client.get("/data/queues", params={"limit": 10})
    contact_response = client.get("/data/contacts", params={"limit": 10})
    assert queue_response.status_code == 200
    assert contact_response.status_code == 200
    assert queue_response.json()["entity_type"] == "QUEUE"
    assert contact_response.json()["entity_type"] == "CONTACT"
