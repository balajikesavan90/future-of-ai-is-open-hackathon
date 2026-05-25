# Removed Features

This file records implementation remnants removed from active source during second-pass credibility cleanup.

Removal date: 2026-05-25

| Feature | Reason removed | Replacement |
| --- | --- | --- |
| Inactive OpenAI image-generation response handling in `src/arctic_analytics/llm/openai_responses.py` | Image generation is not part of the active structured-data analysis workflow. Keeping commented response handling, image params, and file-save references made the implementation contradict archive notes. | Active `generate_plot` tool remains for matplotlib chart generation from structured data. |
| Stale image-generation parameters in `responses_APIcall()` | `allow_image_generation` and `image_params` were not used by the active workflow. | None. |
| Commented web-search and MCP response branches in `src/arctic_analytics/llm/openai_responses.py` | These were not active integrations and created ambiguity about supported tool types. | None. Future integrations should be added with docs, tests, and explicit scope. |
| Embedding helper code in `src/arctic_analytics/llm/openai_responses.py` | Embeddings are not part of the current metadata-aware Tool-Calling Analysis path, and no active retrieval workflow calls the helper. | None. Future retrieval/context work should live in a documented module with tests. |
| Unused imports for removed experiments | Imports for unused pydantic tooling, typing aliases, `uuid`, direct `tiktoken`, and retry helpers increased the appearance of inactive feature surface. | Active imports only. Tokenization remains through `src/arctic_analytics/llm/tokenization.py`. |
| Direct `pydantic` project dependency | No project code imports pydantic after stale tool scaffolding removal. Transitive dependencies can still bring it in if needed by installed libraries. | None. |
