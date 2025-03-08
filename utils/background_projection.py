import numpy as np
import math
"""
------------>  x assume audience are at corner, sight will be extension cord of the stage diagonal. once break the rule there will be audience who can't 
|              see the full stage.
|
|
|
v
y
"""
"object: [x_left, y_left, x_right, y_right, h_low, h_high] , background: [[x_b_left, y_b_left], [x_b_right, y_b_right],[0, h_b]],stage: [x,y,h]"
def calcuate_background_box(object, background = [[0,0],[999,999],[0,999]], stage = [999,999,999]):
    tan_left = (stage[0] - object[0]) / (stage[1] - object[3] + 200) # from right to left, audience is 200 cm away from the stage axis-y, x is the same with stage
    tan_right = object[2] / (stage[1] - object[3] + 200) # from left to right
    left_proj = math.floor(max(background[0][0], object[0] - object[3] * tan_left)) # make sure projecton in the background range
    right_proj = math.ceil(min(background[1][0], object[2] + object[3] * tan_right))# make sure projection in the background range
    # print("check-----------")
    # print(tan_left)
    # print(tan_right)
    h_low = stage[2] - object[4] #transform into the background y coordinate
    h_high = stage[2] - object[5] #transform into the background y coordinate
    return [left_proj,h_high,right_proj,h_low]

def is_contained(box1, box2):
    """判断 box1 是否被 box2 完全包含"""
    return (
        box1[0] >= box2[0] and box1[1] >= box2[1] and
        box1[2] <= box2[2] and box1[3] <= box2[3]
    )

def filter_contained_boxes(boxes):
    """去除被完全包含的 box"""
    result = []
    for i, box1 in enumerate(boxes):
        contained = False
        for j, box2 in enumerate(boxes):
            if i != j and is_contained(box1, box2):
                contained = True
                break
        if not contained:
            result.append(box1)
    return result

def merge_boxes(box1, box2):
    """合并两个 box"""
    x1 = min(box1[0], box2[0])
    y1 = min(box1[1], box2[1])
    x2 = max(box1[2], box2[2])
    y2 = max(box1[3], box2[3])
    return [x1, y1, x2, y2]


def split_box(box1, box2):
    """分割两个 box 使重叠部分保留非重叠区域"""
    if box2[0]> box1[0] and box2[2]< box1[2]:
        if box2[1] > box1[1]:
            return [box2[0],box1[3],box]
        
    return [box1]

def is_overlap(box1, box2):
    """判断两个 box 是否有重叠"""
    return not (
        box1[2] <= box2[0] or  # box1 的右边在 box2 的左边
        box1[0] >= box2[2] or  # box1 的左边在 box2 的右边
        box1[3] <= box2[1] or  # box1 的底边在 box2 的顶边
        box1[1] >= box2[3]     # box1 的顶边在 box2 的底边
    )

def process_boxes(boxes):
    boxes = filter_contained_boxes(boxes)  # 先过滤完全包含的 box
    changed = True  # 用于跟踪是否有合并或分割发生

    while changed:  # 继续循环，直到没有任何改变
        changed = False  # 假设本轮没有操作发生
        new_boxes = []  # 存放新一轮处理后的 box

        while boxes:
            box1 = boxes.pop(0)  # 取出第一个 box
            merged = False
            for i, box2 in enumerate(boxes):
                if ((box1[0] == box2[2] or box1[2] == box2[0]) and box1[1] == box2[1] and box1[3] == box2[3]) or ((box1[1] == box2[3] or box1[3] == box2[1]) and box1[0] == box2[0] and box1[2] == box2[2]):#贴边合并
                    new_box = merge_boxes(box1, box2)
                    boxes.pop(i)
                    boxes.insert(0, new_box)  # 新合并的 box 放回队列头
                    merged = True
                    break
                if is_overlap(box1, box2):  # 判断是否有重叠
                    # 情况 1 和 2：x 或 y 方向重叠且坐标相同，合并
                    if (box1[0] == box2[0] and box1[2] == box2[2]) or (box1[1] == box2[1] and box1[3] == box2[3]):                   
                        new_box = merge_boxes(box1, box2)
                        boxes.pop(i)  # 移除已合并的 box2
                        boxes.insert(0, new_box)  # 将新合并的 box 放回队列头
                        merged = True
                        changed = True  # 标记本轮发生了改变
                        break
            if not merged:
                new_boxes.append(box1)  # 没有合并的 box 放入新列表

        boxes = new_boxes  # 更新为本轮处理后的 box
        boxes = filter_contained_boxes(boxes) #结束合并后再次检测是否有包含并更新
        
    return boxes

def visualization(objects,number):
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    # 创建画布
    fig, ax = plt.subplots(figsize=(10, 10))

    # 遍历所有box并绘制矩形
    for i, (x_left, y_left, x_right, y_right) in enumerate(objects):
        width = x_right - x_left
        height = y_right - y_left
        # 创建矩形
        rect = patches.Rectangle((x_left, y_left), width, height, 
                                linewidth=2, edgecolor='r', facecolor='none')
        ax.add_patch(rect)
        # 为每个box标注序号
        ax.text(x_left, y_left, f'{i+1}', fontsize=12, color='blue')

    # 设置图像显示区域
    ax.set_xlim(0, 1000)
    ax.set_ylim(0, 1000)
    ax.set_aspect('equal')

    # 保存图片
    plt.savefig(f"background_visualization{number}.png", dpi=300)
    plt.close()

if __name__ == "__main__":
    bounding_box = calcuate_background_box([250,300,300,400,12,30],[[0,0],[512,512],[0,512]],[512,512,512])
    print("Bounding Box:", bounding_box)
    # 输入数据
    objects = [
         [0, 924, 999, 999], [0, 819, 669, 999],
        [445, 819, 999, 999], [0, 749, 371, 949], [316, 779, 526, 999],
        [0, 899, 999, 999], [0, 899, 999, 999], [294, 901, 999, 924],
        [186, 954, 999, 999], [0, 949, 999, 999]
    ]

    # # 分割并合并objects
    # objects = process_boxes(objects)

    # # 打印结果
    # print("处理后的box:")
    # for box in objects:
    #     print(box)

