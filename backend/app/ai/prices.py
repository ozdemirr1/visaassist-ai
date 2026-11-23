"""List prices of the models the project may use, in USD per million tokens (NFR-06, ADR 0007).

Standard tier, short context, from https://developers.openai.com/api/docs/pricing on
23 November 2026. A model not listed here has no known price, and the API does not call it; other
tiers (batch, flex, fast, ultrafast) and long context are priced differently and are not used.
"""

import re

PRICES: dict[str, tuple[float, float]] = {
    # model: (input, output)
    "gpt-6.2-sol": (2.00, 10.00),  # measurement and presentation
    "gpt-6.1-terra": (1.00, 5.00),  # development (default)
    "gpt-6-luna": (0.10, 0.50),
    "gpt-5.4": (2.50, 15.00),
    "gpt-5.4-mini": (0.75, 4.50),
}

# A dated snapshot such as "gpt-6.1-terra-2026-10-01" is priced like its model; any other suffix
# (for example "-ultrafast") is a different model with a different price.
_DATED = re.compile(r"^(?P<model>.+)-\d{4}-\d{2}-\d{2}$")


def cost_usd(model: str, input_tokens: int, output_tokens: int) -> float | None:
    """The list price of one call, or None for a model without a known price."""
    dated = _DATED.match(model)
    base = dated.group("model") if dated and model not in PRICES else model
    if base not in PRICES:
        return None
    price_in, price_out = PRICES[base]
    return (input_tokens * price_in + output_tokens * price_out) / 1_000_000
