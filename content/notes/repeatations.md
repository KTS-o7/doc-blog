+++
title = 'Repeatations'
date = 2025-09-18T17:23:25+05:30
draft = false
math = true
+++

Link to the problem : [Repeatations](https://cses.fi/problemset/task/1069)

## Intuition
This problem wants us to find the longest substring of a string that has only 1 type of character.
input has A,G,C and T only.

Edge case: if the string is empty, return 0.

We need to keep track of the current length of the substring and the maximum length of the substring seen so far which satisfies the condition.

Loop through the string and check if the current character is the same as the previous character.
- If it is, increment the current length.
  Update the maximum length if the current length is greater than the maximum length.
- If it is not, reset the current length to 1.



## Solution
```python
def main():
    string = input().strip()
    if not string:
        print(0)
        return
    
    max_len = 1
    current_len = 1
    
    for i in range(1, len(string)):
        if string[i] == string[i-1]:
            current_len += 1
            max_len = max(max_len, current_len)
        else:
            current_len = 1
    
    print(max_len)

if __name__ == "__main__":
    main()
```

### Time complexity
O(n)

### Space complexity
O(1)

This is a greedy problem.
A greedy approach is something that makes the best local choice at each step in the hope that this choice will lead to the global optimal solution.

here the best local choice is to increment the current length if the current character is the same as the previous character.