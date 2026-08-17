import re
from typing import Dict, Tuple

# ============================================================
# PII/PHI REDACTION PATTERNS
# ============================================================

REDACTION_PATTERNS = {
    "member_id": (r"M\d{3,}", "[MEMBER_ID]"),
    "claim_id": (r"C\d{3,}", "[CLAIM_ID]"),
    "amount": (r"\$[\d,]+\.?\d*", "[AMOUNT]"),
    "ssn": (r"\d{3}-\d{2}-\d{4}", "[SSN]"),
    "phone": (r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", "[PHONE]"),
    "email": (r"[\w\.-]+@[\w\.-]+\.\w+", "[EMAIL]"),
    "name": (r"\b[A-Z][a-z]+ [A-Z][a-z]+\b", "[NAME]"),
}

# ============================================================
# REDACTION FUNCTION
# ============================================================

def redact_pii(text: str, patterns: Dict[str, Tuple[str, str]] = None) -> Tuple[str, Dict[str, int]]:
    """
    Redact PII/PHI from text.
    
    Args:
        text: Input text that may contain PII/PHI
        patterns: Dict of {pattern_name: (regex, replacement)}. Defaults to REDACTION_PATTERNS.
    
    Returns:
        Tuple of (redacted_text, redaction_count_dict)
    
    Example:
        >>> text = "Member M001 filed claim C1001 for $500"
        >>> redacted, counts = redact_pii(text)
        >>> print(redacted)
        "Member [MEMBER_ID] filed claim [CLAIM_ID] for [AMOUNT]"
        >>> print(counts)
        {'member_id': 1, 'claim_id': 1, 'amount': 1}
    """
    if patterns is None:
        patterns = REDACTION_PATTERNS
    
    redacted_text = text
    redaction_counts = {}
    
    for pattern_name, (regex, replacement) in patterns.items():
        # Find all matches
        matches = re.findall(regex, redacted_text)
        count = len(matches)
        
        if count > 0:
            # Replace all matches
            redacted_text = re.sub(regex, replacement, redacted_text)
            redaction_counts[pattern_name] = count
    
    return redacted_text, redaction_counts


# ============================================================
# UNIT TESTS
# ============================================================

def test_redact_pii():
    """Unit tests for redact_pii function."""
    
    # Test 1: Member ID + Claim ID + Amount
    test_1 = "Member M001 filed claim C1001 for $500 on 2026-08-15"
    redacted_1, counts_1 = redact_pii(test_1)
    
    assert "[MEMBER_ID]" in redacted_1
    assert "[CLAIM_ID]" in redacted_1
    assert "[AMOUNT]" in redacted_1
    assert counts_1["member_id"] == 1
    assert counts_1["claim_id"] == 1
    assert counts_1["amount"] == 1
    print("✅ Test 1 passed: Basic member/claim/amount redaction")
    
    # Test 2: Multiple occurrences
    test_2 = "Member M001 and M002 both filed claims: C1001 for $1000, C1002 for $2000"
    redacted_2, counts_2 = redact_pii(test_2)
    
    assert counts_2["member_id"] == 2
    assert counts_2["claim_id"] == 2
    assert counts_2["amount"] == 2
    print("✅ Test 2 passed: Multiple PII redactions")
    
    # Test 3: Email + Phone + SSN
    test_3 = "Contact john.doe@example.com at (555) 123-4567 or SSN 123-45-6789"
    redacted_3, counts_3 = redact_pii(test_3)
    
    assert "[EMAIL]" in redacted_3
    assert "[PHONE]" in redacted_3
    assert "[SSN]" in redacted_3
    assert counts_3["email"] == 1
    assert counts_3["phone"] == 1
    assert counts_3["ssn"] == 1
    print("✅ Test 3 passed: Contact info redaction")
    
    # Test 4: No PII
    test_4 = "This question is about plan benefits in general"
    redacted_4, counts_4 = redact_pii(test_4)
    
    assert redacted_4 == test_4  # No changes
    assert len(counts_4) == 0  # No redactions
    print("✅ Test 4 passed: No false positives on clean text")
    
    print("\n✅ All redaction tests passed!")


if __name__ == "__main__":
    # Run unit tests
    test_redact_pii()
    
    # Example usage
    print("\n" + "="*80)
    print("REDACTION EXAMPLE")
    print("="*80)
    
    example = "Member M001 (John Smith) filed claim C1001 for $500 (SSN: 123-45-6789). Contact: john@example.com or (555) 123-4567"
    redacted, counts = redact_pii(example)
    
    print(f"Original:\n{example}\n")
    print(f"Redacted:\n{redacted}\n")
    print(f"Redaction counts: {counts}")