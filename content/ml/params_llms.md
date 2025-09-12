+++
title = ' Parameters in LLMs'
date = 2025-09-12T17:23:41+05:30
draft = false
math = true
+++

# Generation-Time Parameters in Large Language Models

I recently dove deep into how LLMs like GPT-3, GPT-4, and open-source models generate text, and I was fascinated by the sheer number of knobs and dials available to control their behavior. These aren't just abstract concepts,they're the tools that make the difference between getting a coherent essay or a rambling mess, between creative poetry or repetitive drivel.

In this post, I'll break down the key generation-time hyperparameters with practical examples, mathematical foundations, and real-world implications. We'll go beyond the surface-level explanations and understand why each parameter matters and how to tune them effectively.

## Temperature: The Creativity Knob

Temperature is arguably the most important parameter you'll encounter when using LLMs. It's like adjusting the "personality" of the model.

**What it does**: Temperature scales the logits (raw prediction scores) before they're converted to probabilities via softmax. Mathematically:

$$
P(w_i) = \frac{e^{z_i / T}}{\sum_j e^{z_j / T}}
$$

where `z_i` is the logit for token `i`, and `T` is temperature.

**Why it works**: At lower temperatures (`T` < 1), the probability distribution becomes sharper, high-probability tokens become even more likely, leading to more predictable, conservative outputs. At higher temperatures (`T` > 1), the distribution flattens, giving low-probability tokens a better chance.

**Real-world example**: When generating code, you want `T=0.1` for deterministic, correct syntax. For creative writing, `T=0.8-1.2` gives you that spark of originality. I've seen `T=2.0` produce genuinely surprising and creative outputs, though sometimes bordering on incoherent.

**Typical range**: `0.0` (completely deterministic) to `2.0` (highly random). Most applications use `0.7-1.0`.

## Top-k Sampling: Quality Control

Top-k is like telling the model, "Only consider your top k most confident predictions."

**What it does**: After computing all token probabilities, sort them and keep only the top k tokens, then renormalize their probabilities.

**Why it works**: It prevents the model from picking extremely unlikely tokens that might derail the generation. For example, if the model is writing about "coffee," top-k=50 ensures it doesn't suddenly switch to discussing quantum physics unless that was already in its top 50 predictions.

**Practical tip**: For factual writing, use lower k (10-40) to stay on topic. For creative tasks, higher k (50+) allows more flexibility. I've found k=1 essentially gives you greedy decoding,always pick the most likely token.

## Top-p (Nucleus Sampling): Dynamic Quality Control

Top-p takes top-k's idea but makes it adaptive.

**What it does**: Instead of a fixed number of tokens, select the smallest set whose cumulative probability exceeds p. So if p=0.9, it might use 10 tokens one time and 50 tokens another time, depending on the probability distribution.

**Why it works**: In scenarios where the model is very confident (sharp distribution), it uses fewer tokens. When uncertain (flat distribution), it considers more options. This is particularly useful for maintaining coherence while allowing creativity.

**Example**: Writing a technical explanation,early tokens are predictable, so top-p might use 5-10 tokens. When getting creative, it expands to 20-30 tokens. I've seen this outperform top-k in many creative writing tasks because it adapts to the model's confidence level.

**Typical range**: 0.8-1.0. Values below 0.5 can be too restrictive.

## Logit Bias: Manual Steering

This is the parameter for when you want to force the model's hand.

**What it does**: Directly add or subtract values from specific token logits before sampling:

$$
z_i' = z_i + b_i
$$

**Why it works**: Want to ban certain words? Set their bias to -100. Want to encourage specific terminology? Add positive bias. I once used this to prevent an LLM from using certain brand names in generated content.

**Practical applications**: Content moderation, style enforcement, or domain-specific vocabulary control. Particularly useful in enterprise settings where you need to avoid certain terms.

## Repetition Penalty: Fighting the Echo Chamber

Ever noticed how LLMs can get stuck repeating phrases? This parameter fights that.

**What it does**: For tokens that have appeared recently, divide their logits by a penalty factor r > 1:

$$
z_i' = \frac{z_i}{r}
$$

**Why it works**: It makes previously used tokens less attractive, encouraging the model to explore new vocabulary. Without this, models can get into loops like "The best coffee is the best coffee is the best coffee..."

**Real-world use**: Essential for long-form content generation. I use values around 1.1-1.2 for most tasks, but for very creative work, sometimes 1.05 or lower to allow some intentional repetition for emphasis.

## Stop Sequences: The Off Switch

Sometimes you need the model to know when to stop talking.

**What it does**: Define specific strings that, when generated, halt the generation process.

**Why it works**: Prevents runaway generation or ensures structured output. For example, when generating code, you might stop at the next function definition.

**Examples**: `"\n\n"`, `"END"`, `"</response>"`. I once used this to generate structured JSON by setting the stop sequence to `"}"`.

## Max Tokens: Setting Boundaries

The word limit for your AI writer.

**What it does**: Caps the total number of tokens generated in a single response.

**Why it works**: Prevents excessive output and manages costs/compute time. In API contexts, this also affects billing.

**Considerations**: Different models have different limits (GPT-4: 4096, Claude: 8192). Always set this lower than the model's maximum to leave headroom.

## Frequency Penalty: Discouraging Word Hoarders

Similar to repetition penalty, but based on overall frequency in the generated text.

**What it does**: Penalize tokens based on how often they've appeared:

$$
z_i' = z_i - \alpha \cdot \text{count}(i)
$$

**Why it works**: Prevents overuse of common words. If "the" appears 50 times, it gets increasingly penalized.

**Use cases**: Particularly effective for generating diverse content or when you want to avoid repetitive language patterns.

## Presence Penalty: Topic Freshness

This encourages introducing new concepts rather than revisiting old ones.

**What it does**: Penalize tokens that have appeared at all in the current generation:

$$
z_i' = z_i - \beta \cdot \text{presence}(i)
$$

where presence(i) is 1 if the token appeared, 0 otherwise.

**Why it works**: Promotes topic exploration. Without it, models can get stuck discussing the same ideas repeatedly.

**Difference from frequency penalty**: Frequency counts occurrences, presence is binary. Use presence penalty for encouraging breadth of topics.

## Num Keep: Context Continuity

For long conversations or documents, this maintains coherence.

**What it does**: When refreshing the context window, retain the last N tokens from the previous context.

**Why it works**: Prevents abrupt topic changes in long-form generation. Imagine writing a novel,the model needs to remember what happened in the previous chapter.

**Typical range**: 100-500 tokens, depending on the task complexity.

## Seed: Reproducibility Control

For when you need consistent outputs.

**What it does**: Initializes the random number generator with a fixed value, ensuring identical outputs for identical inputs.

**Why it works**: Crucial for testing, debugging, and applications requiring deterministic behavior. Without seeding, the same prompt can produce different outputs.

**Implementation note**: Not all APIs expose seed control, but when available, it's invaluable for quality assurance.

## Repeat Last N: Short-Term Memory

A more targeted repetition control.

**What it does**: Prevents tokens from the most recent N tokens from being selected.

**Why it works**: Stops immediate repetition like "I like coffee. I like coffee. I like coffee."

**Typical range**: 1-10 tokens. Higher values can prevent natural repetition that's actually desirable.

## Mirostat: Adaptive Temperature

This is for the advanced users who want the model to maintain consistent "surprise" levels.

**What it does**: Dynamically adjusts temperature to target a specific perplexity level using parameters τ (target perplexity) and η (adjustment rate).

**Why it works**: Maintains consistent creativity levels throughout generation. Traditional temperature can lead to increasingly erratic outputs as generation progresses.

**Typical range**: τ: 20-100, η: 0.05-0.2. Requires experimentation to find good values for your use case.

## Putting It All Together

These parameters don't exist in isolation, they interact in complex ways. For most applications, you'll primarily tune temperature, top-p, and repetition penalties. But understanding all of them gives you the full toolkit for controlling LLM behavior.

Remember: there's no "perfect" set of parameters. The best settings depend on your specific use case, model, and desired output characteristics. Experimentation and iteration are key.

What parameter have you found most useful in your LLM work? I'd love to hear your thoughts! 

ʕ •ᴥ•ʔ


