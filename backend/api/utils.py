import string


def encode_base62(num):
    alphabet = string.ascii_letters + string.digits
    if num == 0:
        return alphabet[0]
    arr = []
    while num:
        num, rem = divmod(num, 62)
        arr.append(alphabet[rem])
    arr.reverse()
    return ''.join(arr)


def decode_base62(short_code):
    alphabet = string.ascii_letters + string.digits
    num = 0
    for char in short_code:
        num = num * 62 + alphabet.index(char)
    return num