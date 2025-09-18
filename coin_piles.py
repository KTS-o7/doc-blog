def main():
    n = int(input())
    for i in range(n):
        a, b = map(int, input().split())
        if (a+b)%3 == 0 and max(a,b) <= 2*min(a,b):
            print("YES")
        else:
            print("NO")

if __name__ == "__main__":
    main()