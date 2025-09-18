+++
title = 'Increasing Array'
date = 2025-09-18T22:37:39+05:30
draft = false
math = true
+++

Link to the problem : [Increasing Array](https://cses.fi/problemset/task/1094)

## Intuition
The idea is to make an array increasing by making the current element equal to or greater than the previous element.
and in each step we can increase the value of a single element by 1.

That means for `i`th element which is less than the `i-1`th element, we need `elem[i-1] - elem[i]` steps to make it equal to or greater than the `i-1`th element.

So we can come up with the following algorithm:
- Loop through the array
- If the current element is less than the previous element, we need to increase the current element to the previous element.
- Increment the count by the difference between the previous element and the current element.
- Update the current element to the previous element.

At the end of the loop, we will have the minimum number of steps to make the array increasing.

## Solution
```python
def main():
    n = int(input())
    nums = list(map(int, input().split()))
    count = 0
    for i in range(0,n-1):
        if nums[i] > nums[i+1]:
            count += nums[i] - nums[i+1]
            nums[i+1] = nums[i]
    print(count)

if __name__ == "__main__":
    main()
```

### Mathematical Proof

**Theorem:** The greedy algorithm that ensures each element is at least as large as its predecessor gives the minimum total cost to make the array non-decreasing.

**Proof by Induction:**

**Base Cases:**
- For an array of size 1: The cost is 0, which is trivially optimal.
- For an array of size 2: If `nums[0] ≤ nums[1]`, cost is 0. If `nums[0] > nums[1]`, we must increment `nums[1]` by `nums[0] - nums[1]` to make it ≥ `nums[0]`. This is optimal since we must satisfy `nums[1] ≥ nums[0]`.

**Inductive Hypothesis:** Assume the greedy algorithm is optimal for arrays of size ≤ k.

**Inductive Step:** Consider an array of size k+1. Let the array be `a[0], a[1], ..., a[k]`.

Apply the greedy algorithm:
1. Process the first k elements optimally (by inductive hypothesis)
2. For the last element `a[k]`, if `a[k-1] ≤ a[k]`, no change needed (cost 0)
3. If `a[k-1] > a[k]`, increment `a[k]` to `a[k-1]`, costing `a[k-1] - a[k]`

**Why this is optimal:** Any optimal solution must satisfy `a'[i] ≥ a'[i-1]` for all i, where `a'` is the final array.

For the prefix `a'[0] ... a'[k-1]`, the inductive hypothesis says our greedy choices give the minimum cost.

For the last pair `a'[k-1]` and `a'[k]`:
- We must have `a'[k] ≥ a'[k-1]`
- The minimum cost to achieve this is exactly `max(0, a'[k-1] - a'[k])`
- Our greedy algorithm achieves exactly this minimum cost

**Key insight:** The greedy choice doesn't affect the optimality of the prefix because:
1. The prefix constraints are already satisfied optimally
2. Setting `a[k] = max(a[k], a[k-1])` only affects the relationship between a[k-1] and a[k]
3. This choice is independent of future elements since there are none

**Proof by Contradiction :**
Suppose there exists an optimal solution with lower total cost than the greedy algorithm.
Let the greedy algorithm produce array `g` with cost `C_g`.
Let the optimal solution produce array `o` with cost `C_o < C_g`.

Since both `g` and `o` must satisfy `g[i] ≥ g[i-1]` and `o[i] ≥ o[i-1]` for all i:
- At the first position where `g` and `o` differ, the optimal solution must have made a different choice
- But making a different choice would either violate the non-decreasing constraint or require more operations later, contradicting optimality

Therefore, the greedy algorithm is optimal.

