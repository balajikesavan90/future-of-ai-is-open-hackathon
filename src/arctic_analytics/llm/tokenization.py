"""Tokenization helpers that tolerate offline environments."""

import tiktoken


class FallbackEncoding:
    def encode(self, text):
        return str(text).split()


def safe_encoding_for_model(model):
    try:
        return tiktoken.encoding_for_model(model)
    except Exception:
        return FallbackEncoding()

