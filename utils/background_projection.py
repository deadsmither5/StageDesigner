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
    return (
        box1[0] >= box2[0] and box1[1] >= box2[1] and
        box1[2] <= box2[2] and box1[3] <= box2[3]
    )

def filter_contained_boxes(boxes):
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
    x1 = min(box1[0], box2[0])
    y1 = min(box1[1], box2[1])
    x2 = max(box1[2], box2[2])
    y2 = max(box1[3], box2[3])
    return [x1, y1, x2, y2]


def split_box(box1, box2):
    if box2[0]> box1[0] and box2[2]< box1[2]:
        if box2[1] > box1[1]:
            return [box2[0],box1[3],box]
        
    return [box1]

def is_overlap(box1, box2):
    return not (
        box1[2] <= box2[0] or  
        box1[0] >= box2[2] or  
        box1[3] <= box2[1] or  
        box1[1] >= box2[3]     
    )

def process_boxes(boxes):
    boxes = filter_contained_boxes(boxes)
    changed = True  

    while changed:  
        changed = False  
        new_boxes = []  

        while boxes:
            box1 = boxes.pop(0)  
            merged = False
            for i, box2 in enumerate(boxes):
                if ((box1[0] == box2[2] or box1[2] == box2[0]) and box1[1] == box2[1] and box1[3] == box2[3]) or ((box1[1] == box2[3] or box1[3] == box2[1]) and box1[0] == box2[0] and box1[2] == box2[2]):
                    new_box = merge_boxes(box1, box2)
                    boxes.pop(i)
                    boxes.insert(0, new_box)  
                    merged = True
                    break
                if is_overlap(box1, box2):  
                    if (box1[0] == box2[0] and box1[2] == box2[2]) or (box1[1] == box2[1] and box1[3] == box2[3]):                   
                        new_box = merge_boxes(box1, box2)
                        boxes.pop(i)  
                        boxes.insert(0, new_box)  
                        merged = True
                        changed = True  
                        break
            if not merged:
                new_boxes.append(box1)  

        boxes = new_boxes  
        boxes = filter_contained_boxes(boxes) 
        
    return boxes

def visualization(objects,number):
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches

    fig, ax = plt.subplots(figsize=(10, 10))

    for i, (x_left, y_left, x_right, y_right) in enumerate(objects):
        width = x_right - x_left
        height = y_right - y_left
        rect = patches.Rectangle((x_left, y_left), width, height, 
                                linewidth=2, edgecolor='r', facecolor='none')
        ax.add_patch(rect)
        ax.text(x_left, y_left, f'{i+1}', fontsize=12, color='blue')

    ax.set_xlim(0, 1000)
    ax.set_ylim(0, 1000)
    ax.set_aspect('equal')

    plt.savefig(f"background_visualization{number}.png", dpi=300)
    plt.close()

if __name__ == "__main__":
    bounding_box = calcuate_background_box([250,300,300,400,12,30],[[0,0],[512,512],[0,512]],[512,512,512])
    print("Bounding Box:", bounding_box)
    objects = [
         [0, 924, 999, 999], [0, 819, 669, 999],
        [445, 819, 999, 999], [0, 749, 371, 949], [316, 779, 526, 999],
        [0, 899, 999, 999], [0, 899, 999, 999], [294, 901, 999, 924],
        [186, 954, 999, 999], [0, 949, 999, 999]
    ]
    objects = process_boxes(objects)
    for box in objects:
        print(box)

