# Job sample-success-001 Log

## Timeline
- 16:20:00Z – Job submitted by UnifiedJobExecutor.
- 16:20:05Z – `api_search_node` emitted 2 documents (see `samples/external/api_responses/search_api_sample.json`).
- 16:21:12Z – `section_writer` checkpoint saved to `.checkpoints/tests/sample`.
- 16:22:08Z – `write_file_node` wrote `output/sample-live-csv-export.md` using UTF-8 encoding.

## Events
```json
{
  "timestamp": "2025-11-19T16:21:12Z",
  "agent": "section_writer",
  "level": "INFO",
  "message": "Rendered section 3/3",
  "metadata": {
    "tokens": 1342,
    "llm": "llama3.2"
  }
}
```

## Notes
This log pairs with `samples/manifests/job_success_manifest.json` and acts as a golden reference when asserting end-to-end success.
