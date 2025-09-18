#include <iostream>
#include <vector>
#include <string>
#include <sstream>

using namespace std;

int main() {
    int n;
    cin >> n;
    
    if (n % 4 != 0 && n % 4 != 3) {
        cout << "NO" << endl;
        return 0;
    }
    
    long long target_sum = (long long)n * (n + 1) / 4;
    vector<int> set1;
    vector<int> set2;
    
    int i = 1;
    int j = n;
    long long current_sum = 0;
    
    // Build set1 by taking alternating small and large numbers
    while (current_sum < target_sum) {
        if (current_sum + i <= target_sum) {
            set1.push_back(i);
            current_sum += i;
            i++;
        }
        if (current_sum + j <= target_sum && j > i) {
            set1.push_back(j);
            current_sum += j;
            j--;
        }
    }
    
    // Build set2 with remaining numbers
    vector<bool> in_set1(n + 1, false);
    for (int num : set1) {
        in_set1[num] = true;
    }
    
    for (int num = 1; num <= n; num++) {
        if (!in_set1[num]) {
            set2.push_back(num);
        }
    }
    
    // Output the result
    cout << "YES" << endl;
    cout << set1.size() << endl;
    for (size_t k = 0; k < set1.size(); k++) {
        cout << set1[k];
        if (k < set1.size() - 1) cout << " ";
        else cout << endl;
    }
    cout << set2.size() << endl;
    for (size_t k = 0; k < set2.size(); k++) {
        cout << set2[k];
        if (k < set2.size() - 1) cout << " ";
        else cout << endl;
    }
    
    return 0;
}