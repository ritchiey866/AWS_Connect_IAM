import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    aws_region: str = os.getenv("AWS_REGION", "us-east-1")
    connect_instance_id: str = os.getenv("CONNECT_INSTANCE_ID", "")
    connect_contact_flow_id: str = os.getenv("CONNECT_CONTACT_FLOW_ID", "")
    outbound_source_phone_number: str = os.getenv("OUTBOUND_SOURCE_PHONE_NUMBER", "")
    outbound_destination_phone_number: str = os.getenv("OUTBOUND_DESTINATION_PHONE_NUMBER", "")
    dynamodb_table_name: str = os.getenv("DYNAMODB_TABLE_NAME", "connect_data")


settings = Settings()
