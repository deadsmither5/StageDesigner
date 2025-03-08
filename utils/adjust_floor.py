def is_adjacent(rect1, rect2):
    """
    检查两个矩形是否相接。
    """
    # 获取两个矩形的坐标
    x1_left, y1_top = rect1['left']
    x1_right, y1_bottom = rect1['right']
    
    x2_left, y2_top = rect2['left']
    x2_right, y2_bottom = rect2['right']
    
    # 检查是否有水平或垂直边界重叠或者相邻
    # 水平方向相接
    horizontal_adjacent = (x1_right == x2_left or x1_left == x2_right) and (y1_top < y2_bottom and y1_bottom > y2_top)
    
    # 垂直方向相接
    vertical_adjacent = (y1_bottom == y2_top or y1_top == y2_bottom) and (x1_left < x2_right and x1_right > x2_left)
    
    return horizontal_adjacent or vertical_adjacent

def adjust_rectangle(rect, target_rect):
    """
    将不相接的矩形调整到与target_rect相接。
    """
    x1_left, y1_top = rect['left']
    x1_right, y1_bottom = rect['right']
    
    x2_left, y2_top = target_rect['left']
    x2_right, y2_bottom = target_rect['right']
    
    # 水平调整
    if x1_right <= x2_left:
        # rect 在 target_rect 的左边，右移使其相接
        shift_x = x2_left - x1_right
        rect['left'][0] += shift_x
        rect['right'][0] += shift_x
    elif x1_left >= x2_right:
        # rect 在 target_rect 的右边，左移使其相接
        shift_x = x2_right - x1_left
        rect['left'][0] += shift_x
        rect['right'][0] += shift_x
    
    # 垂直调整
    if y1_bottom <= y2_top:
        # rect 在 target_rect 的上面，向下移动
        shift_y = y2_top - y1_bottom
        rect['left'][1] += shift_y
        rect['right'][1] += shift_y
    elif y1_top >= y2_bottom:
        # rect 在 target_rect 的下面，向上移动
        shift_y = y2_bottom - y1_top
        rect['left'][1] += shift_y
        rect['right'][1] += shift_y

def ensure_adjacency(rectangles):
    """
    检查每个矩形是否至少与另一个矩形相接，如果没有相接则进行调整。
    """
    n = len(rectangles)
    
    # 遍历每个矩形
    for i in range(n):
        is_connected = False
        for j in range(n):
            if i != j and is_adjacent(rectangles[i], rectangles[j]):
                is_connected = True
                break
        
        # 如果矩形不相接，调整其位置与最近的矩形相接
        if not is_connected:
            for j in range(n):
                if i != j:
                    adjust_rectangle(rectangles[i], rectangles[j])
                    break
    
    return rectangles