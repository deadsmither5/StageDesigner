import re
import json

def extract_json(text):
    json_data_match = re.search( r'\[\s*{.*}\s*\]', text, re.DOTALL)

    if json_data_match:
        json_data_str = json_data_match.group()
        try:
            json_data = json.loads(json_data_str)
            return json_data
        except json.JSONDecodeError as e:
            print("json error", e)
    else:
        print("didn't find json")
        
        
def get_anchor(data):
    anchors = [item["anchor_entity"] for item in data]
    return anchors
        
def anchor_angle(anchor_entities):
    for anchor in anchor_entities:
        if (anchor["left"][0] + anchor["right"][0]) > 340:
            anchor["ang"] = "left"
        elif (anchor["left"][0] + anchor["right"][0]) < 340:
            anchor["ang"]  = "right"
        else: anchor["ang"] = "front"
    return anchor_entities  

if __name__ =="__main__":
    text = """
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
                "placement_rule": "place_beside(60)"
            },
            {
                "name": "chair2",
                "description": "Another simple wooden chair identical to chair1, placed nearby to suggest a comfortable reading or conversational area.",
                "dimensions": [50, 50, 100],
                "placement_rule": "place_beside(70)"
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
    json_data = extract_json(text)
    anchor = get_anchor(json_data)
    print(anchor)     
    anchor = anchor_angle(anchor)
    print(anchor)