# AWS Connect FastAPI (IAM Auth + DynamoDB)

This project provides a FastAPI application that:
- Uses **IAM authentication** (via boto3 default credential provider chain).
- Reads Amazon Connect **queues**.
- Reads Amazon Connect **contact details** (for demo-created contacts).
- Saves queue/contact data into **DynamoDB**.
- Creates idempotent demo Connect queues and an outbound demo contact.

## 1) Prerequisites

- Python 3.10+
- AWS account with Amazon Connect instance already created
- IAM principal (user/role) configured locally via:
  - `aws configure`, or
  - environment variables, or
  - attached role (EC2/ECS/Lambda)

## 2) Required IAM permissions

Attach a policy with least privilege for your Connect instance and DynamoDB table.
Example (adjust ARNs and region/account):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "connect:ListQueues",
        "connect:DescribeQueue",
        "connect:DescribeContact",
        "connect:CreateQueue",
        "connect:DeleteQueue",
        "connect:ListHoursOfOperations",
        "connect:StartOutboundVoiceContact",
        "connect:GetCurrentMetricData"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:CreateTable",
        "dynamodb:DescribeTable",
        "dynamodb:PutItem",
        "dynamodb:BatchWriteItem",
        "dynamodb:DeleteItem",
        "dynamodb:Query"
      ],
      "Resource": "*"
    }
  ]
}
```

## 3) Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Update `.env` with your actual values:
- `CONNECT_INSTANCE_ID`
- `CONNECT_CONTACT_FLOW_ID` (for outbound demo contact)
- `OUTBOUND_SOURCE_PHONE_NUMBER`
- `OUTBOUND_DESTINATION_PHONE_NUMBER`

## 4) Run API

```bash
uvicorn app.main:app --reload --port 8000
```

Swagger docs:
- [http://localhost:8000/docs](http://localhost:8000/docs)

## 5) API Endpoints

- `GET /health`
  - service health check

- `POST /demo/seed`
  - creates 2 demo queues (`demo-queue-1`, `demo-queue-2`) only if not already present
  - starts 1 outbound demo contact
  - stores demo contact id in DynamoDB for later sync

- `POST /sync/connect-data`
  - fetches all Connect queues
  - fetches contact details for stored demo contacts
  - persists queues and contacts in DynamoDB table

- `GET /connect/queues?limit=20&offset=0&name_contains=demo`
  - paginated queue list from Amazon Connect
  - optional name filter (`name_contains`)

- `GET /connect/contacts?limit=20&offset=0&channel=VOICE`
  - paginated contact details from Connect (based on saved demo contact ids)
  - optional channel filter
  - optional date range filters using ISO-8601:
    - `from_date=2026-03-01T00:00:00Z`
    - `to_date=2026-03-31T23:59:59Z`

- `DELETE /demo/cleanup`
  - deletes demo queues that match `demo-queue-*` naming
  - removes demo contact marker records from DynamoDB
  - returns queue delete failures if a queue cannot be deleted

- `GET /data/queues?limit=20&start_sk=<last_sk>`
  - reads saved queue records from DynamoDB with cursor-based pagination

- `GET /data/contacts?limit=20&start_sk=<last_sk>`
  - reads saved contact records from DynamoDB with cursor-based pagination

## Notes

- The app intentionally uses IAM auth only (no hardcoded AWS keys).
- Contact retrieval in Connect can vary by channel and lifecycle; this demo stores created contact IDs and syncs their details.
- Queue demo creation is idempotent: existing queue names are reused rather than duplicated.
- Contact date filtering uses `initiated_timestamp` from `DescribeContact`.
- Application startup uses FastAPI lifespan handlers (modern replacement for deprecated startup events).

## 6) Run tests

```bash
pytest -q
```
