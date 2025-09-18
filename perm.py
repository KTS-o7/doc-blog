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