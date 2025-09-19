def backtrack(map, path, n):
    if len(path) == n:
        print(''.join(path))  # Base case: complete permutation
        return
    for char in sorted(map.keys()):
        if map[char] > 0:     # Only use available characters
            path.append(char)
            map[char] -= 1
            backtrack(map, path, n)
            path.pop()        # Undo choice (backtrack)
            map[char] += 1

def permutations(n):
    if n == 1:
        return 1
    return n * permutations(n-1)

def main():
    s = input()
    n = len(s)
    map = {}
    for char in s:
        map[char] = map.get(char, 0) + 1
    permute = permutations(n)
    for char in map:
        permute = permute // permutations(map[char])
    print(permute)
    backtrack(map, [], n)

if __name__ == "__main__":
    main()