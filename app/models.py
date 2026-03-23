from typing import Any
from pydantic import BaseModel, Field


class QueueRecord(BaseModel):
    queue_id: str
    name: str
    arn: str | None = None
    description: str | None = None
    status: str | None = None
    outbound_caller_config: dict[str, Any] | None = None


class ContactRecord(BaseModel):
    contact_id: str
    channel: str | None = None
    initiation_method: str | None = None
    queue_info: dict[str, Any] | None = None
    agent_info: dict[str, Any] | None = None
    customer_endpoint: dict[str, Any] | None = None
    system_endpoint: dict[str, Any] | None = None
    disconnect_reason: str | None = None
    initiated_timestamp: str | None = None
    connected_to_agent_timestamp: str | None = None
    disconnect_timestamp: str | None = None


class SyncResponse(BaseModel):
    message: str
    queue_count: int = Field(default=0)
    contact_count: int = Field(default=0)
    table_name: str


class DemoSeedResponse(BaseModel):
    message: str
    created_queue_ids: list[str]
    created_contact_ids: list[str]


class QueueListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[QueueRecord]


class ContactListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[ContactRecord]


class DynamoEntityListResponse(BaseModel):
    entity_type: str
    count: int
    next_sk: str | None = None
    items: list[dict[str, Any]]


class DemoCleanupResponse(BaseModel):
    message: str
    deleted_queue_ids: list[str]
    deleted_contact_markers: list[str]
    failed_queue_deletes: list[str]
