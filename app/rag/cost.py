PRICING = {
    # Groq models
    "llama-3.1-8b-instant"              : {"prompt": 0.000059, "completion": 0.000079},
    "llama-3.1-70b-versatile"           : {"prompt": 0.000590, "completion": 0.000790},
    "llama-3.3-70b-versatile"           : {"prompt": 0.000590, "completion": 0.000790},
    "mixtral-8x7b-32768"                : {"prompt": 0.000270, "completion": 0.000270},
    "meta-llama/llama-4-scout-17b-16e-instruct": {"prompt": 0.000110, "completion": 0.000340},
    "gemma2-9b-it"                      : {"prompt": 0.000200, "completion": 0.000200},

    # OpenAI models
    "gpt-4o-mini"                       : {"prompt": 0.000150, "completion": 0.000600},
    "gpt-4o"                            : {"prompt": 0.002500, "completion": 0.010000},

    # Ollama — free
    "llama3.2"                          : {"prompt": 0.0, "completion": 0.0},
    "llama3.1"                          : {"prompt": 0.0, "completion": 0.0},
    "mistral"                           : {"prompt": 0.0, "completion": 0.0},
}


def calculate_cost(
    model            : str,
    prompt_tokens    : int,
    completion_tokens: int,
) -> float:
    prices = PRICING.get(model, {"prompt": 0.0, "completion": 0.0})
    cost   = (
        (prompt_tokens     / 1000) * prices["prompt"] +
        (completion_tokens / 1000) * prices["completion"]
    )
    return round(cost, 8)


def format_cost(cost_usd: float) -> str:
    if cost_usd == 0.0:
        return "free"
    elif cost_usd < 0.001:
        return f"${cost_usd:.6f}"
    else:
        return f"${cost_usd:.4f}"