---
name: Dataset Validation Metrics
description: A comprehensive specification for evaluating synthetic datasets used to test LLM agents.
license: Complete terms in LICENSE.txt
---

## Overview

To validate that your synthetic dataset is high quality, diverse, and rigorous enough to test your agents, you cannot rely on human intuition alone.  
You need to score the dataset itself **before** using it to score your models.

An evaluation dataset is *good* if it displays:

- **High diversity** (semantic variety)  
- **Relevance** (faithfulness to your documentation)  
- **Hardness** (calibrated difficulty)

Below are the specific metrics and programmatic techniques you can use to validate your dataset.

---

## 1. Hardness & Alignment Metric (LLM‑as‑a‑Judge)

Use a powerful critic model to score each generated test case. A valid test case must be solvable **using only** the data in your `AGENTS.md` file, and its labeled *expected tool* must be completely accurate.

```python
class EvaluateTestCase(dspy.Signature):
    """Critique a synthetically generated test case for an agent simulation."""
    agents_documentation = dspy.InputField(
        desc="The markdown content of AGENTS.md"
    )
    user_query = dspy.InputField(desc="The generated user request")
    expected_tool = dspy.InputField(
        desc="The labeled tool the agent is supposed to use"
    )

    is_solvable = dspy.OutputField(
        desc="Yes/No. Can an agent realistically answer this based ONLY on the documentation?"
    )
    is_label_correct = dspy.OutputField(
        desc="Yes/No. Is the 'expected_tool' absolutely the correct tool for this user query?"
    )
    hardness_score = dspy.OutputField(
        desc="1 to 5. 1=trivial/childish, 3=realistic, 5=highly complex edge case with multiple constraints."
    )

def validate_dataset_sample(agents_md, example_row):
    judge = dspy.Predict(EvaluateTestCase)
    result = judge(
        agents_documentation=agents_md,
        user_query=example_row.user_query,
        expected_tool=example_row.expected_tool
    )
    
    # Fail the sample if it's unsolvable or mislabeled
    if result.is_solvable.lower() != "yes" or result.is_label_correct.lower() != "yes":
        return 0.0
    
    # Scale score based on hardness (we want challenging test cases, not just easy ones)
    return float(result.hardness_score) / 5.0
```

---

## 2. Semantic Diversity / Embedding Distance

If your synthetic generator spits out many semantically similar questions, the optimizer will overfit.

- **How to score it:** Generate vector embeddings for all `user_query` rows and compute the cosine similarity matrix.
- **Target Score:** Average pairwise cosine similarity should be **under 0.75**. Above 0.85 indicates excessive repetition.

---

## 3. Baseline Model Failure Test (Empirical Hardness)

A practical metric is how well a standard, unoptimized local model performs on the dataset.

- **Metric:** Baseline Agent Accuracy  
- **Target Score:** Between **40 % and 70 %** for an out‑of‑the‑box 8B parameter model.  
- **Why it matters:** This range leaves ample room for optimization while ensuring the test suite is challenging enough to expose weaknesses.

---

## 4. Negative Class Ratio (Structural Balance)

Ensure the dataset contains out‑of‑scope or adversarial queries that force the agent to refuse.

- **Metric:** Ratio of standard tool execution cases to out‑of‑scope/adversarial cases.
- **Target Score:** **15 %–20 %** of queries should be labeled `None`, `Out_Of_Scope`, or `Reject`.

---

## Summary Checklist for a Production‑Ready Dataset

| Criterion | Desired Value |
|-----------|---------------|
| **Accuracy** | 100 % samples pass the LLM‑Judge alignment check (valid tools, solvable context). |
| **Diversity** | Mean embedding similarity < 0.75. |
| **Calibration** | Baseline local model accuracy between 40 % and 70 %. |
| **Composition** | ≥ 15 % adversarial/out‑of‑scope cases. |

---

## Quick Diversity Test

If you have an embedding provider (e.g., Ollama's `nomic-embed-text` or another API), use the following snippet to compute your dataset’s exact diversity score:

```python
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
embeddings = model.encode(user_queries)          # `user_queries` is a list of strings
cos_sim_matrix = cosine_similarity(embeddings)

# Exclude the diagonal (self‑similarity)
mask = ~np.eye(cos_sim_matrix.shape[0], dtype=bool)
avg_cosine_similarity = cos_sim_matrix[mask].mean()

print(f'Average pairwise cosine similarity: {avg_cosine_similarity:.3f}')
```

---

### References

1. https://stats.stackexchange.com/questions/152907/how-do-you-use-the-test-dataset-after-cross-validation  
2. https://palantir.com/docs/foundry/evaluate-models/model-evaluation-automatic/  
3. https://www.meegle.com/en_us/topics/ai-model-evaluation/ai-model-evaluation-in-computer-vision  
4. https://www.n-ix.com/rag-evaluation/  
5. https://pub.towardsai.net/llm-eval-workflow-how-to-build-reliable-ai-quality-gates-without-vibes-16da6c4be942  
6. https://dev.to/kuldeep_paul/top-10-metrics-to-monitor-for-reliable-ai-agent-performance-4b36  
7. https://medium.com/@odhitom09/the-most-effective-rag-approach-to-date-anthropics-contextual-retrieval-and-hybrid-search-8dc2af5cb970  
8. https://botscrew.com/blog/key-ai-metrics-for-smarter-llm-evaluation/  
9. https://apxml.com/courses/building-advanced-llm-agent-tools/chapter-6-llm-tool-testing-monitoring-maintenance/evaluating-tool-effectiveness  
10. https://www.evidentlyai.com/llm-guide/rag-evaluation  
11. https://developers.google.com/machine-learning/crash-course/overfitting/dividing-datasets

---