import json
import numpy as np
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA

# Load knowledge base (for section labels) and embeddings (must be same order)
records = []
with open("knowledge_base.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        records.append(json.loads(line))

embeddings = np.load("embeddings.npy")

assert len(records) == embeddings.shape[0], "Mismatch between chunks and embeddings!"

# Reduce to 2D
pca = PCA(n_components=2)
coords_2d = pca.fit_transform(embeddings)

# Color-code by section
sections = [r["section"] for r in records]
unique_sections = sorted(set(sections))
colors = plt.cm.tab10.colors  # up to 10 distinct colors

plt.figure(figsize=(10, 8))
for i, section in enumerate(unique_sections):
    idx = [j for j, s in enumerate(sections) if s == section]
    plt.scatter(
        coords_2d[idx, 0],
        coords_2d[idx, 1],
        label=section,
        color=colors[i % len(colors)],
        s=100,
        alpha=0.8
    )

plt.title("Knowledge Base Chunks — 2D PCA Projection by Section")
plt.xlabel("PCA Component 1")
plt.ylabel("PCA Component 2")
plt.legend()
plt.tight_layout()
plt.savefig("embeddings_2d.png", dpi=150)
print("Saved embeddings_2d.png")
plt.show()