def apple_division(apples):
    n = len(apples)
    total = sum(apples)
    min_diff = total
    for i in range(1<<n):
        group1_sum = 0
        for j in range(n):
            if i & (1<<j):
                group1_sum += apples[j]
        group2_sum = total - group1_sum
        min_diff = min(min_diff, abs(group1_sum - group2_sum))
    return min_diff

def main():
    n = int(input())
    apples = list(map(int, input().split()))
    print(apple_division(apples))

if __name__ == "__main__":
    main()