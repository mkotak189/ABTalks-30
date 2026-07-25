# Vector Database Notes — Chroma vs Pinecone

## Comparison Table

| Criteria | Chroma | Pinecone |
|---|---|---|
| Deployment | Local (runs on your own machine) | Cloud-hosted (managed service) |
| Cost | Fully free, no tier limits for local use | Free tier available (limited storage/reads/writes), paid tiers scale with usage |
| Setup | `pip install chromadb`, a few lines of code, no signup | Account signup, dashboard index creation, API key management |
| Latency | Very low — no network round trip, queries run in-process | Higher — every query is a network call to Pinecone's servers |
| Persistence | Persists to local disk folder | Persists in the cloud, accessible from anywhere with the API key |
| Scalability | Limited by local machine's RAM/disk | Built for large-scale, distributed, production workloads |
| Multi-user access | Not built for concurrent remote access out of the box | Naturally supports multiple app instances/users hitting the same index |
| Embedding generation | Bring your own (e.g. `all-MiniLM-L6-v2` from Day 7) | Can bring your own vectors, or use Pinecone's **Integrated Embedding** (hosted models like `llama-text-embed-v2`) to embed raw text automatically |

## Access Control (Enterprise Consideration)

In a real enterprise deployment — e.g. a per-member or per-plan-restricted healthcare
chatbot — access control looks very different between the two:

**Chroma:** Has no built-in authentication or per-user access control. If different
members should only see their own claims/plan data, that logic must be enforced
entirely in the application layer (e.g. filtering results by `member_id` in Python
before returning them to a user). Since Chroma typically runs locally or on a
single server you control, you're also responsible for securing the server itself
(network access, disk encryption, etc.).

**Pinecone:** Supports metadata filtering at query time (e.g. `filter={"member_id": "M1001"}`)
and namespaces to logically separate tenants/customers within a single index. It
runs behind an API key and TLS by default. Setting up the `coverage-kb` index in
the Pinecone dashboard also surfaced its **Integrated Embedding** option — using
a hosted model like `llama-text-embed-v2` so Pinecone embeds raw text on write,
rather than requiring vectors generated locally. This is convenient, but it means
choosing between Pinecone's hosted embedding model and a self-generated one (like
the `all-MiniLM-L6-v2` model used on Day 7) is itself an access/architecture
decision, since the two aren't interchangeable without re-embedding. Enterprise/paid
tiers offer more formal access-control and compliance features, relevant for
handling PHI/HIPAA-sensitive workloads.

## Decision: Chroma for this program

For this program, I'm using **Chroma** going forward. It's the simplest and fully
free option, requires no signup or API key management, and runs entirely locally —
ideal for a learning environment focused on getting the RAG pipeline working
correctly rather than managing cloud infrastructure or costs. Pinecone remains
useful to know for real enterprise deployments, especially once multi-user access
control, horizontal scale, or hosted embedding become actual requirements — but for
building and iterating on this coverage chatbot, Chroma removes unnecessary
friction while I focus on the core retrieval logic.