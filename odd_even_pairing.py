def main():
    n = int(input())
    if n % 4 not in (0, 3):
        print("NO")
        return
    
    set1 = []
    set2 = []
    toggle = True
    
    if n % 4 == 0:
        low = 1
        high = n
        while low <= high:
            if toggle:
                set1.append(low)
                set1.append(high)
            else:
                set2.append(low)
                set2.append(high)
            low += 1
            high -= 1
            toggle = not toggle
    else:
        for i in range(1, n+1):
            if i % 4 == 1 or i % 4 == 2:
                set1.append(i)
            else:
                set2.append(i)
    
    # Output the result
    print("YES")
    print(len(set1))
    print(" ".join(map(str, set1)))
    print(len(set2))
    print(" ".join(map(str, set2)))

if __name__ == "__main__":
    main()