def main():
    n = int(input())
    nums = list(map(int, input().split()))
    count = 0
    for i in range(0,n-1):
        if nums[i] > nums[i+1]:
            count += nums[i] - nums[i+1]
            nums[i+1] = nums[i]
    print(count)

if __name__ == "__main__":
    main()