+++
title = 'Missing Number'
date = 2025-09-18T17:17:22+05:30
draft = false
math = true
+++

Link to the problem : [Missing Number](https://cses.fi/problemset/task/1083)

## Intuition
This problem wants us to find the missing number in a sequence of numbers from 1 to n.
The naive approach is to use a hash map to store the numbers and then find the missing number.
But this is not efficient.

The idea is to use the formula for the sum of an arithmetic series.
The sum of an arithmetic series is given by the formula:

$$S = \frac{n}{2} (a + l)$$
where `n` is the number of terms, `a` is the first term, and `l` is the last term.
In this problem, the first term is 1 and the last term is `n`.
So the sum of the series is given by the formula:
$$S = \frac{n}{2} (1 + n)$$

now if we accumulate the sum of the numbers in the list, we can find the missing number by subtracting the sum of the numbers in the list from the sum of the series.
Since only one number is missing, the sum of the numbers in the list will be less than the sum of the series and the difference will be the missing number.

## Solution
```python
def main():
    n = int(input())
    nums_list = input().strip()
    nums = nums_list.split()
    total = 0
    for num in nums:
        total += int(num)
    tot = n * (n + 1) // 2
    print(tot - total)


if __name__ == "__main__":
    main()
```

## Some formulae for arithmetic series
###  nth term
$$a_n = a + (n-1)d$$
where `a` is the first term, `d` is the common difference, and `n` is the number of terms.
### sum of the first n terms
$$S = \frac{n}{2} (a + l)$$
where `n` is the number of terms, `a` is the first term, and `l` is the last term.
### sum of the first n terms
$$S = \frac{n}{2} (2a + (n-1)d)$$
where `n` is the number of terms, `a` is the first term, and `d` is the common difference.

