# def possible_game(n, a, b):
#     if n == 1 and a== 0 and b== 0:
#         print("YES")
#         print(1)
#         print(1)
#         return
#     elif n == 1 and a != b:
#         print("NO")
#         return
#     # If impossible score combination (cannot have more wins than rounds, or negative)
#     if a < 0 or b < 0 or a + b > n:
#         print("NO")
#         return

#     A = list(range(1, n+1))
#     B = [None] * n
#     available = set(range(1, n+1))
#     draws = n - a - b

#     # Assign draws first
#     for i in range(draws):
#         B[i] = A[i]
#         available.remove(A[i])

#     # Assign B's wins (B must beat A)
#     idx = draws
#     for _ in range(b):
#         found = False
#         for val in sorted(available):
#             if val > A[idx]:
#                 B[idx] = val
#                 available.remove(val)
#                 found = True
#                 break
#         if not found:
#             print("NO")
#             return
#         idx += 1

#     # Assign A's wins (A must beat B)
#     for j in range(idx, n):
#         found = False
#         for val in sorted(available, reverse=True):
#             if val < A[j]:
#                 B[j] = val
#                 available.remove(val)
#                 found = True
#                 break
#         if not found:
#             print("NO")
#             return

#     print("YES")
#     print(" ".join(map(str, A)))
#     print(" ".join(map(str, B)))


# def main():
#     t = int(input())
#     for _ in range(t):
#         n, a, b = map(int, input().split())
#         possible_game(n, a, b)

# if __name__ == "__main__":



def main():
    t = int(input())
    for _ in range(t):
        n, a, b = map(int, input().split())
        possible_game(n, a, b)

def possible_game(n, a, b):
    if a + b > n or a == n or b == n:
        print("NO")
        return
    
    A = list(range(1, n+1))
    B = list(range(1, n+1))

    # B wins: shift some elements forward
    counter = 0
    draws = n - a - b
    for i in range(draws):
        B[i] = A[i]
        counter += 1
    
    for i in range(b):
        temp = B[n-1]
        B[counter] = B[n-1]
        B[n-1] = temp
        counter += 1

    # Rest stay draws
    print("YES")
    print(*A)
    print(*B)

if __name__ == "__main__":
    main()    
