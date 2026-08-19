import tiktoken
from typing import Tuple, Dict

# ============================================================
# INITIALIZE TIKTOKEN ENCODER
# ============================================================

# Use cl100k_base encoding (used by gpt-3.5-turbo, gpt-4, etc.)
ENCODING = tiktoken.get_encoding("cl100k_base")

# Cost per 1K tokens (published rates as of Aug 2026)
# For local Ollama: $0 (no API cost)
# For Claude API: adjust as needed
COST_PER_1K_INPUT = 0.003   # $0.003 per 1K input tokens
COST_PER_1K_OUTPUT = 0.01   # $0.01 per 1K output tokens

# ============================================================
# TOKEN COUNTING
# ============================================================

def count_tokens(text: str) -> int:
    """
    Count the number of tokens in a text string.
    
    Args:
        text: Input text to tokenize
    
    Returns:
        Number of tokens
    
    Example:
        >>> count_tokens("What's the Gold PPO premium?")
        8
    """
    if not text:
        return 0
    
    tokens = ENCODING.encode(text)
    return len(tokens)


def estimate_cost(input_tokens: int, output_tokens: int) -> float:
    """
    Estimate API cost based on token counts.
    
    Args:
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
    
    Returns:
        Estimated cost in USD
    
    Example:
        >>> estimate_cost(100, 50)
        0.0005  # $0.0005
    """
    input_cost = (input_tokens / 1000) * COST_PER_1K_INPUT
    output_cost = (output_tokens / 1000) * COST_PER_1K_OUTPUT
    return input_cost + output_cost


def analyze_tokens(prompt: str, completion: str) -> Dict[str, int | float]:
    """
    Analyze tokens in a prompt + completion pair.
    
    Args:
        prompt: The input prompt
        completion: The LLM's response
    
    Returns:
        Dict with token counts and estimated cost
    """
    prompt_tokens = count_tokens(prompt)
    completion_tokens = count_tokens(completion)
    total_tokens = prompt_tokens + completion_tokens
    cost = estimate_cost(prompt_tokens, completion_tokens)
    
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "estimated_cost_usd": round(cost, 6),
    }


# ============================================================
# UNIT TESTS
# ============================================================

def test_token_counting():
    """Test token counting accuracy."""
    
    # Test 1: Simple question
    q1 = "What's the Gold PPO premium?"
    tokens_1 = count_tokens(q1)
    assert tokens_1 > 0, "Should count tokens"
    print(f"✅ Test 1: '{q1}' = {tokens_1} tokens")
    
    # Test 2: Longer text
    q2 = "Can you provide details about the Silver HMO plan including deductible, copay percentage, and any exclusions?"
    tokens_2 = count_tokens(q2)
    assert tokens_2 > tokens_1, "Longer text should have more tokens"
    print(f"✅ Test 2: Longer question = {tokens_2} tokens")
    
    # Test 3: Cost estimation
    cost = estimate_cost(100, 50)
    expected_cost = (100/1000) * COST_PER_1K_INPUT + (50/1000) * COST_PER_1K_OUTPUT
    assert abs(cost - expected_cost) < 0.0001, "Cost calculation should be accurate"
    print(f"✅ Test 3: Cost estimation = ${cost:.6f}")
    
    # Test 4: Full analysis
    prompt = "What procedures are covered?"
    completion = "Most procedures are covered under our plans. Please consult your plan documents for specifics."
    analysis = analyze_tokens(prompt, completion)
    
    assert analysis["prompt_tokens"] > 0
    assert analysis["completion_tokens"] > 0
    assert analysis["total_tokens"] == analysis["prompt_tokens"] + analysis["completion_tokens"]
    assert analysis["estimated_cost_usd"] >= 0
    print(f"✅ Test 4: Full analysis = {analysis}")
    
    print("\n✅ All token counting tests passed!")


if __name__ == "__main__":
    test_token_counting()
    
    # Example: Analyze a real prompt-completion pair
    print("\n" + "="*80)
    print("EXAMPLE: Token Analysis")
    print("="*80)
    
    example_prompt = "Is physical therapy covered under the Silver HMO plan?"
    example_completion = "Physical therapy is covered under the Silver HMO plan. The plan includes physical therapy with a $25 copay per visit and requires prior authorization. Please check your plan documents for session limits and any exclusions."
    
    analysis = analyze_tokens(example_prompt, example_completion)
    
    print(f"\nPrompt: {example_prompt}")
    print(f"Completion: {example_completion}")
    print(f"\nAnalysis:")
    for key, value in analysis.items():
        print(f"  {key}: {value}")