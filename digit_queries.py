def digit_query(k):
    digits = 1
    total_digits = 0
    while True:
        numbers_in_group = 9 * 10**(digits - 1)
        group_digits = numbers_in_group * digits
        if k <= total_digits + group_digits:
            break
        total_digits += group_digits
        digits += 1

    offset_in_group = k - total_digits - 1

    number_index = offset_in_group // digits
    digit_index = offset_in_group % digits

    start_number = 10**(digits - 1)
    actual_number = start_number + number_index
    digit_str = str(actual_number)

    return digit_str[digit_index]

def main():
    n = int(input())
    queries = []
    for i in range(n):
        queries.append(int(input()))
    for query in queries:
        print(digit_query(query))

if __name__ == "__main__":
    main()