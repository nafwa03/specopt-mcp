# Dataset Validation Report

## Summary
* **Dataset:** `simple_prompt_generated_dataset.json`
* **Agent File:** `simple_prompt.md`
* **Total Examples:** 2
* **Avg Hardness:** 0.0/5.0
* **Overall Verdict:** **FAIL**

## Results

### 1. Alignment Check
* **Status:** FAIL
* **Score:** 0.0% (threshold: ≥80%)
* **Detail:** 0/2 examples passed LLM judge

### 2. Semantic Diversity
* **Status:** FAIL
* **Score:** N/A (threshold: <0.75)
* **Detail:** SKIPPED — sentence-transformers not installed or computation failed

### 3. Baseline Failure Test
* **Status:** FAIL
* **Score:** 100.0% (threshold: 40%-70%)
* **Detail:** Unoptimized agent accuracy on dataset

### 4. Negative Class Ratio
* **Status:** FAIL
* **Score:** 0.0% (threshold: ≥15%)
* **Detail:** 0/2 adversarial cases detected
