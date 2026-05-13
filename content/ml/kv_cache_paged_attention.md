+++
title = "KV Cache and PagedAttention: Why vLLM Actually Works"
date = 2026-05-03T00:00:00+05:30
draft = false
math = false
author = "Krishnatejaswi S"
description = "KV cache stores attention keys and values across tokens to avoid recomputation during autoregressive decoding. PagedAttention extends this with virtual memory paging, making vLLM's throughput possible."
tags = ["machine-learning", "llm", "inference", "attention", "vllm"]
+++

LLM inference is split into two phases with completely different performance characteristics. The first phase processes all input tokens in parallel -- it's compute-bound, and modern GPUs handle it well. The second phase generates one token at a time -- it's memory-bandwidth-bound, and this is where naive serving falls apart.

The key data structure driving both phases is the KV cache.

## What the KV Cache Is

In the attention mechanism, each token attends to every previous token in the sequence. To compute attention for token N, you need the key and value vectors for tokens 1 through N-1. Recomputing those from scratch at each step would mean re-running the full model for all previous tokens every time you generate a new one -- O(N^2) compute per sequence.

The KV cache avoids this. After the prefill phase, the key and value vectors for every input token are stored in GPU memory. During the decode phase, each new token appended to the sequence just needs to compute its own K and V vectors and append them to the cache. Attending to all previous tokens is then a lookup into the cached K and V tensors, not a recomputation.

The cost of this: GPU memory. For a 7B parameter model at FP16, the KV cache for a single sequence can be hundreds of megabytes depending on context length, number of layers, and number of attention heads. For larger models serving many concurrent users, the KV cache dominates memory usage.

## The Fragmentation Problem

Naive serving allocates KV cache memory statically: reserve a maximum-size block for each sequence upfront. This has the same problem as a badly written memory allocator.

Say you pre-allocate 4096 tokens per sequence and your GPU can hold 20 such blocks. A new request comes in and needs 10 blocks. 18 are free but they're fragmented across physical memory -- no contiguous run of 10. Request rejected, GPU sitting at 60% capacity.

Even worse: you don't know the output length when a request arrives. If you allocate for the max context length immediately, most of that memory is wasted for short outputs. If you allocate conservatively, long outputs fail mid-generation.

## PagedAttention

vLLM's solution, introduced in the 2023 paper, borrows the virtual memory abstraction from operating systems.

Physical GPU memory is divided into fixed-size blocks (pages), typically 16 tokens each. Each sequence gets a logical block table that maps logical block indices to physical blocks. The blocks for one sequence don't need to be contiguous in physical memory -- the block table handles the translation.

```
Sequence A: logical [0,1,2] → physical [block_7, block_2, block_15]
Sequence B: logical [0,1]   → physical [block_3, block_11]
```

Blocks are allocated one at a time as tokens are generated, not all upfront. A short output uses a few blocks and returns them when done. A long output gradually accumulates more. Fragmentation is eliminated because the allocation granularity matches the actual growth pattern of sequences.

The result: GPU memory utilization goes from 20-40% with naive block allocation to 70-90% with PagedAttention. More sequences fit in memory simultaneously, which means higher throughput.

## Continuous Batching

PagedAttention works with continuous batching to make the GPU utilization gains practical.

Traditional batching waits until a batch of N requests is assembled, runs inference for the full batch, returns all results. Any sequence that finishes early holds its slot until the full batch is done. Expensive for variable-length outputs.

Continuous batching (also called iteration-level scheduling) processes one decode step at a time across all in-flight sequences. After each step, finished sequences are removed and new requests are inserted into the freed slots. The batch is always full -- there's no waiting.

Combined with PagedAttention, the memory freed by completed sequences is immediately available for new ones. The GPU is busy at every step, not idling through early completions.

## RadixAttention

SGLang introduced RadixAttention for workloads with shared prompt prefixes, common in agentic systems and structured generation.

Consider an agent that runs many LLM calls with the same system prompt and tool definitions -- often 1000+ tokens. With standard PagedAttention, each request recomputes the KV vectors for those shared tokens during prefill. If you're making 100 calls with the same 1000-token preamble, that's 100x the prefill compute for tokens that never change.

RadixAttention maintains a radix tree of cached KV blocks keyed by token sequence prefix. When a new request arrives, it walks the tree to find the longest matching prefix, reuses those cached blocks, and only computes KV vectors for the novel suffix.

For agentic workloads where the same system prompt and tool list appear in every call, the first request pays the full prefill cost. Every subsequent request with the same prefix pays only for its unique portion. At the scale of thousands of agent steps, this is a substantial throughput difference.

The tradeoff: RadixAttention adds cache management overhead. The tree needs to be pruned when memory pressure is high. The eviction policy matters -- evicting a heavily shared prefix that gets reused on the next request undoes the benefit. SGLang uses LRU eviction, which works well for stable prefixes but less well for highly dynamic ones.

## Choosing Between vLLM and SGLang

The choice comes down to workload:

**vLLM** is the default for general inference, chat APIs, and throughput benchmarks. PagedAttention and continuous batching are well-tested across a wide range of models and hardware.

**SGLang** is better for agentic workflows, structured output (constrained decoding for JSON, function calling), and any case where many requests share large prompt prefixes. The RadixAttention benefit only materializes when your prefix reuse rate is high.

Both expose an OpenAI-compatible API and support the same quantization formats. Running both and profiling your actual traffic pattern is the right answer if you're unsure -- the throughput difference on real workloads is usually decisive.

The KV cache is why LLM inference is memory-bound rather than compute-bound during decode. Understanding it makes the rest of the optimization landscape -- quantization to shrink the model, PagedAttention to use memory efficiently, RadixAttention to reuse computation -- follow naturally from first principles.
