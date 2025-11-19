---
title: "Realtime Jobs API"
description: "Reference slice of the `/api/jobs` contract."
source_url: "https://example.com/api/realtime-jobs"
sample_type: "live_fixture"
apiVersion: "v2"
authentication: "Bearer token issued by IAM"
---

## Endpoint
`POST /api/jobs`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `workflow` | string | yes | Name of the workflow definition stored in `workflow_compiler`. |
| `input_params` | object | yes | Arbitrary key/value payload forwarded to agents. |
| `checkpoint_mode` | enum(checkpoint,stateless) | no | Overrides default checkpoint behavior. |

## Response
```json
{
  "job_id": "3ec55be6419c",
  "status": "pending",
  "links": {
    "self": "/api/jobs/3ec55be6419c",
    "events": "/api/jobs/3ec55be6419c/events"
  }
}
```

## Error Handling
Errors propagate as RFC7807 documents; the `trace_id` matches entries in `samples/logs/job_success_log.md` when replaying fixtures.
