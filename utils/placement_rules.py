import numpy as np
import random
import json
import pdb
import re
import math

# 定义三维物体或区域的边界矩形类，用于表示物体的边界
class Rectangle:
    def __init__(self, x_left, y_left, x_right, y_right, height_low, height_high, name=None, orientation='front', description=None):
        self.x_left = x_left
        self.y_left = y_left
        self.x_right = x_right
        self.y_right = y_right
        self.height_low = height_low
        self.height_high = height_high
        self.name = name
        self.orientation = orientation  # 默认朝向
        self.surface_collision_maps = {
            'front_surface': None,
            'left_surface': None,
            'right_surface': None,
            'top_surface': None
        }  # 各表面的碰撞检测图
        self.description = description
    # 检查当前矩形是否与另一个矩形重叠（包括高度）
    def is_overlapping(self, other):
        if self.x_right <= other.x_left or self.x_left >= other.x_right:
            return False
        if self.y_right <= other.y_left or self.y_left >= other.y_right:
            return False
        # 检查高度是否重叠
        if self.height_high <= other.height_low or self.height_low >= other.height_high:
            return False
        return True

    # 获取矩形的边界
    def get_bounding_box(self):
        return [self.x_left, self.y_left, self.x_right, self.y_right, self.height_low, self.height_high]

def anchor_angle(anchor):
    if (anchor["left"][0] + anchor["right"][0]) / 2 > 950:
        return "left"
    elif (anchor["left"][0] + anchor["right"][0]) / 2 < 250:
        return "right"
    return "front"

# 解析输入数据，生成锚定物体和非锚定物体的列表
def parse_anchor_prompt_data(text, collision_map):
    entities = json.loads(text)
    anchor_entities = []
    non_anchor_entities = []

    for item in entities:
        # 解析anchor实体
        anchor_data = item["anchor_entity"]
        anchor_rect = Rectangle(
            x_left = anchor_data["left"][0],
            y_left = anchor_data["left"][1],
            x_right = anchor_data["right"][0],
            y_right = anchor_data["right"][1],
            height_low = anchor_data["h"][0],
            height_high = anchor_data["h"][1],
            name = anchor_data["name"],
            orientation = anchor_angle(anchor_data),
            description = anchor_data['description']
        )
        anchor_entities.append(anchor_rect)

        # 初始化每个表面的碰撞图（根据锚定物体的高度和宽度）(y,x)
        anchor_rect.surface_collision_maps['front_surface'] = initialize_collision_map(
            anchor_rect.height_high - anchor_rect.height_low, anchor_rect.x_right - anchor_rect.x_left)
        anchor_rect.surface_collision_maps['left_surface'] = initialize_collision_map(
            anchor_rect.height_high - anchor_rect.height_low, anchor_rect.y_right - anchor_rect.y_left)
        anchor_rect.surface_collision_maps['right_surface'] = initialize_collision_map(
            anchor_rect.height_high - anchor_rect.height_low, anchor_rect.y_right - anchor_rect.y_left)
        anchor_rect.surface_collision_maps['top_surface'] = initialize_collision_map(
            anchor_rect.y_right - anchor_rect.y_left, anchor_rect.x_right - anchor_rect.x_left
        )
        #更新anchor在floor的碰撞图
        update_collision_map(collision_map, anchor_rect.x_left, anchor_rect.y_left, anchor_rect.x_left - anchor_rect.x_right, anchor_rect.y_right - anchor_rect.y_left)
        # 解析非锚定实体
        non_anchors = item.get("non_anchor_entities", [])
        for non_anchor in non_anchors:
            non_anchor["anchor_name"] = anchor_data["name"]  # 添加锚定物体名称
            non_anchor_entities.append(non_anchor)

    return anchor_entities, non_anchor_entities

def parse_ornament_prompt_data(text, non_anchor_entities):
    entities = json.loads(text)
    for item in entities:
        # 解析非锚定实体
        if any(rule in item['placement_rule'] for rule in ['place_beside', 'place_top']):
            item["anchor_name"] = item['placement_rule'].split('(')[1].split(')')[0]  # 添加锚定物体名称
        elif 'place_attach' in item['placement_rule']:
            content = item['placement_rule'][item['placement_rule'].find('(') + 1 : item['placement_rule'].rfind(')')]    
            parts = [part.strip() for part in content.split(',')]
            item["anchor_name"] = parts[2]
        else:
            item["anchor_name"] = None   
        non_anchor_entities.append(item)

    return non_anchor_entities

# 初始化一个矩形区域的表面碰撞图（height, width）
def initialize_collision_map(height, width):
    return np.zeros((height, width), dtype=np.uint8)  # 0 表示可用区域，1 表示已被占用

def is_valid_position(x, y, h, w, collision_map):#3d 里面h代表x轴 map(y,x)
    if x is None or y is None or h <= 0 or w <= 0:
        return False
    # 边界检查，防止索引越界
    if not (0 <= y < collision_map.shape[0] and 0 <= x < collision_map.shape[1]):
        return False
    if not (0 <= y + w < collision_map.shape[0] and 0 <= x + h < collision_map.shape[1]):
        return False

    # 检查指定位置是否在边界外或被占用 (1 表示已被占用)
    if 1 in collision_map[max(0, y):min(collision_map.shape[0], y + w),
                          max(0, x):min(collision_map.shape[1], x + h)]:
        return False
    # 检查指定位置是否为空（0 表示可用）
    return np.all(collision_map[y:y + w, x:x + h] == 0)

# 更新碰撞图：标记物体在某个位置的占用情况
def update_collision_map(collision_map, x, y, h, w):
    """
    更新碰撞图，在指定的局部坐标系位置标记物体区域为占用状态（1表示已占用）。
    :param collision_map: 表面的碰撞检测图
    :param y: 局部表面坐标系中的起始y坐标
    :param x: 局部表面坐标系中的起始x坐标
    :param h: 物体在表面上的高度
    :param w: 物体在表面上的宽度
    :param buffer: 缓冲区大小，用于确保物体与其他物体或边界的间距
    """
    x = min(999, max(0, math.ceil(x)))
    y = min(999, max(0, math.ceil(y)))
    h = min(999, max(0, math.ceil(h)))
    w = min(999, max(0, math.ceil(w)))
    # 边界检查，防止更新时越界
    collision_map[max(0, y):min(collision_map.shape[0], y + w),
                  max(0, x):min(collision_map.shape[1], x + h)] = 1  # 1 表示占用

# 定义物体的放置策略，返回非锚定物体的最终位置, 考虑要不要一层一层的递归往上，其实感觉没有必要叠太多, 如果要递归，第一层anchor就可以设置成floor(0,0, 999,999, 0, 0)，
def place_entity(anchor, entity, collision_map):
    anchor_x_left, anchor_y_left, anchor_x_right, anchor_y_right, anchor_height_low, anchor_height_high = anchor.get_bounding_box()
    entity_length, entity_width, entity_height = entity['dimensions']#长是横着的对应x轴，宽是竖着的对应y轴

    if "place_beside" in entity["placement_rule"]:
        surfaces = ['front', 'left', 'right']
        
        search_area_back = anchor_y_left - 150  
        search_area_front = anchor_y_right + 150  
        search_area_left = anchor_x_left - 150  
        search_area_right = anchor_x_right + 150  

        while surfaces:
            angle = random.choice(surfaces)
            if angle == 'front':
                left_bound = search_area_left - entity_length
                for _ in range(5000):  # 随机采样5000次
                    x_offset = random.randint(0, search_area_right - left_bound)
                    y_offset = random.randint(0, search_area_front - anchor_y_right)
                    place_left = left_bound + x_offset
                    place_back = anchor_y_right + y_offset

                    if is_valid_position(place_left, place_back, entity_length, entity_width, collision_map):
                        update_collision_map(collision_map, place_left, place_back, entity_length, entity_width)
                        return Rectangle(
                            place_left,
                            place_back,
                            place_left + entity_length,
                            place_back + entity_width,
                            anchor_height_low,
                            anchor_height_low + entity_height,
                            name=entity['name'],
                            orientation='front',
                            description=entity['description']
                        )

            elif angle == 'left':
                front_bound = search_area_front + entity_length
                for _ in range(5000):
                    x_offset = random.randint(0, anchor_x_left - search_area_left)
                    y_offset = random.randint(0, front_bound - search_area_back)
                    place_left = anchor_x_left - x_offset - entity_width 
                    place_back = search_area_back + y_offset - entity_length

                    if is_valid_position(place_left, place_back, entity_width, entity_length, collision_map):
                        update_collision_map(collision_map, place_left, place_back, entity_width, entity_length)
                        return Rectangle(
                            place_left,
                            place_back,
                            place_left + entity_width,
                            place_back + entity_height,
                            anchor_height_low,
                            anchor_height_low + entity_height,
                            name=entity['name'],
                            orientation='right',
                            description=entity['description']
                        )

            else:
                back_bound = search_area_back - entity_length
                for _ in range(5000):
                    x_offset = random.randint(0, search_area_right - anchor_x_right)
                    y_offset = random.randint(0, search_area_front - back_bound)
                    place_left = anchor_x_right + x_offset
                    place_back = back_bound + y_offset

                    if is_valid_position(place_left, place_back, entity_width, entity_length, collision_map):
                        update_collision_map(collision_map, place_left, place_back, entity_width, entity_length)
                        return Rectangle(
                            place_left,
                            place_back,
                            place_left + entity_width,
                            place_back + entity_length,
                            anchor_height_low,
                            anchor_height_low + entity_height,
                            name=entity['name'],
                            orientation='left',
                            description=entity['description']
                        )
            
            surfaces.remove(angle)
        
    # 若未找到合适位置，则返回 None
    elif "place_top" in entity["placement_rule"]:
        surface_collision_map = anchor.surface_collision_maps['top_surface']
        MAX_ATTEMPTS = 5000  # 最大采样次数
        surfaces = ['front', 'left', 'right']
        for _ in range(MAX_ATTEMPTS):
            # 在允许的范围内随机采样
            if surfaces == []:
                return None
            orientation = random.choice(surfaces)
            if orientation == 'front':
                x = entity_width
                y = entity_length
                if surface_collision_map.shape[0] - x <0 or surface_collision_map.shape[1] - y <0 :
                    print(anchor.name)
                    print(surface_collision_map.shape[0])
                    print(surface_collision_map.shape[1])
                    surfaces.remove(orientation)
                    continue
            elif orientation == 'left' or orientation == 'right':
                x = entity_length
                y = entity_width
                if surface_collision_map.shape[0] - x <0 or surface_collision_map.shape[1] - y <0 :
                    surfaces.remove(orientation)
                    continue        
            place_back = random.randint(0, surface_collision_map.shape[0] - x)
            place_left = random.randint(0, surface_collision_map.shape[1] - y)
            if is_valid_position(place_left, place_back, y, x, surface_collision_map):
                # 更新碰撞地图
                update_collision_map(surface_collision_map, place_left, place_back, y, x)
                # 返回找到的有效位置
                return Rectangle(
                    place_left + anchor_x_left,
                    place_back + anchor_y_left,
                    place_left + anchor_x_left + y,
                    place_back + anchor_y_left + x,
                    anchor_height_high,
                    anchor_height_high + entity_height,
                    name = entity['name'],
                    orientation = orientation,
                    description = entity['description']
                )
        # 如果在最大尝试次数内没有找到合适位置，返回 None

    elif "place_attach" in entity["placement_rule"]:
        def extract_first_two_numbers(rule):
            # 使用正则表达式提取所有整数
            numbers = re.findall(r'\d+', rule)         
            if len(numbers) < 2:
                raise ValueError("Placement rule must contain at least two integers.")
            # 转换前两个数字为整数
            h_low, h_high = map(int, numbers[:2])
            return h_low, h_high

        h_low, h_high = extract_first_two_numbers(entity["placement_rule"])
        anchor_orientation = getattr(anchor, 'orientation', 'front')
        surfaces = []

        if anchor_orientation == 'front':
            surfaces = ['front_surface', 'left_surface', 'right_surface']
        elif anchor_orientation == 'left':
            surfaces = ['left_surface']
        elif anchor_orientation == 'right':
            surfaces = ['right_surface']

        while surfaces:
            chosen_surface = random.choice(surfaces)
            surface_collision_map = anchor.surface_collision_maps[chosen_surface]
            if surface_collision_map.shape[1] < entity_length:
                surfaces.remove(chosen_surface)
                continue  # 尝试其他表面
            MAX_ATTEMPTS = 5000  # 最大采样次数
            for _ in range(MAX_ATTEMPTS):
                # 随机采样 x_offset 范围
                x_offset = random.randint(0, surface_collision_map.shape[1] - entity_length)
                if chosen_surface == 'front_surface':
                    place_left = x_offset
                    place_back = surface_collision_map.shape[0] - h_high
                    global_x = place_left + anchor_x_left
                    global_y = anchor_y_right + entity_width
                    
                    if is_valid_position(place_left, place_back, entity_length, entity_height, surface_collision_map) and \
                    all(0 <= coord <= 999 for coord in [global_x, global_y, global_x + entity_length, global_y + entity_width]):
                        update_collision_map(surface_collision_map, place_left, place_back, entity_length, entity_height)
                        update_collision_map(collision_map, global_x, global_y, entity_length, entity_width)
                        return Rectangle(global_x, global_y, global_x + entity_length, global_y + entity_width,
                                        h_low, h_high, name=entity['name'], orientation='front', description=entity['description'])

                elif chosen_surface == 'left_surface':
                    place_left = x_offset
                    place_back = surface_collision_map.shape[0] - h_high
                    global_x = anchor_x_left - entity_width
                    global_y = place_left + anchor_y_left

                    if is_valid_position(place_left, place_back, entity_length, entity_height, surface_collision_map) and \
                    all(0 <= coord <= 999 for coord in [global_x, global_y, global_x + entity_width, global_y + entity_length]):
                        update_collision_map(surface_collision_map, place_left, place_back, entity_length, entity_height)
                        update_collision_map(collision_map, global_x, global_y, entity_width, entity_length)
                        return Rectangle(global_x, global_y, global_x + entity_width, global_y + entity_length,
                                        h_low, h_high, name=entity['name'], orientation='left', description=entity['description'])

                elif chosen_surface == 'right_surface':
                    place_left = x_offset
                    place_back = surface_collision_map.shape[0] - h_high
                    global_x = anchor_x_right
                    global_y = place_left + anchor_y_left

                    if is_valid_position(place_left, place_back, entity_length, entity_height, surface_collision_map) and \
                    all(0 <= coord <= 999 for coord in [global_x, global_y, global_x + entity_width, global_y + entity_length]):
                        update_collision_map(surface_collision_map, place_left, place_back, entity_length, entity_height)
                        update_collision_map(collision_map, global_x, global_y, entity_width, entity_length)
                        return Rectangle(global_x, global_y, global_x + entity_width, global_y + entity_length,
                                        h_low, h_high, name=entity['name'], orientation='right', description=entity['description'])

            surfaces.remove(chosen_surface)
            
        return None

def place_corner(entity, collision_map):
    entity_length, entity_width, entity_height = entity['dimensions']
    corner = ['left_back', 'left_front', 'right_back', 'right_front']
    
    if (250 - entity_length <= 0) or (250 - entity_width <= 0):
        print(f"Entity {entity['name']} is too large to fit in the corner area.")
        return None  # 如果无法放置，直接返回 None
    
    while corner:
        chosen_corner = random.choice(corner)
        SEARCH_ATTEMPTS = 5000  # 每个角落采样 1000 次
        for _ in range(SEARCH_ATTEMPTS):
            orientation = random.choice(['front', 'right'])
            if orientation == 'front':
                x = entity_length
                y = entity_width
            else:
                x = entity_width
                y = entity_length
                    
            # 根据角落选择生成随机位置（每个角落范围为 250x250）
            if chosen_corner == 'left_back':
                place_left = random.randint(0, 250 - x)
                place_back = random.randint(0, 250 - y)

            elif chosen_corner == 'left_front':
                place_left = random.randint(0, 250 - x)
                place_back = random.randint(750, 999 - y)

            elif chosen_corner == 'right_back':
                place_left = random.randint(750, 999 - x)
                place_back = random.randint(0, 999 - y)

            else:  # 'right_front'
                place_left = random.randint(750, 999 - x)
                place_back = random.randint(750, 999 - y)

            # 检查当前位置是否有效
            if is_valid_position(place_left, place_back, x, y, collision_map):
                # 更新碰撞地图
                update_collision_map(collision_map, place_left, place_back, x, y)

                # 返回生成的实体矩形对象
                return Rectangle(
                    place_left,
                    place_back,
                    place_left + x,
                    place_back + y,
                    0,
                    0 + entity_height,
                    name=entity['name'],
                    orientation=orientation,
                    description=entity['description']
                )

        # 如果当前角落无法找到合适的位置，则尝试其他角落
        corner.remove(chosen_corner)

    # 如果所有角落都无法找到合适的位置，则返回 None
    return None

def place_center(entity, collision_map):
    entity_length, entity_width, entity_height = entity['dimensions']

    # 检查实体是否能放进 (250, 250) 到 (750, 750) 区域
    if (749 - entity_length <= 250) or (749 - entity_width <= 250):
        print(f"Entity {entity['name']} is too large to fit in the central area.")
        return None  # 如果无法放置，直接返回 None

    SEARCH_ATTEMPTS = 5000  # 在范围内随机尝试 5000 次

    for _ in range(SEARCH_ATTEMPTS):
        # 在 (250, 250) 到 (749 - entity_length, 749 - entity_width) 范围内生成随机位置
        orientation = random.choice(['front', 'left', 'right'])
        if orientation == 'front':
            x = entity_length
            y = entity_width
        elif orientation == 'left'or orientation == 'right':
            x = entity_width
            y = entity_length  
            
        place_left = random.randint(250, 749 - x)
        place_back = random.randint(250, 749 - y)
        # 检查该位置是否有效
        if is_valid_position(place_left, place_back, x, y, collision_map):
            # 更新碰撞地图
            update_collision_map(collision_map, place_left, place_back, x, y)

            # 返回包含位置和尺寸的 Rectangle 对象
            return Rectangle(
                place_left,
                place_back,
                place_left + x,
                place_back + y,
                0,
                entity_height,
                name=entity['name'],
                orientation=orientation,
                description=entity['description']
            )

    # 如果 1000 次尝试后没有找到合适位置，返回 None
    return None

# 放置实体并检查重叠情况
def place_entities(anchor_entities, non_anchor_entities, floor_collision_map, successful_placements):
    # 将锚定物体直接添加到 successful_placements
    for entity in anchor_entities:
        successful_placements.append({
            "name": entity.name,
            "orientation": entity.orientation,
            "position": entity.get_bounding_box(),
            "description": entity.description
        })
    for entity in non_anchor_entities:
        # 查找对应的锚定物体
        anchor_name = entity["anchor_name"]
        anchor = next((a for a in anchor_entities if a.name == anchor_name), None)

        # 放置非锚定物体
        if not anchor:
            if 'place_corner' in entity["placement_rule"]:
                entity_rectangle = place_corner(entity, floor_collision_map)
            elif 'place_center' in entity["placement_rule"]:
                entity_rectangle = place_center(entity, floor_collision_map)
        else:
            entity_rectangle = place_entity(anchor, entity, floor_collision_map)

        if entity_rectangle:
            # 将非锚定物体添加到 successful_placements
            successful_placements.append({
                "name": entity_rectangle.name,
                "orientation": entity_rectangle.orientation,
                "position": entity_rectangle.get_bounding_box(),
                "description": entity_rectangle.description
            })
            entity_rectangle = None
        else:
            print(f"Failed to place {entity['name']}, no available position found.")

    return successful_placements

def layout(anchor_text, ornament_text):
    floor_collision_map = initialize_collision_map(1000, 1000)
    anchor_entities, non_anchor_entities = parse_anchor_prompt_data(anchor_text, floor_collision_map)
    non_anchor_entities = parse_ornament_prompt_data(ornament_text, non_anchor_entities)
    print("anchor_entities:",anchor_entities)
    print("non_anchor_entities",non_anchor_entities)
    # 初始化一个空白的地板碰撞图，0表示可用区域，1表示已被占用
    successful_placements = []
    # 放置实体并更新碰撞检测图
    successful_placements = place_entities(anchor_entities, non_anchor_entities, floor_collision_map, successful_placements)
    # 输出最终结果
    for placement in successful_placements:
        print(f"Placed {placement['name']} at {placement['position']}. description: {placement['description']}")
    return successful_placements    

def main():
    # 输入数据
    anchor_text = """
    [
        {
            "anchor_entity": {
                "name": "background_board",
                "description": "The background board of the room, enclosing the space with a visually appealing design theme. It is white in color and features a smooth, matte texture. This board serves as the foundational element, supporting the placement of other elements like windows and doors.",
                "dimensions": [1024, 30, 300],
                "left": [0, 0],
                "right": [1024, 30],
                "h": [0, 300]
            },
            "non_anchor_entities": [
            {
                "name": "window1",
                "description": "A large French-style window with white-painted wooden frames and transparent glass panes. The window is symmetrically divided into six sections, allowing ample natural light to enter the room and visually connecting the interior with the exterior.",
                "dimensions": [300, 30, 200],
                "placement_rule": "place_attach(50, 250)"
            },
            {
                "name": "door1",
                "description": "A modern-style door with a white-painted wooden frame and a frosted glass center panel, designed to separate the room from an adjacent space. The frosted glass adds a sense of privacy while maintaining a translucent effect.",
                "dimensions": [100, 30, 220],
                "placement_rule": "place_attach(0, 220)"
            }
            ]
        },
        {
            "anchor_entity": {
                "name": "table1",
                "description": "A rectangular wooden table with a polished oak finish, providing a flat and stable surface. The table is placed towards the right side of the room but not directly against the wall, creating a sense of openness in the space.",
                "dimensions": [120, 60, 75],
                "left": [650, 600],
                "right": [770, 660],
                "h": [0, 75]
            },
            "non_anchor_entities": [
                {
                    "name": "chair1",
                    "description": "A simple wooden chair with a soft cushion, designed for reading or writing. The chair features four sturdy legs and a slightly curved backrest for ergonomic support.",
                    "dimensions": [50, 50, 100],
                    "placement_rule": "place_beside()"
                },
                {
                    "name": "chair2",
                    "description": "Another simple wooden chair identical to chair1, placed nearby to suggest a comfortable reading or conversational area.",
                    "dimensions": [50, 50, 100],
                    "placement_rule": "place_beside()"
                },
                {
                    "name": "bottle",
                    "description":"",
                    "dimensions": [12,13,23],
                    "placement_rule": "place_top()"
                }
            ]
        },
        {
            "anchor_entity": {
                "name": "floor_lamp1",
                "description": "A tall, modern-style floor lamp with a black metal frame and a fabric lampshade. The lamp is positioned to the left of the room to create an exaggerated shadow effect, highlighting local details and enhancing the visual layering.",
                "dimensions": [30, 30, 180],
                "left": [150, 700],
                "right": [180, 730],
                "h": [0, 180]
            },
            "non_anchor_entities": []
        },
        {
            "anchor_entity": {
                "name": "floor_lamp2",
                "description": "Another identical floor lamp, placed symmetrically to the right side of the room, balancing the lighting and creating a harmonious ambiance.",
                "dimensions": [30, 30, 180],
                "left": [850, 700],
                "right": [880, 730],
                "h": [0, 180]
            },
            "non_anchor_entities": []
        }
    ]
    """

    ornament_text = """
    [
        {
            "name": "vase1",
            "description": "A modern ceramic vase with a slender body, featuring abstract geometric patterns in gray and white. Its shape is curvy, adding a sense of elegance to the room's simple style.",
            "dimensions": [15, 15, 45],
            "placement_rule": "place_beside(table1)"
        },
        {
            "name": "statue1",
            "description": "A small marble statue of a seated figure with smooth contours and minimalist details. The figure appears to be in a thoughtful pose, aligning with the room's serene atmosphere.",
            "dimensions": [20, 20, 50],
            "placement_rule": "place_corner()"
        }
    ]
    """

    # 解析anchor prompt输入数据
    floor_collision_map = initialize_collision_map(1000, 1000)
    anchor_entities, non_anchor_entities = parse_anchor_prompt_data(anchor_text,floor_collision_map)
    non_anchor_entities = parse_ornament_prompt_data(ornament_text, non_anchor_entities)
    # 初始化一个空白的地板碰撞图，0表示可用区域，1表示已被占用
    successful_placements = []
    # 放置实体并更新碰撞检测图
    place_entities(anchor_entities, non_anchor_entities, floor_collision_map, successful_placements)
    with open('generation_data/test.json', 'w', encoding= 'utf-8') as f:
        json.dump(successful_placements, f, indent=4, ensure_ascii=False)
    # 输出最终结果
    for placement in successful_placements:
        print(f"Placed {placement['name']} at {placement['position']}. Description: {placement['description']}")

if __name__ == "__main__":
    main()

#层次化碰撞检测图