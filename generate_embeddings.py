import json
import numpy as np
from sentence_transformers import SentenceTransformer

print("Loading model (first run downloads it, may take a minute)...")
model = SentenceTransformer("all-MiniLM-L6-v2")

def embed(text):
    return model.encode(text)

# Load knowledge base
records = []
with open("knowledge_base.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        records.append(json.loads(line))

print(f"Loaded {len(records)} chunks. Generating embeddings...")

texts = [r["text"] for r in records]
embeddings = model.encode(texts, show_progress_bar=True)

# Save as .npy - one row per chunk, same order as knowledge_base.jsonl
np.save("embeddings.npy", embeddings)

print(f"\nSaved embeddings.npy with shape {embeddings.shape}")
print(f"(That's {embeddings.shape[0]} chunks x {embeddings.shape[1]} dimensions)")