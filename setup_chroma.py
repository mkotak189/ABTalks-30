import chromadb

# Persistent client - saves data to disk in a folder called chroma_data
client = chromadb.PersistentClient(path="chroma_data")

# Create the collection (or get it if it already exists)
collection = client.get_or_create_collection(name="coverage_kb")

print(f"Collection created: {collection.name}")
print(f"Current item count: {collection.count()}")

# Confirm it exists by listing all collections
all_collections = client.list_collections()
print(f"\nAll collections in this client: {[c.name for c in all_collections]}")