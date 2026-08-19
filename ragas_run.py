import json
import os
import sys
from typing import Dict, List

# Add repo root to path
sys.path.insert(0, os.path.abspath("."))

from rag_chatbot import retrieve_and_answer
from retrieval_engine import retrieve
import openai

# For RAGAS evaluation
from datasets import Dataset
from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
from ragas import evaluate

# ============================================================
# LOAD EVAL SET
# ============================================================

def load_eval_set(filepath: str = "ragas_eval_set.jsonl") -> List[Dict]:
    """Load question/ground_truth pairs from JSONL."""
    pairs = []
    with open(filepath, "r") as f:
        for line in f:
            pairs.append(json.loads(line))
    return pairs

# ============================================================
# RUN RAG PIPELINE ON EVAL SET
# ============================================================

def run_rag_evaluation(eval_set: List[Dict]) -> List[Dict]:
    """
    Run each question through the RAG pipeline and capture:
    - question
    - retrieved contexts
    - generated answer
    - ground_truth answer
    """
    results = []
    
    for i, pair in enumerate(eval_set, 1):
        question = pair["question"]
        ground_truth = pair["ground_truth"]
        
        print(f"\n[{i}/{len(eval_set)}] Processing: {question}")
        
        try:
            # Step 1: Retrieve context
            retrieval_result = retrieve(question)
            contexts = retrieval_result.get("merged_context", [])
            
            # Step 2: Generate answer
            rag_result = retrieve_and_answer(question, stream=False)
            generated_answer = rag_result.get("answer", "")
            
            results.append({
                "question": question,
                "contexts": contexts,  # List of retrieved context strings
                "answer": generated_answer,
                "ground_truth": ground_truth,
            })
            
            print(f"  ✅ Generated answer ({len(generated_answer)} chars)")
        
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
            results.append({
                "question": question,
                "contexts": [],
                "answer": f"[ERROR: {str(e)}]",
                "ground_truth": ground_truth,
            })
    
    return results

# ============================================================
# FORMAT FOR RAGAS & EVALUATE
# ============================================================

def prepare_ragas_dataset(rag_results: List[Dict]) -> Dataset:
    """
    Convert RAG results to RAGAS-compatible dataset format.
    RAGAS expects: question, contexts, answer, ground_truth
    """
    data = {
        "question": [],
        "contexts": [],
        "answer": [],
        "ground_truth": [],
    }
    
    for result in rag_results:
        data["question"].append(result["question"])
        data["contexts"].append(result["contexts"])  # List of context strings
        data["answer"].append(result["answer"])
        data["ground_truth"].append(result["ground_truth"])
    
    return Dataset.from_dict(data)

def run_ragas_evaluation(dataset: Dataset) -> Dict:
    """
    Run RAGAS metrics on the dataset.
    Returns scores for: faithfulness, answer_relevancy, context_precision, context_recall
    """
    print("\n" + "="*80)
    print("RUNNING RAGAS EVALUATION")
    print("="*80)
    
    # Metrics to evaluate
    metrics = [
        faithfulness,
        answer_relevancy,
        context_precision,
        context_recall,
    ]
    
    # Run evaluation
    results = evaluate(
        dataset=dataset,
        metrics=metrics,
    )
    
    return results

# ============================================================
# MAIN PIPELINE
# ============================================================

def main():
    """Full RAG evaluation pipeline."""
    
    print("="*80)
    print("DAY 27: RAGAS EVALUATION PIPELINE")
    print("="*80)
    
    # Step 1: Load eval set
    print("\nStep 1: Loading evaluation set...")
    eval_set = load_eval_set("ragas_eval_set.jsonl")
    print(f"✅ Loaded {len(eval_set)} question/answer pairs")
    
    # Step 2: Run RAG on each question
    print("\nStep 2: Running RAG pipeline on eval set...")
    rag_results = run_rag_evaluation(eval_set)
    
    # Step 3: Prepare RAGAS dataset
    print("\nStep 3: Preparing RAGAS dataset...")
    ragas_dataset = prepare_ragas_dataset(rag_results)
    print(f"✅ Dataset ready: {len(ragas_dataset)} samples")
    
    # Step 4: Run RAGAS evaluation
    print("\nStep 4: Running RAGAS metrics...")
    ragas_scores = run_ragas_evaluation(ragas_dataset)
    
    # Step 5: Save results
    print("\nStep 5: Saving results...")
    with open("ragas_results.json", "w") as f:
        # Convert scores to JSON-serializable format
        scores_dict = {
            metric: float(ragas_scores[metric]) if hasattr(ragas_scores[metric], '__float__') else ragas_scores[metric]
            for metric in ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
        }
        json.dump(scores_dict, f, indent=2)
    
    print("✅ Results saved to ragas_results.json")
    
    # Step 6: Print summary
    print("\n" + "="*80)
    print("RAGAS SCORES SUMMARY")
    print("="*80)
    print(f"Faithfulness:        {ragas_scores['faithfulness']:.3f}")
    print(f"Answer Relevancy:    {ragas_scores['answer_relevancy']:.3f}")
    print(f"Context Precision:   {ragas_scores['context_precision']:.3f}")
    print(f"Context Recall:      {ragas_scores['context_recall']:.3f}")
    print("="*80)
    
    # Find weakest metric
    scores = {
        "faithfulness": ragas_scores['faithfulness'],
        "answer_relevancy": ragas_scores['answer_relevancy'],
        "context_precision": ragas_scores['context_precision'],
        "context_recall": ragas_scores['context_recall'],
    }
    
    weakest = min(scores, key=scores.get)
    print(f"\n⚠️  WEAKEST METRIC: {weakest} ({scores[weakest]:.3f})")
    
    return {
        "eval_set_size": len(eval_set),
        "rag_results": rag_results,
        "ragas_scores": scores,
        "weakest_metric": weakest,
    }

if __name__ == "__main__":
    results = main()