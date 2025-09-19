def main():
    n = int(input())
    for i in range(2**n):
        num = i^(i>>1)
        num_str = bin(num)[2:].zfill(n)
        print(num_str, end="\n")

if __name__ == "__main__":
    main()