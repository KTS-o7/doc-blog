def main():
    n = int(input())
    p = 5
    count = 1
    tot = 0
    while(n>=(p**count)):
        tot += n//(p**count)
        count+=1
    print(tot)

if __name__=="__main__":
    main()
