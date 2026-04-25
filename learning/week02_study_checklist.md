# Week 2 Study Checklist (Algorithms)

Use this as a quick prep sheet for Week 2 topics from `week02.tex`.

## What to Learn

- [ ] Compute hash values correctly using modular arithmetic.
- [ ] Insert keys into a hash table in order.
- [ ] Resolve collisions with chaining (append to end of chain).
- [ ] Explain why collisions happen and how chaining affects lookup/insert.
- [ ] Use exponential search to find a search range in an unbounded domain.
- [ ] Use binary search after bracketing to get total `O(log k)` queries.
- [ ] Solve exact two-sum in expected `O(n)` using a hash set/table.
- [ ] Explain expected vs worst-case runtime for hashing methods.
- [ ] Find best pair with sum `<= h` when no exact pair exists.
- [ ] Explain how to get worst-case linear time under bounded-integer assumptions.

## Core Ideas to Understand

### 1) Hash Tables and Chaining

- Hash function in Week 2 task: `h(k) = (8k + 2) mod 7`
- Table size is 7, so all indices are `0..6`.
- If two keys map to same index, store both in a linked chain (in insertion order).

What to be able to do:
- Compute each key's index quickly and accurately.
- Draw the final table with chains after all inserts.
- Describe the tradeoff: simple collision handling, but long chains can slow operations.

### 2) Searching in an Infinite Numbered Space

Problem pattern: the target is in room `k`, but you do not know `k` ahead of time.

Strategy:
1. Check rooms `1, 2, 4, 8, ...` until you pass the target range.
2. Binary search within the last interval.

Why it works:
- Doubling takes `O(log k)` checks to bracket `k`.
- Binary search in that interval is also `O(log k)`.
- Total remains `O(log k)`.

### 3) Exact Two-Sum in Expected `O(n)`

Goal: decide if any pair in `S` sums exactly to `h`.

Standard method:
- Iterate each `x` in `S`.
- Check whether `h - x` is already seen in a hash set.
- If yes, pair exists; if no, insert `x` and continue.

Reasoning:
- Hash lookup/insert is expected `O(1)`.
- Over `n` elements, expected time is `O(n)`.

### 4) Closest Sum `<= h` in Worst-Case `O(n)` (No Exact Match)

Goal: return pair with largest sum not exceeding `h`.

High-level approach:
1. Sort integers in linear time under the given bounded-value setup.
2. Use two pointers (`i` at smallest, `j` at largest):
   - If `S[i] + S[j] > h`, move `j` left.
   - Otherwise record candidate and move `i` right.
3. Keep best valid sum seen.

Why this matches the requirement:
- Linear-time integer sorting is possible with bounded integer ranges / digit-based sorting assumptions.
- Two-pointer scan is linear.
- Total worst-case time stays `O(n)` under those assumptions.

## Common Pitfalls

- Mixing up expected `O(n)` (hashing) with guaranteed worst-case `O(n)`.
- Forgetting to preserve insertion order in hash chains.
- Using only binary search for infinite-space search without first bracketing.
- Returning a pair above `h` in the closest-without-going-over problem.
- Not justifying why the sorting step can be linear in this specific setting.

## 5 Practice Questions

1. For keys `[3, 18, 42, 31, 40, 56, 71]`, compute each hash index under `h(k) = (8k+2) mod 7` and draw the final chained table.
2. Why does checking rooms `1,2,4,8,...` before binary search guarantee `O(log k)` total questions?
3. Give pseudocode for exact two-sum with expected `O(n)` and explain correctness in 2-3 sentences.
4. Compare expected-time hashing vs worst-case linear-time methods: when is each appropriate?
5. For the closest sum `<= h` problem, explain the two-pointer invariant and why it never misses the optimal pair.

## Quick Self-Test (Before You Move On)

- [ ] I can compute hash indices without mistakes.
- [ ] I can explain chaining and expected performance impact.
- [ ] I can derive why infinite-space search is `O(log k)`.
- [ ] I can write two-sum hash pseudocode from memory.
- [ ] I can justify worst-case `O(n)` for closest-sum under the given assumptions.

