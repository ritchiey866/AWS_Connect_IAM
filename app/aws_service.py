from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from app.config import settings
from app.models import ContactRecord, QueueRecord


def _to_iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def _parse_iso(dt: str | None) -> datetime | None:
    if not dt:
        return None
    normalized = dt.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _dynamo_safe(value: Any) -> Any:
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, dict):
        return {k: _dynamo_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_dynamo_safe(v) for v in value]
    return value


class AWSConnectService:
    def __init__(self) -> None:
        # IAM auth is automatic via boto3 credential chain:
        # env vars -> shared credentials -> IAM role (EC2/ECS/Lambda) etc.
        self.connect = boto3.client("connect", region_name=settings.aws_region)
        self.dynamo = boto3.resource("dynamodb", region_name=settings.aws_region)
        self.table = self.dynamo.Table(settings.dynamodb_table_name)

    def ensure_table_exists(self) -> None:
        try:
            self.table.load()
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "")
            if error_code != "ResourceNotFoundException":
                raise
            self.dynamo.create_table(
                TableName=settings.dynamodb_table_name,
                KeySchema=[
                    {"AttributeName": "pk", "KeyType": "HASH"},
                    {"AttributeName": "sk", "KeyType": "RANGE"},
                ],
                AttributeDefinitions=[
                    {"AttributeName": "pk", "AttributeType": "S"},
                    {"AttributeName": "sk", "AttributeType": "S"},
                ],
                BillingMode="PAY_PER_REQUEST",
            )
            self.table = self.dynamo.Table(settings.dynamodb_table_name)
            self.table.wait_until_exists()

    def list_queues(self) -> list[QueueRecord]:
        results: list[QueueRecord] = []
        paginator = self.connect.get_paginator("list_queues")
        for page in paginator.paginate(InstanceId=settings.connect_instance_id, QueueTypes=["STANDARD"]):
            for q in page.get("QueueSummaryList", []):
                queue_id = q["Id"]
                details = self.connect.describe_queue(
                    InstanceId=settings.connect_instance_id,
                    QueueId=queue_id,
                ).get("Queue", {})
                results.append(
                    QueueRecord(
                        queue_id=queue_id,
                        name=details.get("Name", q.get("Name", "")),
                        arn=details.get("QueueArn"),
                        description=details.get("Description"),
                        status=details.get("Status"),
                        outbound_caller_config=details.get("OutboundCallerConfig"),
                    )
                )
        return results

    def list_queues_paginated(
        self,
        *,
        limit: int,
        offset: int,
        name_contains: str | None = None,
    ) -> tuple[list[QueueRecord], int]:
        all_queues = self.list_queues()
        if name_contains:
            lowered = name_contains.lower()
            all_queues = [q for q in all_queues if lowered in q.name.lower()]
        total = len(all_queues)
        return all_queues[offset : offset + limit], total

    def get_contact_details(self, contact_id: str) -> ContactRecord:
        data = self.connect.describe_contact(
            InstanceId=settings.connect_instance_id,
            ContactId=contact_id,
        ).get("Contact", {})
        return ContactRecord(
            contact_id=contact_id,
            channel=data.get("Channel"),
            initiation_method=data.get("InitiationMethod"),
            queue_info=data.get("QueueInfo"),
            agent_info=data.get("AgentInfo"),
            customer_endpoint=data.get("CustomerEndpoint"),
            system_endpoint=data.get("SystemEndpoint"),
            disconnect_reason=data.get("DisconnectReason"),
            initiated_timestamp=_to_iso(data.get("InitiationTimestamp")),
            connected_to_agent_timestamp=_to_iso(data.get("ConnectedToAgentTimestamp")),
            disconnect_timestamp=_to_iso(data.get("DisconnectTimestamp")),
        )

    def persist_queues(self, queues: list[QueueRecord]) -> None:
        now_iso = datetime.now(timezone.utc).isoformat()
        with self.table.batch_writer() as batch:
            for queue in queues:
                item = {
                    "pk": "QUEUE",
                    "sk": queue.queue_id,
                    "entityType": "QUEUE",
                    "syncedAt": now_iso,
                    "data": queue.model_dump(),
                }
                batch.put_item(Item=_dynamo_safe(item))

    def persist_contacts(self, contacts: list[ContactRecord]) -> None:
        now_iso = datetime.now(timezone.utc).isoformat()
        with self.table.batch_writer() as batch:
            for contact in contacts:
                item = {
                    "pk": "CONTACT",
                    "sk": contact.contact_id,
                    "entityType": "CONTACT",
                    "syncedAt": now_iso,
                    "data": contact.model_dump(),
                }
                batch.put_item(Item=_dynamo_safe(item))

    def list_demo_contact_ids(self) -> list[str]:
        ids: list[str] = []
        kwargs: dict[str, Any] = {
            "KeyConditionExpression": Key("pk").eq("DEMO_CONTACT"),
        }
        while True:
            response = self.table.query(**kwargs)
            for item in response.get("Items", []):
                contact_id = item.get("sk")
                if contact_id:
                    ids.append(contact_id)
            last_key = response.get("LastEvaluatedKey")
            if not last_key:
                break
            kwargs["ExclusiveStartKey"] = last_key
        return ids

    def list_contacts_paginated(
        self,
        *,
        limit: int,
        offset: int,
        channel: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> tuple[list[ContactRecord], int]:
        from_dt = _parse_iso(from_date)
        to_dt = _parse_iso(to_date)
        if from_dt and to_dt and from_dt > to_dt:
            raise ValueError("from_date must be earlier than or equal to to_date.")

        ids = self.list_demo_contact_ids()
        contacts: list[ContactRecord] = []
        for cid in ids:
            try:
                record = self.get_contact_details(cid)
                if channel and (record.channel or "").upper() != channel.upper():
                    continue
                initiated_dt = _parse_iso(record.initiated_timestamp)
                if from_dt and initiated_dt and initiated_dt < from_dt:
                    continue
                if to_dt and initiated_dt and initiated_dt > to_dt:
                    continue
                contacts.append(record)
            except ClientError:
                continue
        total = len(contacts)
        return contacts[offset : offset + limit], total

    def query_entities_from_dynamodb(
        self,
        *,
        entity_pk: str,
        limit: int,
        start_sk: str | None = None,
    ) -> tuple[list[dict[str, Any]], str | None]:
        kwargs: dict[str, Any] = {
            "KeyConditionExpression": Key("pk").eq(entity_pk),
            "Limit": limit,
        }
        if start_sk:
            kwargs["ExclusiveStartKey"] = {"pk": entity_pk, "sk": start_sk}
        response = self.table.query(**kwargs)
        items = response.get("Items", [])
        last_key = response.get("LastEvaluatedKey")
        next_sk = None if not last_key else last_key.get("sk")
        return items, next_sk

    def create_demo_queue(self, queue_name: str, description: str = "Demo queue created by FastAPI app") -> str:
        paginator = self.connect.get_paginator("list_queues")
        for page in paginator.paginate(InstanceId=settings.connect_instance_id, QueueTypes=["STANDARD"]):
            for queue in page.get("QueueSummaryList", []):
                if queue.get("Name") == queue_name:
                    return queue["Id"]

        response = self.connect.create_queue(
            InstanceId=settings.connect_instance_id,
            Name=queue_name,
            Description=description,
            HoursOfOperationId=self._get_first_hours_of_operation_id(),
        )
        return response["QueueId"]

    def delete_queue(self, queue_id: str) -> None:
        self.connect.delete_queue(
            InstanceId=settings.connect_instance_id,
            QueueId=queue_id,
        )

    def list_demo_queue_ids(self) -> list[str]:
        queue_ids: list[str] = []
        paginator = self.connect.get_paginator("list_queues")
        for page in paginator.paginate(InstanceId=settings.connect_instance_id, QueueTypes=["STANDARD"]):
            for queue in page.get("QueueSummaryList", []):
                name = queue.get("Name", "")
                if name.startswith("demo-queue-"):
                    queue_ids.append(queue["Id"])
        return queue_ids

    def delete_demo_contact_marker(self, contact_id: str) -> None:
        self.table.delete_item(
            Key={"pk": "DEMO_CONTACT", "sk": contact_id},
        )

    def save_demo_contact_marker(self, contact_id: str) -> None:
        self.table.put_item(
            Item={
                "pk": "DEMO_CONTACT",
                "sk": contact_id,
                "entityType": "DEMO_CONTACT",
            }
        )

    def start_demo_contact(self) -> str:
        if not settings.connect_contact_flow_id:
            raise ValueError("CONNECT_CONTACT_FLOW_ID is required to start a demo contact.")
        if not settings.outbound_source_phone_number or not settings.outbound_destination_phone_number:
            raise ValueError("OUTBOUND_SOURCE_PHONE_NUMBER and OUTBOUND_DESTINATION_PHONE_NUMBER are required.")

        response = self.connect.start_outbound_voice_contact(
            InstanceId=settings.connect_instance_id,
            ContactFlowId=settings.connect_contact_flow_id,
            SourcePhoneNumber=settings.outbound_source_phone_number,
            DestinationPhoneNumber=settings.outbound_destination_phone_number,
        )
        return response["ContactId"]

    def _get_first_hours_of_operation_id(self) -> str:
        page = self.connect.list_hours_of_operations(
            InstanceId=settings.connect_instance_id,
            MaxResults=1,
        )
        items = page.get("HoursOfOperationSummaryList", [])
        if not items:
            raise ValueError("No Hours of Operation found in this Connect instance.")
        return items[0]["Id"]

