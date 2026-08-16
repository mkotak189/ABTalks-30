import os
import json
from dotenv import load_dotenv
import openai
from retrieval_engine import retrieve

load_dotenv()

client = openai.OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama",
)

MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")

# ============================================================
# SYSTEM PROMPT (from Day 12 Variant E)
# ============================================================

SYSTEM_PROMPT = """You are a compassionate health insurance coverage assistant committed to accuracy and clarity.

Your responsibilities:
1. Answer ONLY using information from the provided context
2. Be warm and understanding—members often have stressful questions about medical costs
3. Be precise about coverage—do not speculate or infer what isn't explicitly stated
4. Refuse medical advice—redirect diagnosis or treatment questions to a licensed healthcare provider
5. Admit information gaps—if you don't have the answer, say so clearly and suggest contacting support

Before answering, briefly identify: (a) which plan is being asked about, (b) what section (coverage/claims/exclusions/enrollment) is relevant.

Important disclaimer: This is not medical advice. Coverage details may vary by your specific plan, rider, or enrollment date. For complex questions or exceptions, please contact support.

If the question would benefit from calling a tool (e.g., to check specific claim status, plan details, or coverage), call the appropriate tool. Otherwise, answer based on context alone."""

# ============================================================
# GENERATE ANSWER WITH CITATION TRACKING
# ============================================================

def generate_answer(question: str, context: str, stream: bool = False):
    """
    Generate answer with streaming support and citation tracking.
    """
    # Track chunk IDs used (from context)
    chunk_ids_used = []
    # Extract chunk IDs if they're embedded in context
    # For now, return empty list (can enhance later)
    
    prompt = f"""{SYSTEM_PROMPT}

Context: {context}

Question: {question}"""
    
    if stream:
        # Streaming mode
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            stream=True,
            timeout=120
        )
        
        full_text = ""
        for chunk in response:
            if chunk.choices[0].delta.content:
                full_text += chunk.choices[0].delta.content
                yield chunk.choices[0].delta.content
        
        return {
            "answer": full_text,
            "chunk_ids": chunk_ids_used,
            "classification": "unknown",
        }
    else:
        # Non-streaming mode
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            stream=False,
            timeout=120
        )
        
        answer = response.choices[0].message.content
        return {
            "answer": answer,
            "chunk_ids": chunk_ids_used,
            "classification": "unknown",
        }

# ============================================================
# RETRIEVE AND ANSWER ORCHESTRATION
# ============================================================

def retrieve_and_answer(question: str, stream: bool = False) -> dict:
    """
    Full pipeline: retrieve context → generate answer with citations.
    """
    # Step 1: Get retrieval context
    retrieval_result = retrieve(question)
    context = "\n".join(f"- {c}" for c in retrieval_result["merged_context"]) if retrieval_result["merged_context"] else "(no context)"
    
    # Step 2: Generate answer with streaming support
    if stream:
        # For streaming, we need to return a generator
        result = generate_answer(question, context, stream=True)
        return {
            "question": question,
            "classification": retrieval_result.get("classification", "unknown"),
            "answer_stream": result,  # Generator
        }
    else:
        # Non-streaming
        result = generate_answer(question, context, stream=False)
        return {
            "question": question,
            "classification": result.get("classification", "unknown"),
            "answer": result["answer"],
            "chunk_ids": result["chunk_ids"],
        }

# ============================================================
# TEST HARNESS (optional)
# ============================================================

if __name__ == "__main__":
    test_question = "What's the monthly premium for the Gold PPO plan?"
    result = retrieve_and_answer(test_question, stream=False)
    print(f"Q: {test_question}")
    print(f"A: {result['answer']}")
    print(f"Citations: {result['chunk_ids']}")