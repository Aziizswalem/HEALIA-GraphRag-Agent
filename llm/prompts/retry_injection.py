"""Formats validation-error context for Cypher retry turns."""


def format_validation_retry_block(validation_error: str | None) -> str:
    if not validation_error:
        return ""
    return f"""
WARNING — Your previous query failed with this Neo4j error:
{validation_error}

Analyze the error carefully and generate a corrected query. Do not repeat the same mistake.
"""
