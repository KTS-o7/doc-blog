+++
title = 'Bit Strings'
date = 2025-09-19T22:53:15+05:30
draft = false
math = true
+++

Link to the problem : [Bit Strings](https://cses.fi/problemset/task/1617)

## Intuition
Problem is asking us to find the number of combinations of 0s and 1s of length n.
Basically its 2^n combinations.

## Solution
```python
def main():
    n = int(input())
    print(2**n % 1000000007)

if __name__ == "__main__":
    main()
```

In python it feels cheating to use the power operator **, but it is a valid way to solve the problem.

In lower level languages like C, C++, Java, we need to use a loop to calculate the power of 2 and each time we take modulo 1e9+7.

```c
#include <stdio.h>
#include <stdlib.h>

int main() {
    int n;
    scanf("%d", &n);
    long long result = 1;
    for(int i = 0; i < n; i++) {
        result = (result * 2) % 1000000007;
    }
    printf("%lld\n", result);
    return 0;
}
```