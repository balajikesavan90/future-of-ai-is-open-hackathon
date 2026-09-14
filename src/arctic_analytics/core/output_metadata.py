"""Shared metadata contract for user-visible tool output."""

DISPLAY_OUTPUT_FIELDS = frozenset({
    "display_output",
    "display_output_truncated",
    "display_output_length_chars",
    "display_output_ref",
    "display_output_agent_limited",
    "display_output_not_retained",
})
