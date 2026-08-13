import os
import json
from dotenv import load_dotenv
import boto3

load_dotenv()

client = boto3.client("bedrock-runtime", region_name="us-east-1")
MODEL = "us.anthropic.claude-haiku-4-5-20251001-v1:0"

# Load test examples
test_examples = []
with open("fine_tune_test.jsonl", "r") as f:
    for line in f:
        test_examples.append(json.loads(line))

results = []

for i, example in enumerate(test_examples, 1):
    messages = example["messages"]
    user_question = messages[-2]["content"]  # Second to last is user
    ground_truth = messages[-1]["content"]   # Last is assistant
    
    # Get response from model
    response = client.converse(
        modelId=MODEL,
        messages=[{"role": "user", "content": [{"text": user_question}]}],
        system=[{"text": messages[0]["content"]}],  # Keep as-is (this one is correct)
    )
    
    model_answer = response["output"]["message"]["content"][0]["text"]
    
    results.append({
        "question_num": i,
        "question": user_question,
        "ground_truth": ground_truth,
        "model_answer": model_answer,
    })
    
    print(f"Q{i}: {user_question}\n")
    print(f"  Expected: {ground_truth}\n")
    print(f"  Got: {model_answer}\n")
    print("-" * 70 + "\n")

# Save results
with open("evaluation_results.json", "w") as f:
    json.dump(results, f, indent=2)

print("Evaluation complete. Fill in fine_tune_comparison.md manually.")