"""List prices of the models the project may use, in USD per million tokens (NFR-06, ADR 0007).

From the provider's pricing page on 20 November 2026 (standard tier, short context). A model not
listed here has no known price; its calls are logged without a cost and count as over budget.
"""

PRICES: dict[str, tuple[float, float]] = {
    # model: (input, output)
    "gpt-5.4": (2.50, 15.00),
    "gpt-5.4-mini": (0.75, 4.50),
    "gpt-5.4-nano": (0.20, 1.25),
    "gpt-5-mini": (0.25, 2.00),
    "gpt-4.1": (2.00, 8.00),
    "gpt-4.1-mini": (0.40, 1.60),
}


def cost_usd(model: str, input_tokens: int, output_tokens: int) -> float | None:
    """The list price of one call, or None for a model without a known price."""
    # Dated snapshots such as "gpt-5.4-mini-2026-03-05" are priced like their model.
    base = next(
        (name for name in sorted(PRICES, key=len, reverse=True) if model.startswith(name)), None
    )
    if base is None:
        return None
    price_in, price_out = PRICES[base]
    return (input_tokens * price_in + output_tokens * price_out) / 1_000_000
