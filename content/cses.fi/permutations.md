+++
title = 'Permutations'
date = 2025-09-18T22:49:10+05:30
draft = false
math = true
+++

Link to the problem : [Permutations](https://cses.fi/problemset/task/1070)

## Intuition
The idea is to generate a permutation of the numbers from 1 to n such that the difference between any two consecutive elements is at least greater than 1.

One way to do this is to first write all the even numbers between 1 and n in increasing order and then write all the odd numbers between 1 and n in increasing order.

This is only one such solution. There are other solutions as well.

## Solution
```python
def main():
    n = int(input())
    if n == 1:
        print(1)
        return
    if n < 4:
        print("NO SOLUTION")
        return
    for i in range(2,n+1,2):
        print(i, end=" ")
    for i in range(1,n+1,2):
        print(i, end=" ")

if __name__ == "__main__":
    main()
```

### Other possible solutions
- Write all the odd numbers between 1 and n in increasing order and then write all the even numbers between 1 and n in increasing order.
- Write all the odd numbers between 1 and n in decreasing order and then write all the even numbers between 1 and n in decreasing order.
- Write all the even numbers between 1 and n in increasing order and then write all the odd numbers between 1 and n in decreasing order.
