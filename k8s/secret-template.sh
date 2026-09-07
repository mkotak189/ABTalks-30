#!/bin/bash
# ============================================================
# Secret Creation Script (DO NOT COMMIT THIS WITH REAL VALUES!)
# ============================================================
# This script creates a Kubernetes Secret from environment variables.
# Run this locally; do NOT commit the output or real secret values.

set -e

# Load environment variables from .env (local only, not in repo)
if [ -f .env ]; then
    export $(cat .env | grep -v '#' | xargs)
fi

# Create the secret in Minikube
echo "Creating Kubernetes Secret: chatbot-secrets"
kubectl create secret generic chatbot-secrets \
  --from-literal=OLLAMA_MODEL=llama3.1 \
  --from-literal=AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID:-placeholder} \
  --from-literal=AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY:-placeholder} \
  --from-literal=AWS_REGION=${AWS_REGION:-us-east-1} \
  --from-literal=ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:-placeholder} \
  --dry-run=client -o yaml | kubectl apply -f -

echo "✅ Secret 'chatbot-secrets' created/updated"
echo "ℹ️  Secret values are NOT stored in Git; they live in Minikube's etcd"