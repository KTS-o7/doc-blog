+++
title = 'Two Sets'
date = 2025-09-19T15:41:11+05:30
draft = false
math = true
+++

Link to the problem : [Two Sets](https://cses.fi/problemset/task/1092)

## Intuition
The problem asking us to partition the given set of numbers into two sets such that the sum of the numbers in the two sets are equal.

For the sum of two sets to be equal the total sum of the numbers must be even.
That means sum(numbers) % 2 == 0.
by the forumla for the sum of the first n natural numbers, sum(numbers) = n * (n + 1) / 2.
So that means sum of each set must be n * (n + 1) / 4.

Hence we got that n mod 4 is 0  or (n+1) mod 4 is 0, combining both we get n mod 4 must be 0 or 3 to be able to partition the numbers into two sets.
So this becomes a necessary condition for the problem to be solvable.

but this is not a sufficient condition.

When 
n mod 4 = 0:
Total sum is even, partition is possible.
The set can be split so both subsets have the same number of elements (equal size).

Example: 
n=8

Pairs: (8,1), (7,2), (6,3), (5,4)

Assign two pairs to one set, the other two pairs to the other set—both sum to 18.

When n mod 4 = 3:
Total sum is even, partition is possible.

The sets will have different sizes (one will have one more element).
Example: 
n=7

Pairs: (7,1,6) sums to 14, rest (2,3,4,5) sum to 14.

The sum of each smallest–largest pair is always n+1.

For  n mod 4 = 0: you can split pairs alternately between the two sets.

For n mod 4 = 3:  this is a tricky case
Consider some integer k such that we have n = 4k+3. that means n mod 4 = 3.
Now sum of n numbers is n * (n + 1) / 2 = (4k+3) * (4k+4) / 2 = (4k+3) * (2k+2)


---
### Mathematical Derivation

For n = 4k + 3, we assign:
- **Set 1**: numbers where i ≡ 1 or 2 (mod 4)
- **Set 2**: numbers where i ≡ 0 or 3 (mod 4)

#### Count of numbers in each residue class:
- **≡ 0 mod 4**: k numbers (4, 8, ..., 4k)
- **≡ 1 mod 4**: k+1 numbers (1, 5, ..., 4k+1)
- **≡ 2 mod 4**: k+1 numbers (2, 6, ..., 4k+2)
- **≡ 3 mod 4**: k+1 numbers (3, 7, ..., 4k+3)

#### Sum of each residue class:

**≡ 0 mod 4**:
```
4 + 8 + ... + 4k = 4(1 + 2 + ... + k) = 4 × k(k+1)/2 = 2k(k+1)
```

**≡ 1 mod 4**:
```
1 + 5 + 9 + ... + (4k+1)
```
Arithmetic series: first term = 1, last term = 4k+1, common difference = 4, terms = k+1
```
Sum = (k+1) × (1 + 4k+1)/2 = (k+1) × (4k+2)/2 = (k+1) × 2(k+1) = 2(k+1)²
```

**≡ 2 mod 4**:
```
2 + 6 + 10 + ... + (4k+2)
```
Arithmetic series: first term = 2, last term = 4k+2, common difference = 4, terms = k+1
```
Sum = (k+1) × (2 + 4k+2)/2 = (k+1) × (4k+4)/2 = (k+1) × 2(k+2) = 2(k+1)(k+2)
```

**≡ 3 mod 4**:
```
3 + 7 + 11 + ... + (4k+3)
```
Arithmetic series: first term = 3, last term = 4k+3, common difference = 4, terms = k+1
```
Sum = (k+1) × (3 + 4k+3)/2 = (k+1) × (4k+6)/2 = (k+1) × 2(k+3) = 2(k+1)(k+3)
```

#### Total sum verification:
```
Total sum = 2k(k+1) + 2(k+1)² + 2(k+1)(k+2) + 2(k+1)(k+3)
         = 2(k+1) × [k + (k+1) + (k+2) + (k+3)]
         = 2(k+1) × (4k + 6)
         = 2(k+1) × 2(2k + 3)
         = 4(k+1)(2k + 3)
```

Each set should sum to: **2(k+1)(2k + 3)**

#### Sum of each set:
**Set 1 (≡1 or ≡2 mod 4)**:
```
Sum = 2(k+1)² + 2(k+1)(k+2) = 2(k+1) × [(k+1) + (k+2)] = 2(k+1) × (2k + 3)
```

**Set 2 (≡0 or ≡3 mod 4)**:
```
Sum = 2k(k+1) + 2(k+1)(k+3) = 2(k+1) × [k + (k+3)] = 2(k+1) × (2k + 3)
```

Both sets sum to **2(k+1)(2k + 3)**, which is exactly half the total sum.

---

## Solution
```python
def main():
    n = int(input())
    if n % 4 not in (0, 3):
        print("NO")
        return
    
    set1 = []
    set2 = []
    toggle = True
    
    if n % 4 == 0:
        low = 1
        high = n
        while low <= high:
            if toggle:
                set1.append(low)
                set1.append(high)
            else:
                set2.append(low)
                set2.append(high)
            low += 1
            high -= 1
            toggle = not toggle
    else:
        for i in range(1, n+1):
            if i % 4 == 1 or i % 4 == 2: # 
                set1.append(i)
            else:
                set2.append(i)
    
    # Output the result
    print("YES")
    print(len(set1))
    print(" ".join(map(str, set1)))
    print(len(set2))
    print(" ".join(map(str, set2)))

if __name__ == "__main__":
    main()
```
