+++
title = "LLM Inference Optimization: Stop Paying for Idle Silicon"
date = 2026-05-02T00:00:00+05:30
draft = false
math = false
author = "Krishnatejaswi S"
description = "LLM inference is memory-bandwidth bound, not compute bound. Continuous batching, speculative decoding, quantization, and KV cache management — the techniques that actually move the needle."
tags = ["machine-learning", "llm", "inference", "optimization", "performance"]
+++

GPU bills were doubling every quarter. Throughput wasn't moving. I kept assuming the answer was a bigger GPU. It wasn't.

The problem was naive serving. Standard HuggingFace `pipeline()` processes one request at a time, sequentially. The GPU sits idle between requests, waiting. You're paying for hardware that's doing nothing most of the time.

The fix is a set of four techniques, each with a different ROI profile. Here's what they are, how they work, and when to use each one.

## Quantization

This is the first thing to do because it's a one-time change with immediate impact. AWQ 4-bit quantization cuts VRAM usage by roughly 75%. FP8 cuts it by 50% but requires H100s.

That 75% reduction matters because it changes which GPU class you need. A model that required an A100 might now fit on an A6000. That's not a minor cost reduction -- it's a different tier of hardware entirely.

The tooling is straightforward. Use [AutoAWQ](https://github.com/casper-hansen/AutoAWQ) to quantize yourself, or just pull a pre-quantized checkpoint from HuggingFace. Most popular models have AWQ variants already uploaded.

## Serving Engine

Once you're quantized, the next question is which serving engine to use. The two serious options are vLLM and SGLang, and they're not interchangeable.

**vLLM** is the right choice for chat and general inference. Two mechanisms make the difference:

Continuous batching inserts new requests into the batch as slots open up rather than waiting for a full batch to complete. Naive serving sits at around 20% GPU utilization. vLLM pushes that to 60-85%.

PagedAttention treats VRAM like virtual memory for the KV cache. Instead of pre-allocating contiguous blocks, it pages memory on demand. More sequences can coexist in memory simultaneously, which means more throughput per dollar.

The key vLLM flags worth knowing in production:

```bash
--max-num-seqs 64        # tune for your context length + available VRAM
--disable-log-stats      # remove logging overhead
```

**SGLang** is the right choice for agentic workflows and structured output. Its main advantage is RadixAttention -- it automatically detects shared prompt prefixes and reuses their KV cache. If every request in your system starts with the same 1000-token system prompt and tool definitions, SGLang computes that prefix once and caches it. LMSYS benchmarks show higher throughput than vLLM on structured generation workloads.

The rule of thumb: SGLang for agents and JSON, vLLM for chat.

## Speculative Decoding

This one is less obvious but gets you 2-3x speedup on long-form generation. The mechanism is a draft-then-verify loop:

1. A small draft model (1-7B parameters) generates 3-12 candidate tokens per step
2. The large target model verifies all candidates in a single parallel forward pass
3. When the draft guesses correctly -- which happens 70-90% of the time -- you get multiple tokens for the cost of one forward pass

The canonical pairing is Llama-3-8B-Instruct-AWQ as the draft model against Llama-3-70B-Instruct-AWQ as the target.

A full deployment looks like this:

```python
import runpod
runpod.api_key = "your_api_key"
pod = runpod.create_pod(
    name="llama3-70b-speculative",
    image_name="vllm/vllm-openai:latest",
    gpu_type_id="NVIDIA RTX A6000",
    gpu_count=2,
    docker_args=(
        "--model TechxGenus/Meta-Llama-3-70B-Instruct-AWQ "
        "--quantization awq "
        "--tensor-parallel-size 2 "
        "--speculative-model TechxGenus/Meta-Llama-3-8B-Instruct-AWQ "
        "--num-speculative-tokens 5 "
        "--max-model-len 8192"
    )
)
```

The critical thing to watch: draft model acceptance rate. Monitor it via Prometheus:

```
vllm:spec_decode_draft_acceptance_length
```

If acceptance drops below 0.5 tokens per step, you have the wrong draft model. It adds overhead rather than saving it. The draft model must match the target architecture -- vLLM won't warn you about this at startup.
## Deployment Mode

The last decision is serverless vs. pods, and it's purely a traffic pattern question.

Spiky or unpredictable traffic belongs on serverless -- you pay only for actual inference time. Sustained, predictable load is cheaper on pods because you're not paying the serverless premium on every call.

Neither is universally better. The mistake is running pods for workloads that get 10 requests an hour or paying for serverless when you have a steady 200 RPS.

## Why Decode is the Bottleneck

LLM generation has two phases and they're bound by different things.

Prefill is compute-bound -- processing all the input tokens in one parallel forward pass. Decode is memory-bound -- generating one token at a time, loading the entire model's KV cache from VRAM on every single step.

This means VRAM bandwidth determines inter-token latency, not FLOPs. Two GPUs with similar compute specs can have very different inference latency:

| GPU | Memory Bandwidth |
|-----|-----------------|
| H100 SXM5 | 3.35 TB/s |
| A6000 | 768 GB/s |

That's a ~4x difference on long-form generation. If you're choosing hardware for an inference workload and only looking at FLOPs, you're optimizing the wrong thing.

The practical checklist once you understand this:

- Quantize with AWQ first (or FP8 on H100s)
- Pick SGLang for agents and JSON, vLLM for chat
- Enable speculative decoding for long-form endpoints, monitor acceptance rate
- Wire Prometheus to `vllm:gpu_cache_usage_perc` to know when you're VRAM-constrained
- Match deployment mode to your actual traffic shape

The hardware question comes last, not first.
