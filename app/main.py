from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from botocore.exceptions import ClientError

from app.aws_service import AWSConnectService
from app.config import settings
from app.models import (
    ContactListResponse,
    DemoCleanupResponse,
    DemoSeedResponse,
    DynamoEntityListResponse,
    QueueListResponse,
    SyncResponse,
)

service = AWSConnectService()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    service.ensure_table_exists()
    yield


app = FastAPI(title="AWS Connect + DynamoDB API", version="1.0.0", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/connect/queues", response_model=QueueListResponse)
def get_connect_queues(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    name_contains: str | None = Query(default=None),
) -> QueueListResponse:
    try:
        items, total = service.list_queues_paginated(limit=limit, offset=offset, name_contains=name_contains)
        return QueueListResponse(total=total, limit=limit, offset=offset, items=items)
    except (ClientError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/connect/contacts", response_model=ContactListResponse)
def get_connect_contacts(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    channel: str | None = Query(default=None, description="Example: VOICE, CHAT, TASK"),
    from_date: str | None = Query(default=None, description="ISO-8601 date-time"),
    to_date: str | None = Query(default=None, description="ISO-8601 date-time"),
) -> ContactListResponse:
    try:
        items, total = service.list_contacts_paginated(
            limit=limit,
            offset=offset,
            channel=channel,
            from_date=from_date,
            to_date=to_date,
        )
        return ContactListResponse(total=total, limit=limit, offset=offset, items=items)
    except (ClientError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/sync/connect-data", response_model=SyncResponse)
def sync_connect_data() -> SyncResponse:
    try:
        queues = service.list_queues()
        service.persist_queues(queues)

        contacts = []
        for queue in queues:
            # Collect the latest contact ids from each queue.
            # For real production usage, consider CTR stream or contact search strategy.
            queue_contacts = service.connect.get_current_metric_data(
                InstanceId=settings.connect_instance_id,
                Filters={"Queues": [queue.queue_id], "Channels": ["VOICE"]},
                Groupings=["QUEUE"],
                CurrentMetrics=[{"Name": "CONTACTS_IN_QUEUE", "Unit": "COUNT"}],
            )
            # This endpoint provides metrics, not contact ids. Kept to show queue-level contact signal.
            # Contact detail persistence happens from demo-created contact ids below or external source.
            _ = queue_contacts

        # Persist contact data for contacts created by this demo in DynamoDB index items.
        for cid in service.list_demo_contact_ids():
            if not cid:
                continue
            try:
                contacts.append(service.get_contact_details(cid))
            except ClientError:
                # Contact may no longer be queryable.
                continue

        service.persist_contacts(contacts)
        return SyncResponse(
            message="Successfully synced queues and contacts to DynamoDB.",
            queue_count=len(queues),
            contact_count=len(contacts),
            table_name=settings.dynamodb_table_name,
        )
    except (ClientError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/demo/seed", response_model=DemoSeedResponse)
def seed_demo_data() -> DemoSeedResponse:
    created_queue_ids: list[str] = []
    created_contact_ids: list[str] = []
    try:
        for i in range(1, 3):
            queue_id = service.create_demo_queue(queue_name=f"demo-queue-{i}")
            created_queue_ids.append(queue_id)

        # Create one demo outbound contact (requires a valid flow/phone numbers).
        contact_id = service.start_demo_contact()
        created_contact_ids.append(contact_id)

        for cid in created_contact_ids:
            service.save_demo_contact_marker(cid)

        return DemoSeedResponse(
            message="Demo queues and contact created successfully.",
            created_queue_ids=created_queue_ids,
            created_contact_ids=created_contact_ids,
        )
    except (ClientError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.delete("/demo/cleanup", response_model=DemoCleanupResponse)
def cleanup_demo_data() -> DemoCleanupResponse:
    deleted_queue_ids: list[str] = []
    deleted_contact_markers: list[str] = []
    failed_queue_deletes: list[str] = []
    try:
        for queue_id in service.list_demo_queue_ids():
            try:
                service.delete_queue(queue_id)
                deleted_queue_ids.append(queue_id)
            except ClientError:
                failed_queue_deletes.append(queue_id)

        for contact_id in service.list_demo_contact_ids():
            service.delete_demo_contact_marker(contact_id)
            deleted_contact_markers.append(contact_id)

        return DemoCleanupResponse(
            message="Demo cleanup finished.",
            deleted_queue_ids=deleted_queue_ids,
            deleted_contact_markers=deleted_contact_markers,
            failed_queue_deletes=failed_queue_deletes,
        )
    except (ClientError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/data/queues", response_model=DynamoEntityListResponse)
def get_saved_queues(
    limit: int = Query(default=20, ge=1, le=100),
    start_sk: str | None = Query(default=None),
) -> DynamoEntityListResponse:
    try:
        items, next_sk = service.query_entities_from_dynamodb(entity_pk="QUEUE", limit=limit, start_sk=start_sk)
        return DynamoEntityListResponse(entity_type="QUEUE", count=len(items), next_sk=next_sk, items=items)
    except ClientError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/data/contacts", response_model=DynamoEntityListResponse)
def get_saved_contacts(
    limit: int = Query(default=20, ge=1, le=100),
    start_sk: str | None = Query(default=None),
) -> DynamoEntityListResponse:
    try:
        items, next_sk = service.query_entities_from_dynamodb(entity_pk="CONTACT", limit=limit, start_sk=start_sk)
        return DynamoEntityListResponse(entity_type="CONTACT", count=len(items), next_sk=next_sk, items=items)
    except ClientError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
