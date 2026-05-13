#!/usr/bin/env python3
"""
Inject description, tags, and author into Hugo post frontmatter.
Only modifies TOML frontmatter (+++...+++) files.
Skips files that already have a description field.
"""

import re
import os

AUTHOR = "Krishnatejaswi S"

# Map: relative path from content/ -> (description, tags)
META = {
    # === SYSTEMS ===
    "systems/bulkhead_pattern.md": (
        "How the bulkhead pattern isolates failures in distributed systems — partition thread pools, connection pools, and resources so one degraded dependency cannot sink the whole service.",
        ["distributed-systems", "reliability", "patterns", "bulkhead"]
    ),
    "systems/circuit_breakers_distributed_systems.md": (
        "Circuit breakers prevent cascading failures in distributed systems by tripping open when a downstream dependency fails, giving it time to recover while protecting callers.",
        ["distributed-systems", "reliability", "patterns", "circuit-breaker"]
    ),
    "systems/connection_pool_exhaustion.md": (
        "Diagnosing and fixing MongoDB connection pool exhaustion: SDAM monitoring, pool sizing, async leak patterns, and how to read the driver's topology events.",
        ["distributed-systems", "mongodb", "databases", "debugging", "infra"]
    ),
    "systems/consistent_hashing.md": (
        "Consistent hashing lets you add or remove nodes from a distributed cluster while minimising the number of keys that need to move — the algorithm behind Dynamo, Cassandra, and load balancers.",
        ["distributed-systems", "algorithms", "databases", "consistent-hashing"]
    ),
    "systems/crdts.md": (
        "CRDTs eliminate merge conflicts by design — commutative, associative, idempotent data structures that converge to the same state regardless of operation order. G-Counters, OR-Sets, and LWW registers explained.",
        ["distributed-systems", "crdt", "consistency", "algorithms"]
    ),
    "systems/multi_paxos.md": (
        "Multi-Paxos extends single-decree Paxos into a replicated log by electing a stable leader, skipping Phase 1 for subsequent entries, and batching proposals for throughput.",
        ["distributed-systems", "consensus", "paxos", "replication"]
    ),
    "systems/paxos.md": (
        "Paxos is a consensus protocol for getting a distributed system to agree on a single value despite node failures and message delays — the foundation of most replicated state machines.",
        ["distributed-systems", "consensus", "paxos"]
    ),
    "systems/paxos_consensus.md": (
        "A deep dive into Paxos: Phase 1 (Prepare/Promise) and Phase 2 (Accept/Accepted), safety guarantees, liveness limitations, and why real systems use Multi-Paxos instead.",
        ["distributed-systems", "consensus", "paxos", "replication"]
    ),
    "systems/raft_consensus.md": (
        "Raft is a consensus algorithm designed for understandability — leader election, log replication, and safety properties explained, with a comparison to Paxos.",
        ["distributed-systems", "consensus", "raft", "replication"]
    ),
    "systems/raft_log_compaction.md": (
        "Raft logs grow forever if left unchecked. Log compaction via snapshots lets nodes discard old entries, transfer state to slow followers, and recover quickly after a restart.",
        ["distributed-systems", "consensus", "raft", "replication"]
    ),
    "systems/saga_outbox_pattern.md": (
        "The outbox pattern solves the dual-write problem in event-driven systems: persist events to a local outbox table in the same transaction as your domain change, then relay them reliably.",
        ["distributed-systems", "patterns", "saga", "event-driven", "databases"]
    ),
    "systems/saga_pattern.md": (
        "The Saga pattern manages distributed transactions across microservices without 2PC — a sequence of local transactions with compensating actions for rollback when a step fails.",
        ["distributed-systems", "patterns", "saga", "microservices"]
    ),
    "systems/spanner_distributed_transactions.md": (
        "Google Spanner achieves globally consistent distributed transactions using TrueTime — bounded clock uncertainty instead of classic 2PC, enabling external consistency at planetary scale.",
        ["distributed-systems", "databases", "spanner", "transactions", "consistency"]
    ),
    "systems/two_phase_commit.md": (
        "Two-phase commit achieves distributed atomicity — all nodes commit or none do. But the coordinator is a single point of failure that can leave participants blocked indefinitely.",
        ["distributed-systems", "databases", "transactions", "2pc", "consistency"]
    ),
    "systems/vector_clocks.md": (
        "Vector clocks track causality in distributed systems — each event carries a logical timestamp that tells you whether two events are causally related or concurrent.",
        ["distributed-systems", "algorithms", "vector-clocks", "causality"]
    ),
    "systems/why_mysql_is_not_CA.md": (
        "MySQL is often called a CA system in CAP theorem discussions, but the reality is more nuanced — network partitions force tradeoffs even in single-master setups.",
        ["distributed-systems", "databases", "mysql", "cap-theorem", "consistency"]
    ),

    # === ML ===
    "ml/eigen_vals.md": (
        "Eigenvalues and eigenvectors — the linear algebra behind PCA, Google's PageRank, and the stability analysis of dynamical systems. Geometric intuition and computation.",
        ["machine-learning", "linear-algebra", "mathematics", "eigenvalues"]
    ),
    "ml/kv_cache_paged_attention.md": (
        "KV cache stores attention keys and values across tokens to avoid recomputation during autoregressive decoding. PagedAttention extends this with virtual memory paging, making vLLM's throughput possible.",
        ["machine-learning", "llm", "inference", "attention", "vllm"]
    ),
    "ml/llm_inference_optimization.md": (
        "LLM inference is memory-bandwidth bound, not compute bound. Continuous batching, speculative decoding, quantization, and KV cache management — the techniques that actually move the needle.",
        ["machine-learning", "llm", "inference", "optimization", "performance"]
    ),
    "ml/matrix_vec_dot.md": (
        "Matrix-vector dot products are the inner loop of neural network inference. Understanding the memory access patterns and FLOP counts explains why hardware utilisation matters so much.",
        ["machine-learning", "linear-algebra", "mathematics", "performance"]
    ),
    "ml/params_llms.md": (
        "How to count parameters in a transformer LLM — attention heads, MLP layers, embeddings, and normalization. Includes a worked example matching published model sizes.",
        ["machine-learning", "llm", "transformers", "mathematics"]
    ),
    "ml/twenty_things_about_gen_ai.md": (
        "Twenty observations about generative AI — capabilities, limitations, deployment realities, and the gap between benchmark performance and production usefulness.",
        ["machine-learning", "generative-ai", "llm"]
    ),

    # === INFRA ===
    "infra/cicd_docker_buildx_sha_deploys.md": (
        "SHA-tagged Docker images replace mutable latest tags, eliminating silent overwrites in CI/CD pipelines. Docker Buildx, multi-arch builds, and dynamic workflow generation for a Kubernetes platform.",
        ["infra", "cicd", "docker", "kubernetes", "devops"]
    ),
    "infra/kubernetes_oom_memory_leaks.md": (
        "Four memory leaks inside OOMKilled Kubernetes pods — slow async accumulation in Python services, unclosed client sessions, unbounded caches, and how to track each one down without a profiler.",
        ["infra", "kubernetes", "python", "debugging", "memory"]
    ),
    "infra/reverse_proxy.md": (
        "End-to-end HTTPS with Cloudflare Origin Certificates and Nginx — full-strict SSL mode, origin certificate installation, and Dockerfile configuration to eliminate 521 errors.",
        ["infra", "nginx", "cloudflare", "https", "security"]
    ),
    "infra/sse_disconnect_handling.md": (
        "Server-Sent Events in FastAPI silently drop cleanup code when a browser tab closes. How to detect client disconnects and ensure generator cleanup runs reliably.",
        ["infra", "fastapi", "python", "sse", "async"]
    ),
    "infra/vps_self_hosting.md": (
        "Running Obsidian LiveSync, Matrix Synapse, and Calibre-Web on a $22/year VPS — nginx reverse proxy, Docker Compose, Cloudflare tunnels, and what actually fits in 2.9GB RAM.",
        ["infra", "self-hosting", "vps", "docker", "nginx"]
    ),
    "infra/vps_self_hosting_stack.md": (
        "A minimal self-hosting stack on a budget VPS — three useful services (sync, chat, library) running on Docker Compose behind nginx, for under $22 a year.",
        ["infra", "self-hosting", "vps", "docker"]
    ),

    # === NOTES ===
    "notes/agentbudget_ulimit_for_ai_agents.md": (
        "An OSS contribution to AgentBudget: fixing silent $0 costs for streaming responses by hooking into the token usage callbacks that LangChain emits post-stream.",
        ["open-source", "ai-agents", "langchain", "oss-contribution"]
    ),
    "notes/bifrost_parallel_tool_call_fix.md": (
        "Debugging a parallel tool call streaming bug in Bifrost — how delta chunks from different tool calls interleave incorrectly and the fix that restores correct JSON assembly.",
        ["open-source", "debugging", "oss-contribution", "llm"]
    ),
    "notes/bit_strings.md": (
        "CSES bit string enumeration — counting and generating n-character strings over a binary alphabet using recursion and bitmask techniques.",
        ["competitive-programming", "cses", "combinatorics", "algorithms"]
    ),
    "notes/codex_worktrees_adventure.md": (
        "Running parallel AI coding agents with Git worktrees — isolate each task to its own working tree, fire agents concurrently, and merge results without conflicts.",
        ["ai-agents", "git", "productivity", "devtools"]
    ),
    "notes/coin_piles.md": (
        "CSES coin piles problem — determining whether two piles can be emptied with operations that remove one coin from one pile or one from each, using divisibility reasoning.",
        ["competitive-programming", "cses", "mathematics", "algorithms"]
    ),
    "notes/freeseek_proxy.md": (
        "Freeseek proxies DeepSeek's web chat interface into an OpenAI-compatible API endpoint, enabling local tools and agents to use DeepSeek R1 without an API key.",
        ["ai-tools", "open-source", "llm", "proxy"]
    ),
    "notes/git.md": (
        "Git internals and practical patterns — objects model, rebase vs merge, worktrees, reflog recovery, and the commands that matter for day-to-day engineering work.",
        ["git", "devtools", "productivity"]
    ),
    "notes/gray_code.md": (
        "Gray code generates binary sequences where consecutive values differ by exactly one bit — the algorithm, its uses in hardware and error correction, and a CSES solution.",
        ["competitive-programming", "cses", "algorithms", "combinatorics"]
    ),
    "notes/hermes_local_ai_stack.md": (
        "Building a local AI stack: Hermes as the agent framework, Bifrost for LLM routing, a Telegram bot as the interface, and Camoufox for browser automation — all running on local hardware.",
        ["ai-agents", "open-source", "llm", "self-hosting"]
    ),
    "notes/increasing_array.md": (
        "CSES increasing array — the minimum number of operations to make an array non-decreasing when you can only increment elements.",
        ["competitive-programming", "cses", "algorithms", "greedy"]
    ),
    "notes/markdown_stuff.md": (
        "A reference for Hugo-flavoured Markdown — shortcodes, callout blocks, math rendering with KaTeX, and code block options used on this site.",
        ["meta", "hugo", "markdown"]
    ),
    "notes/missing_number.md": (
        "CSES missing number — finding the missing integer in a permutation of 1..n in O(n) time using the arithmetic sum formula.",
        ["competitive-programming", "cses", "algorithms", "mathematics"]
    ),
    "notes/obsidian_second_brain.md": (
        "Building a second brain with Obsidian and Zettelkasten — atomic notes, linking ideas, periodic reviews, and an AI agent that surfaces connections you'd otherwise miss.",
        ["productivity", "obsidian", "zettelkasten", "ai-tools", "note-taking"]
    ),
    "notes/permutations.md": (
        "CSES permutations — constructing a permutation of 1..n with no two adjacent elements differing by 1, using an interleaving strategy.",
        ["competitive-programming", "cses", "algorithms", "combinatorics"]
    ),
    "notes/repeatations.md": (
        "CSES repetitions — finding the longest run of a single character in a string in a single linear pass.",
        ["competitive-programming", "cses", "algorithms", "strings"]
    ),
    "notes/teaching_myself_cs.md": (
        "A structured self-study plan for computer science fundamentals — algorithms, systems, databases, networks, and mathematics, with resources and a realistic timeline.",
        ["learning", "computer-science", "study-plan", "self-improvement"]
    ),
    "notes/two_sets.md": (
        "CSES two sets — partitioning integers 1..n into two subsets with equal sum, with a proof of when this is possible and an O(n) construction.",
        ["competitive-programming", "cses", "algorithms", "mathematics"]
    ),
    "notes/weird_algorithm.md": (
        "CSES weird algorithm (Collatz conjecture) — simulating the 3n+1 sequence and the open question of whether it always terminates.",
        ["competitive-programming", "cses", "algorithms", "mathematics"]
    ),
}

def inject_meta(filepath, description, tags, author):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Only handle TOML frontmatter (+++...+++)
    if not content.startswith('+++'):
        print(f"  SKIP (not TOML): {filepath}")
        return False

    # Check if description already exists
    if 'description =' in content or 'description=' in content:
        print(f"  SKIP (has description): {filepath}")
        return False

    tags_str = '", "'.join(tags)
    insert = f'author = "{author}"\ndescription = "{description}"\ntags = ["{tags_str}"]\n'

    # Insert after the last existing frontmatter field before closing +++
    # Find closing +++
    end_match = re.search(r'\n\+\+\+', content)
    if not end_match:
        print(f"  SKIP (no closing +++): {filepath}")
        return False

    insert_pos = end_match.start()
    new_content = content[:insert_pos] + '\n' + insert.rstrip('\n') + content[insert_pos:]

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(f"  OK: {os.path.basename(filepath)}")
    return True


def main():
    base = os.path.join(os.path.dirname(__file__), '..', 'content')
    base = os.path.abspath(base)

    updated = 0
    skipped = 0
    for rel_path, (description, tags) in META.items():
        full_path = os.path.join(base, rel_path)
        if not os.path.exists(full_path):
            print(f"  MISSING: {full_path}")
            skipped += 1
            continue
        result = inject_meta(full_path, description, tags, AUTHOR)
        if result:
            updated += 1
        else:
            skipped += 1

    print(f"\nDone: {updated} updated, {skipped} skipped")


if __name__ == '__main__':
    main()
