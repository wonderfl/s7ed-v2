def display_width(s: str) -> int:
    """한글은 2칸, 그 외는 1칸으로 계산한 너비"""
    width = 0
    for ch in s:
        if ord(ch) >= 0xAC00 and ord(ch) <= 0xD7A3:  # 한글 범위
            width += 2
        else:
            width += 1
    return width

def pad_string(s: str, target_width: int, align: str = 'left') -> str:
    """한글 너비를 고려하여 target_width까지 공백으로 채움"""
    current_width = display_width(s)
    pad_len = target_width - current_width
    if pad_len <= 0:
        return s
    if align == 'left':
        return s + ' ' * pad_len
    elif align == 'right':
        return ' ' * pad_len + s
    elif align == 'center':
        left = pad_len // 2
        right = pad_len - left
        return ' ' * left + s + ' ' * right
    else:
        raise ValueError("align은 'left', 'right', 'center' 중 하나여야 함")
