+++
title = 'Gray Code'
date = 2025-09-19T23:03:51+05:30
draft = false
math = true
+++

Link to the problem : [Gray Code](https://cses.fi/problemset/task/2205)

## Intuition
The problem is asking us to generate the gray code for a given number n.

Gray code is a binary numeral system where two successive values differ in only one bit.
This is similar to bit strings problem. But instead of printing the binary representation of the number, we need to print the gray code.

The formula to generate the gray code for a given number n is:
$$G(n) = n \oplus (n >> 1)$$

## Solution
```python
def main():
    n = int(input())
    for i in range(2**n):   
        num = i^(i>>1)
        num_str = bin(num)[2:].zfill(n)
        print(num_str, end="\n")

if __name__ == "__main__":
    main()
```

## Other possible solutions
### Bit-by-Bit Approach

This approach constructs the Gray code by calculating each bit position individually using the property that the i-th bit of the Gray code is the XOR of the i-th and (i+1)-th bits of the binary representation.

#### Dry Run for n = 2

For n = 2, we need to generate 4 Gray codes (2² = 4). Let's walk through each iteration:

**Iteration 1: i = 0**
- Binary representation: 00
- **Bit position 0 (rightmost):**
  - Current bit: (0 >> 0) & 1 = 0 & 1 = 0
  - Next bit: (0 >> 1) & 1 = 0 & 1 = 0 (since bit position 1 < n=2)
  - Gray bit: 0 ⊕ 0 = 0
  - Set bit: gray = 0 | (0 << 0) = 0
- **Bit position 1:**
  - Current bit: (0 >> 1) & 1 = 0 & 1 = 0
  - Next bit: 0 (since bit position 2 >= n=2)
  - Gray bit: 0 ⊕ 0 = 0
  - Set bit: gray = 0 | (0 << 1) = 0
- Result: 00

**Iteration 2: i = 1**
- Binary representation: 01
- **Bit position 0:**
  - Current bit: (1 >> 0) & 1 = 1 & 1 = 1
  - Next bit: (1 >> 1) & 1 = 0 & 1 = 0
  - Gray bit: 1 ⊕ 0 = 1
  - Set bit: gray = 0 | (1 << 0) = 1
- **Bit position 1:**
  - Current bit: (1 >> 1) & 1 = 0 & 1 = 0
  - Next bit: 0 (since bit position 2 >= n=2)
  - Gray bit: 0 ⊕ 0 = 0
  - Set bit: gray = 1 | (0 << 1) = 1
- Result: 01

**Iteration 3: i = 2**
- Binary representation: 10
- **Bit position 0:**
  - Current bit: (2 >> 0) & 1 = 2 & 1 = 0 (2 in binary is 10, rightmost bit is 0)
  - Next bit: (2 >> 1) & 1 = 1 & 1 = 1
  - Gray bit: 0 ⊕ 1 = 1
  - Set bit: gray = 0 | (1 << 0) = 1
- **Bit position 1:**
  - Current bit: (2 >> 1) & 1 = 1 & 1 = 1
  - Next bit: 0 (since bit position 2 >= n=2)
  - Gray bit: 1 ⊕ 0 = 1
  - Set bit: gray = 1 | (1 << 1) = 1 | 2 = 3
- Result: 11

**Iteration 4: i = 3**
- Binary representation: 11
- **Bit position 0:**
  - Current bit: (3 >> 0) & 1 = 3 & 1 = 1 (3 in binary is 11, rightmost bit is 1)
  - Next bit: (3 >> 1) & 1 = 1 & 1 = 1
  - Gray bit: 1 ⊕ 1 = 0
  - Set bit: gray = 0 | (0 << 0) = 0
- **Bit position 1:**
  - Current bit: (3 >> 1) & 1 = 1 & 1 = 1
  - Next bit: 0 (since bit position 2 >= n=2)
  - Gray bit: 1 ⊕ 0 = 1
  - Set bit: gray = 0 | (1 << 1) = 2
- Result: 10

**Final Gray Code Sequence:** 00, 01, 11, 10

Notice how each consecutive Gray code differs by only one bit:
- 00 → 01 (bit 0 changes: 0→1)
- 01 → 11 (bit 1 changes: 0→1)
- 11 → 10 (bit 0 changes: 1→0)


```python
def generate_gray_code_bitwise(n):
    result = []
    for i in range(2**n):
        gray = 0
        for bit in range(n):
            # Gray bit is XOR of current bit and next bit
            current_bit = (i >> bit) & 1 # this step get the current bit using bitwise shift and bitwise and
            next_bit = (i >> (bit + 1)) & 1 if bit + 1 < n else 0 # this step get the next bit using bitwise shift and bitwise and
            gray_bit = current_bit ^ next_bit # this step get the gray bit using bitwise xor
            gray |= (gray_bit << bit) # this step set the gray bit using bitwise or
        result.append(bin(gray)[2:].zfill(n))
    return result

def main():
    n = int(input())
    gray_codes = generate_gray_code_bitwise(n)
    for code in gray_codes:
        print(code)

if __name__ == "__main__":
    main()
```