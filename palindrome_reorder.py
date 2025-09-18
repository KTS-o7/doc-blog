def main():
    string = input().strip()
    string = string.upper()
    count = {}
    for char in string:
        count[char] = count.get(char, 0) + 1
    
    odd = 0
    odd_char = ''
    for char in count:
        if count[char] % 2 == 1:
            odd += 1
            odd_char = char
    
    if odd > 1:
        print("NO SOLUTION")
        return
    
    first_half = []
    for char in sorted(count.keys()):  
        if count[char] % 2 == 0:
            for i in range(count[char] // 2):
                first_half.append(char)
    
    # Build the palindrome
    result = first_half.copy()
    if odd_char:
        for i in range(count[odd_char]):
            result.append(odd_char)
    result.extend(first_half[::-1])  
    
    print(''.join(result))

if __name__ == "__main__":
    main()