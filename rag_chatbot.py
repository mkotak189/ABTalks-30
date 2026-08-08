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

    prompt = f"""Answer using ONLY the context below. Respond in a complete, natural sentence.
If the answer isn't in the context, say you don't know and suggest the member contact support.
This is not medical advice.

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