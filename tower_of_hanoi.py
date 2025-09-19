def main():
    n = int(input())
    print(2**n - 1)
    tower_of_hanoi(n, 1, 3, 2)

def tower_of_hanoi(n, source, target, auxiliary):
    if n == 1:
        print(source, target)
        return
    tower_of_hanoi(n-1, source, auxiliary, target)
    print(source, target)
    tower_of_hanoi(n-1, auxiliary, target, source)

if __name__ == "__main__":
    main()