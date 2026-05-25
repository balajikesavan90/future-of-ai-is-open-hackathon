# Identity Audit

This audit covers repository wording related to Arctic Analytics positioning as an experimental open-source framework for metadata-aware, inspectable, constrained AI-assisted analysis over structured data.

| Term | Current wording | Recommended wording | Reason | Severity |
| --- | --- | --- | --- | --- |
| sandbox / sandboxed | "Run a python function in a sandboxed environment" in `src/arctic_analytics/llm/openai_responses.py` | "Run a python function with application-level execution restrictions." | Avoids implying security isolation. | High |
| sandbox / sandboxed | README and security docs distinguish Python restrictions from OS/container sandboxing. | Keep or rewrite to "security isolation" where clearer. | Limitation language is appropriate, but repeated "sandbox" can blur claims. | Medium |
| assistant | OpenAI message roles and tests use `assistant`. | Keep for API semantics. | Required OpenAI message role terminology. | Low |
| assistant | Design docs referred to opaque assistant behavior. | "Opaque model behavior." | Narrows the project away from generic AI assistant framing. | Medium |
| copilot | Design docs say the project is not a copilot. | Keep as non-goal wording. | Explicitly distances project from broad copilot positioning. | Low |
| AI assistant | No active positive claims found. | Keep avoiding. | Aligns with constrained analysis framework positioning. | Low |
| chat with data | Legacy archive note lists broad chat-with-data framing as out of scope. | Archive. | Historical positioning context only. | Medium |
| autonomous | Design and security docs warn against autonomous-decision framing. | Keep as limitation wording. | Supports human-review positioning. | Low |
| enterprise | README, design docs, and research docs say the project is not enterprise governance. | Keep as non-goal wording. | Correctly narrows scope. | Low |
| governance | README and docs say there is no governance or role-based governance. | Keep as non-goal wording. | Avoids production governance claims. | Low |
| AIR Insights | No active references found before cleanup. | Add only as explicit non-goal in README. | Distances the OSS project from internal proprietary systems. | Medium |
| hackathon | No tracked content references found. | Keep absent. | Avoids temporary event framing. | Low |
| production-ready | No tracked content references found. | Keep absent; use "experimental" and "prototype" where needed. | Avoids maturity overclaims. | Low |

## Applied Rewrites

- Replaced sandboxed execution docstrings with application-level execution restrictions.
- Reframed the README identity statement around experimental, inspectable, constrained analysis.
- Added explicit non-goals for generic assistant, chat-with-data, governance platform, enterprise product, sandboxed execution environment, and AIR Insights.
- Rewrote design wording from assistant behavior to model behavior where it was not an API role.
- Archived legacy migration positioning notes under `docs/archive/`.
