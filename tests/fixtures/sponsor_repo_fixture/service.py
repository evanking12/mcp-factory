def repo_echo_sentinel(sentinel: str) -> str:
    """Return a deterministic repo-ingestion proof string."""
    return f"MCP_FACTORY_REPO_FIXTURE:{sentinel}"


def repo_lookup_customer(customer_id: str) -> str:
    """Return a deterministic Contoso customer lookup result."""
    return f"customer:{customer_id}:active"
