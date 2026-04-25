# Week 2 - 6-Hour Study Plan

This plan is designed to complete both:

- `learning/week02_study_checklist.md`
- `algorithments_tasks_and_tests/week02.tex`

It follows `learning_method.jsonld` strategy emphasis:
- **Deliberate Practice** (Week 2 focus)
- **Learn -> Apply -> Explain -> Review**

---

## Hour 1 (0:00-1:00) - Learn + Setup

- Read all prompts in `algorithments_tasks_and_tests/week02.tex` once.
- Open `learning/week02_study_checklist.md` and use it as your grading rubric.
- Create scratch notes with 4 sections:
  - Hashing/chaining
  - Infinite-room search
  - Two-sum exact `= h`
  - Closest pair `<= h` in worst-case linear

### End-of-hour goal
You can restate each problem in 1-2 sentences.

---

## Hour 2 (1:00-2:00) - Hash Table Task (from `.tex`)

Solve:

- `C = [3, 18, 42, 31, 40, 56, 71]`
- `h(k) = (8k + 2) mod 7`
- table size `7`
- collision strategy: chaining, append to end

Deliverables:

- Compute each hash index correctly.
- Draw final table `0..6` with chains in insertion order.
- Write short explanation of why collisions happen and how chains affect operations.

### Checklist items covered
- Compute hash values with modular arithmetic
- Insert keys in order
- Resolve collisions with chaining
- Explain collision effects on lookup/insert

---

## Hour 3 (2:00-3:00) - Searching in Infinite Rooms `O(log k)`

Write algorithm:

1. Ask rooms `1,2,4,8,...` until target room `k` is bracketed.
2. Binary search in the final bracket interval.

Write runtime justification:

- Doubling/bracketing takes `O(log k)`.
- Binary search in bracket also takes `O(log k)`.
- Total remains `O(log k)`.

### Checklist items covered
- Exponential search for bracketing
- Binary search after bracketing
- Correct total complexity argument

---

## Hour 4 (3:00-4:00) - Campus Construction (a): Exact Two-Sum Expected `O(n)`

Write pseudocode using hash set/table:

- Iterate each `x` in `S`.
- Check whether `h - x` is already seen.
- If yes: pair exists.
- Else: insert `x` and continue.

Add correctness + complexity notes:

- If pair exists, second element will find first in hash set.
- Hash operations are expected `O(1)`.
- Total expected time is `O(n)`.

### Checklist items covered
- Solve exact two-sum in expected `O(n)`
- Explain expected vs worst-case for hashing methods

---

## Hour 5 (4:00-5:00) - Campus Construction (b): Closest Sum `<= h` Worst-Case `O(n)`

Use prompt assumption: `h = 800n^8`.

Approach:

1. Sort integers in linear time under bounded-integer assumptions (integer-key linear sorting setting).
2. Two-pointer scan:
   - `i` at smallest, `j` at largest
   - if `S[i] + S[j] > h`, move `j` left
   - else record candidate, move `i` right
3. Track best valid sum seen.

Justify:

- Linear-time integer sorting is valid under the assignment assumptions.
- Two-pointer pass is linear.
- Total worst-case remains `O(n)`.

### Checklist items covered
- Best pair with sum `<= h`
- Worst-case linear justification under bounded assumptions

---

## Hour 6 (5:00-6:00) - Explain + Review + Final Check

- Feynman pass: explain all 4 tasks out loud in simple language.
- Check every checkbox in `learning/week02_study_checklist.md`.
- Final quality pass on `.tex` responses:
  - clear steps
  - explicit runtime
  - expected vs worst-case wording correct
- Create 10 flashcards from mistakes for spaced review.

### End-of-session goal
- All `week02.tex` questions answered cleanly.
- All checklist items completed.
- Can re-derive each algorithm from memory.

---

## Quick Homework-Style Answer Skeletons

### Searching for Keys
"First query rooms `1,2,4,8,...` until the target is bracketed in an interval. Then binary search inside that interval. The first phase takes `O(log k)` and the second phase takes `O(log k)`, so total is `O(log k)`."

### Campus Construction (a)
"Scan each element `x` in `S`, check if `h-x` is already in a hash set of seen elements. If yes, return that a pair exists; otherwise insert `x` and continue. Hash lookup/insert is expected `O(1)`, so total expected time is `O(n)`."

### Campus Construction (b)
"Given the bounded-integer setting (`h=800n^8`), sort in worst-case linear time using an integer-key linear sorting method. Then run a two-pointer sweep from both ends to find the largest sum not exceeding `h` in one linear pass. Total worst-case time is `O(n)`."

---

## Final Submission Checklist

- [ ] Hash indices and final chained table are correct
- [ ] Infinite-room algorithm + `O(log k)` proof included
- [ ] Two-sum expected `O(n)` algorithm and explanation included
- [ ] Closest `<= h` worst-case `O(n)` algorithm and proof included
- [ ] Expected vs worst-case distinctions are explicit
- [ ] No answer exceeds `h` in closest-sum part
