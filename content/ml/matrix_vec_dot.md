+++
title = 'Matrix-Vector Dot Product'
date = 2025-09-06T07:07:07+01:00
draft = false
math = true
+++

## Matrix-Vector Dot Product

1. [Question 1 From deep-ml.com](https://www.deep-ml.com/problems/1)
Essentially a dot product of a matrix and a vector an happen only if the number of columns in the matrix is equal to the number of elements in the vector.

That is if A[m,n] and B[n], then A*B is defined.

So in this case, the matrix is 2x3 and the vector is 3x1, so the dot product is defined.

The result is a 2x1 matrix.

The result is:

$$
\begin{bmatrix}
1 & 2 & 3 \\
4 & 5 & 6 \\
\end{bmatrix}
\cdot
\begin{bmatrix}
1 \\
2 \\
3 \\
\end{bmatrix}
\equiv
\begin{bmatrix}
1 \cdot 1 + 2 \cdot 2 + 3 \cdot 3 \\
4 \cdot 1 + 5 \cdot 2 + 6 \cdot 3 \\
\end{bmatrix}
\equiv
\begin{bmatrix}
14 \\
32 \\
\end{bmatrix}
$$

## Solution
```python
def matrix_dot_vector(a: list[list[int|float]], b: list[int|float])
 -> list[int|float]:
	# Return a list where each element is the dot product of a row of 'a' with 'b'.
	# If the number of columns in 'a' does not match the length of 'b', return -1.
    if len(a[0]) != len(b):
        return -1
    c = []
    for i in range(len(a)):
        sum = 0
        for j in range(len(a)):
            sum += a[i][j]*b[j]

        c.append(sum)
	return c
```
---