import os
import openai
from dotenv import load_dotenv
from retrieval_engine import retrieve

load_dotenv()

client = openai.OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama",
)

MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")


def generate_answer(question: str, context: list[str], stream: bool = False):
    context_block = "\n".join(f"- {c}" for c in context) if context else "(no context retrieved)"

    prompt = f"""You are a compassionate health insurance coverage assistant committed to accuracy and clarity.

Your responsibilities:
1. Answer ONLY using information from the provided context
2. Be warm and understanding—members often have stressful questions about medical costs
3. Be precise about coverage—do not speculate or infer what isn't explicitly stated
4. Refuse medical advice—redirect diagnosis or treatment questions to a licensed healthcare provider
5. Admit information gaps—if you don't have the answer, say so clearly and suggest contacting support

Before answering, briefly identify: (a) which plan is being asked about, (b) what section (coverage/claims/exclusions/enrollment) is relevant.

Important disclaimer: This is not medical advice. Coverage details may vary by your specific plan, rider, or enrollment date. For complex questions or exceptions, please contact support.

Context: {context_block}

Question: {question}"""

    messages = [{"role": "user", "content": prompt}]

    if stream:
        full_text = ""
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            stream=True,
        )
        for chunk in response:
            delta = chunk.choices[0].delta.content
            if delta:
                print(delta, end="", flush=True)
                full_text += delta
        print()
        return full_text
    else:
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            stream=False,
        )
        return response.choices[0].message.content


def retrieve_and_answer(question: str, stream: bool = False) -> dict:
    retrieval_result = retrieve(question)
    context = retrieval_result["merged_context"]
    answer = generate_answer(question, context, stream=stream)

    return {
        "question": question,
        "classification": retrieval_result["classification"],
        "context": context,
        "answer": answer,
    }


if __name__ == "__main__":
    # Step 7: streaming smoke test
    print("=== STREAMING SMOKE TEST ===\n")
    result = retrieve_and_answer(
        "What's the deductible on the Gold PPO plan?",
        stream=True
    )
    print(f"\nClassification: {result['classification']}")