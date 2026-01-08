+++
title = 'Eigenvalues of a Matrix'
date = 2026-01-08T07:07:07+01:00
draft = false
math = true
+++


## Why Eigenvalues Matter

Eigenvalues describe the directions along which a linear transformation stretches or compresses space. Behind every PCA dimension, every stability analysis, and every spectral decomposition lies the same question: _What scalars \(\lambda\) satisfy \(A\mathbf{v} = \lambda \mathbf{v}\) for some non-zero vector \(\mathbf{v}\)?_ Here we clarify the polynomial road map to those scalars and show how it generalizes from 2×2 matrices to higher dimensions, including why principal minors appear in the coefficients.

## The Characteristic Equation

For any square matrix \(A\), the eigenvalues are the roots of the characteristic polynomial:

\[
\chi(\lambda) = \det(A - \lambda I) = 0.
\]

### 2×2 refresher

When \(A = \begin{bmatrix} a & b \\ c & d \end{bmatrix}\), the determinant expands to

\[
\chi(\lambda) = \lambda^2 - (a+d)\lambda + (ad - bc).
\]

Hence the trace \((a+d)\) appears as the \(\lambda\)-coefficient and the determinant \(ad-bc\) is the constant term. Solving the quadratic gives the eigenvalues.

## Worked Examples: \(n=3\) and \(n=4\)

### \(3 × 3\)

Let

\[
A = \begin{bmatrix}
a & b & c \\
d & e & f \\
g & h & i
\end{bmatrix}.
\]

Then \(A - \lambda I\) becomes

\[
\begin{bmatrix}
a - \lambda & b & c \\
d & e - \lambda & f \\
g & h & i - \lambda
\end{bmatrix},
\]
For a 3×3 matrix \( A = \begin{bmatrix} a & b & c \\ d & e & f \\ g & h & i \end{bmatrix} \), the characteristic polynomial expands as

\[
\chi(\lambda) = \lambda^3 - \text{tr}(A)\,\lambda^2 + \sigma_2(A)\,\lambda - \det(A),
\]

where \(\sigma_2(A)\) is the sum of the 2×2 principal minors:

\[
\sigma_2(A) = (ae - bd) + (ai - cg) + (ei - fh).
\]

Principal minors are the determinants of every square submatrix formed by selecting the same rows and columns. They appear because the expansion of \(\det(A - \lambda I)\) naturally produces sums over these subdeterminants—each coefficient gathers the contributions of principal minors of increasingly large size, which mathematically captures the pairwise, triple, etc., interactions between eigenvalues.

Notice:
- The \( \lambda^3 \) coefficient is 1 because the polynomial is monic.
- The \(-\text{tr}(A)\) term mirrors the 2×2 case.
- The constant term is \(-\det(A)\).
- Intermediate coefficients aggregate principal minors.

**Numeric example.** For
\[
A = \begin{bmatrix}
1 & 2 & 3 \\
0 & 4 & 5 \\
0 & 0 & 6
\end{bmatrix},
\]
the trace is 11, \(\sigma_2(A) = (1\cdot4 - 0\cdot2) + (1\cdot6 - 0\cdot3) + (4\cdot6 - 0\cdot5) = 4 + 6 + 24 = 34\), and the determinant is \(1\cdot4\cdot6 = 24\). The characteristic polynomial becomes \(\lambda^3 - 11\lambda^2 + 34\lambda - 24\), whose roots are the eigenvalues of \(A\).


### \(4 × 4\)

For a 4×4 matrix, the pattern continues. Without loss of generality, \(A\) produces

\[
\chi(\lambda) = \lambda^4 - \text{tr}(A)\,\lambda^3 + \sigma_2(A)\,\lambda^2 - \sigma_3(A)\,\lambda + \det(A),
\]

where:
- \(\sigma_2(A)\) sums all 2×2 principal minors,
- \(\sigma_3(A)\) sums all 3×3 principal minors,
- Signs alternate as dictated by the expansion of \(\det(A - \lambda I)\),
- Trace and determinant remain the first and last invariants, and the intermediate \(\sigma_k\) tie into symmetric polynomials of eigenvalues.

Each \(\sigma_k\) aggregates the determinants of the \(k \times k\) principal submatrices because the Leibniz expansion of the determinant iterates over all permutations of row/column pairs. Keeping track of these minors lets us express the characteristic polynomial coefficients without expanding every term manually, which is why they are a compact way to encode the invariant relationships between eigenvalues and the matrix entries.

**Numeric example.** Take
\[
A = \begin{bmatrix}
2 & 0 & 1 & 0 \\
0 & 3 & 0 & 1 \\
0 & 0 & 4 & 0 \\
0 & 0 & 0 & 5
\end{bmatrix}.
\]
The trace is 14, \(\sigma_2(A)\) collects the 2×2 minors (e.g., \(2\cdot3, 2\cdot4, 3\cdot4\) plus the shifts introduced by the 1s), and the determinant is \(2\cdot3\cdot4\cdot5 = 120\). The characteristic polynomial becomes \(\lambda^4 - 14\lambda^3 + \sigma_2(A)\lambda^2 - \sigma_3(A)\lambda + 120\), encoding the same invariants as before but for four eigenvalues.

These expressions remind us that the characteristic polynomial encodes global constraints: eigenvalues sum to the trace, pairwise products sum to \(\sigma_2(A)\), triple products to \(\sigma_3(A)\), and so on. Even though solving quartics or higher-degree polynomials analytically becomes impractical, numerical methods target the same invariants, so the conceptual road map stays intact.

## Method 1: Manual Calculation (Educational)

```python
import math

def calculate_eigenvalues_2x2(A: list[list[float | int]]) -> list[float]:
    if len(A) != 2 or len(A[0]) != 2 or len(A[1]) != 2:
        raise ValueError("Input must be a 2x2 matrix.")

    trace = A[0][0] + A[1][1]
    determinant = A[0][0] * A[1][1] - A[0][1] * A[1][0]

    discriminant = trace**2 - 4 * determinant
    if discriminant < 0:
        raise ValueError("Matrix has complex eigenvalues in this implementation.")

    eigenvalue_1 = (trace + math.sqrt(discriminant)) / 2
    eigenvalue_2 = (trace - math.sqrt(discriminant)) / 2

    return [eigenvalue_1, eigenvalue_2]
```

This hands-on route is excellent for reinforcing how the trace and determinant become coefficients of the characteristic polynomial and how complex eigenvalues arise when the discriminant is negative.

## Method 2: NumPy for the General Case

```python
import numpy as np

def calculate_eigenvalues_numpy(matrix: list[list[float | int]]) -> list[complex]:
    A = np.array(matrix)

    if A.shape[0] != A.shape[1]:
        raise ValueError("Input must be a square matrix.")

    eigenvalues = np.linalg.eigvals(A)
    return eigenvalues.tolist()
```

NumPy hides the polynomial expansion but still solves \(\det(A - \lambda I) = 0\). It handles arbitrary square matrices, complex eigenvalues, and higher dimensions effortlessly.

## Conclusion

Whether you expand a characteristic polynomial by hand for \(n=2\) or rely on NumPy for \(n>2\), the goal is the same: find the roots of \(\det(A - \lambda I)\). The trace and determinant continue to anchor the polynomial’s coefficients, while the intermediate terms encode sums of minors. Understanding this structure helps you make sense of the numerical results produced for large matrices and gives intuition for the algebra that underlies eigenvalue computation.
