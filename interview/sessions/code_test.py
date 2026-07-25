#'''
#A phrase is a palindrome if, after converting all uppercase letters into lowercase letters and removing all non-alphanumeric characters, it reads the same forward and backward. Alphanumeric characters include letters and numbers.
#
#Given a string s, return true if it is a palindrome, or false otherwise.
# 
#Example 1:
#
#Input: s = "A man, a plan, a canal: Panama"Output: trueExplanation: "amanaplanacanalpanama" is a palindrome.
#
#Example 2:
#
#Input: s = "race a car"Output: falseExplanation: "raceacar" is not a palindrome.
#
#Example 3:
#
#Input: s = " "Output: trueExplanation: s is an empty string "" after removing non-alphanumeric characters.
#
#Since an empty string reads the same forward and backward, it is a palindrome.
#'''
#def solution(s):
#    s = ''.join([_ for _ in s.lower() if _.isalnum()])
#    l = len(s)
#    mid = len(s) // 2
#    if l % 2 != 0:
#        mid += 1
#    left = s[:mid-1]
#    right = s[mid:][::-1]
#
#    return True if left == right else False


'''Question:
Given an array nums containing n distinct numbers in the range [0, n], return the only number in the range that is missing from the array.
 
Verification:
 
find_missing_num([0,1,3]) #returns 2
find_missing_num([3,2,1]) #returns 0
find_missing_num([2,1,0]) #returns 3
find_missing_num([4,2,3,5,0]) #returns 1'''

def solution(l):
    l = eval(l)
    size = len(l)
    print(size)
    step = 1 if l[0] - l[-1] < 0 else -1
    print(step)
    r = list(range(l[0], l[-1] + step, step))
    # [3, 2, 1]
    print(f'r: {r}')
    found = False
    for _ in r:
        if _ not in l:
            found = True
            return _
    if not found:
        return r[-1] + step

if __name__ == '__main__':
    import sys
    print(solution(sys.argv[1]))
