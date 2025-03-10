import os
import openai
from openai import OpenAI
import argparse
import re
import json
from utils.json_process import *
from utils.background_projection import calcuate_background_box, process_boxes, visualization
from utils.placement_rules import*
from retrieve_obj import*
from diffusers import StableDiffusionPipeline
import torch
from reco import create_reco_prompt

def parse_arguments():
    parser = argparse.ArgumentParser(description='Generate 3D stage design from text')
    parser.add_argument('--text', type=str, required=True, help='Input text description')
    parser.add_argument('--openai_api_key', type=str, required=True, help='OpenAI API key')
    parser.add_argument('--output_dir', type=str, required=True, help='Output directory')
    return parser.parse_args()

def scene_list_generator(scripts,client):
    scene_list_prompt = f"""
    Task:You are an expert in analyzing stage scripts. Read the following script and split its content into two parts:
    1.scene descriptions: Extract detailed descriptions of the specific scenes, environments, objects, characters, their actions, and spatial information mentioned in the script. Focus on visual elements, physical spaces, and spatial relationships.
    2.imagery descriptions: Summarize the overarching imagery, emotional tone, atmosphere, and themes conveyed by the script. Focus on high-level concepts, emotions, symbolic meanings, and implicit messages that can inform the creation of prompts for Stable Diffusion after further processing.
    
    Scripts:{scripts}
    
    Requirements:
    1.Clear Separation: Distinct Sections: Separate the output into two clearly labeled sections:"1. scene descriptions:" "2. overall imagery descriptions:"
    2. No Overlap: Ensure that content specific to one section does not appear in the other.
    3.For scene descriptions:
        Extract specific descriptions of physical settings, environments, objects, characters, and their actions.
        Include Spatial Information: Note the positioning, orientation, and spatial relationships between objects and characters.
        Describe the layout of the environment, such as distances, directions, and relative locations.
        Include sensory details like sights, sounds, smells, textures, and movements as described in the script.
        Direct Quotes: Use wording from the script where appropriate, but feel free to add paraphrase for clarity.
        Exclusions: Do not include interpretations, emotions, or abstract concepts in this section.
    4. For imagery Descriptions:
        First Sentence Summary: Start with one sentence summarizing the whole scene succinctly to provide a clear overall understanding.
        High-Level Concepts: Summarize the general mood, emotions, themes, and atmosphere conveyed by the script in an abstract manner. Focus on overarching ideas and symbolic meanings that capture the essence of the script.
        Emotional Tone: Capture the overall feelings or emotional responses that the script is intended to evoke (e.g., hope, despair, tranquility).
        Avoid Specifics: Do not include detailed descriptions of visual elements or specific objects.
        Keep the language abstract to allow for flexibility in further processing.
        Exclusions: Do not include specific physical details or actions from the scene descriptions.
    Detail Extraction:
        Comprehensive Coverage: Ensure all relevant elements from the script are captured in their respective sections.
        Prioritize Relevance: Focus on details that significantly contribute to understanding the scene or the overall themes and emotions.
        
    Output Format:
    Provide the final list of description in the following JSON format:
    [
        {{
            "scene_descriptions": "the description",
            "imagery_descriptions": "the description"       
        }}
    ]
    """
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role":"user", "content":scene_list_prompt},
        ],
        temperature = 0.7,
        max_tokens=2048,
        top_p=1.0,
        frequency_penalty=0.0,
        presence_penalty=0.0,
        stop="Condition:",
        n=1, 
    )

    return response.choices[0].message.content

def anchor_generater(scripts,client):
    foreground_anchor_prompt = f"""
    Task:
    You are an expert in creating 3D stage foregrounds based on a script.
    The stage's floor is considered as a 1000×1000 square cms x-y plane with the top-left corner at (0, 0) and the bottom-right corner at (999, 999), where the y-coordinate increases downward.
    The stage's height (z-axis) ranges from 0 to 999. Note: the unit for the coordinates is cm.

    Please analyze the following script to predict the anchor entities (the most important entities in the stage that could be decorated by other ornaments) that should be included in the stage foreground.

    Scripts: {scripts}

    Requirements:
        1. The stage is totally empty at beginning. Ensure entities contribute to the overall atmosphere of the script. The entities can be artificially created, sourced from nature, or imagined.
        2. List entities in descending order of importance. Separate the entities into groups that will exist together in the stage, such as a bed and two nightstands. 
           For those entities that are unrelated with each other, put them in different groups. For each group, you should determine only one anchor entities.
           For example, if you want to generate a window on the wall, the wall will be anchor. The window, door and inpainting cannot serve as an anchor since it cannot exist independently. Do not generate rug as non-anchor entity which place under other entity. 
        3. Provide detailed descriptions for each entity, including materials, colors, textures, and design styles.
        4. Provide every entities' a reasonable dimensions [length(cm), width(cm), height(cm)] in cm and ensure that the dimensions are as closely as possible to real-world size relationships. keeping in mind the 1000×1000 square cms room area.
        5. Append an index to each entity's name, for example: if there are two lazy sofas and an armchair, list them as: [lazy_sofa1, lazy_sofa2, armchair1].
    For anchor entities:
        1.Conforming to their dimensions and functionality, and arrange anchors' positions (the top-left and bottom-right coordinates: [x_left, y_left], [x_right, y_right]).
        2.The anchors' bounding boxes must not overlap with each other.
        3.Assign a reasonable height [h_low, h_high] (h_high < 500) to each item based on its type and function. If items are placed on top of each other (e.g., a lamp on a table), their h coordinates should reflect this to show they are connected.
    For non-anchor entities:
        Inside every group, decide a placement_rule for non-anchor entities:
        (1) "place_beside()" which places the entity beside the anchor like a nightstand beside a bed.
        (2) "place_top()" which directly places the entity on top of the anchor, like placing a vodka bottle on a table.
        (3) "place_attach(h_low, h_high)" which attachs the entity to the surface of anchor, the entity's bottom at h_low (h_low>=anchor's h_low) and top at h_high (h_high<=anchor's h_high), like placing a clock on the house_wall.
        For "place_top" and "place_attach" the entity's lenght and width must less than anchor's. For "place_attach" the entity has a small width (length > width)
    Output Format and Example:
    Provide the final list of entities in the following JSON format:
    [
        {{
            "anchor_entity": {{
                "name": "left_wall",
                "description": "The left wall of the room, painted white.",
                "dimensions": [15, 999, 300],
                "left": [0, 0],
                "right": [15, 999],
                "h": [0, 300]
            }},
            "non_anchor_entities": [
                {{
                    "name": "window1",
                    "description": "A French-style window with white-painted wooden frames and transparent glass panes. The window is symmetrically divided into four sections.",
                    "dimensions": [150, 15, 150],
                    "placement_rule": "place_attach(250)"
                }}
            ]
        }}        
    ]        
    Note: Please use the output example as a reference for the expected format, but do not include this example in your final response.
    """

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role":"user", "content":foreground_anchor_prompt},
        ],
        temperature = 0.7,
        max_tokens=2048,
        top_p=1.0,
        frequency_penalty=0.0,
        presence_penalty=0.0,
        stop="Condition:",
        n=1, 
    )

    return response.choices[0].message.content

def ornament_generator(scripts, anchor_entities, client):
    foreground_ornament_prompt = f"""
    Task:
    You are an expert in creating 3D stage foregrounds based on a script.
    The stage's floor is considered as a 1000×1000 square cms x-y plane with the top-left corner at (0, 0) and the bottom-right corner at (999, 999), where the y-coordinate increases downward.
    The stage's height (z-axis) ranges from 0 to 999. Note: the unit for the coordinates is cm.

    Please analyze the following script to predict the ornaments that should decorate those anchor entities.

    Scripts: {scripts}
    Requirements:
    1. Ornament List:
        Enumerate all the ornaments in this stage. Anchor entities include:{anchor_entities}. Any objects beside anchor entities are considered ornaments.
        Generate as many ornaments as you can, and be CREATIVE with the ornaments. You can generate any ornament and any weird ornaments are welcome but do not generate rug as ornament.
        Append an index to each ornament's name, for example: if there are two vase and an inpainting, list them as: [vase1, vase2, inpainting1].
    2. Provide detailed descriptions for each ornament, including materials, colors, textures, and design styles. Example: "An arched structure representing the castle's architecture, with stone-like textures and a dark color"
    3. For each ornament, provide its dimensions (length, width, and height) in cm and ensure that the dimensions are as closely as possible to real-world size relationships. Keeping in mind the 1000×1000 square cms room area.
    4. Ornament Placements: 
    For each ornament, provide its placement rule in the scene; below are the rules that you can use:
        (1) "place_center()" which places the ornament at the center of available spaces in the room.
        (2) "place_corner()" which places the ornament at a corner.
        (3) "place_beside(anchor)" which places the ornament beside an existing anchor in the given list above, like placing a vase beside a TV stand.
        (4) "place_top(anchor)" which places the ornament on top of an existing anchor in the given list above with a buffer distance of x cm, like placing a vodka bottle on a table.
        (5) "place_attach(h_low, h_high, anchor)" which attachs the entity to the surface of anchor in the given list above, the entity's bottom at h_low (h_low>=anchor's h_low) and top at h_high (h_high<=anchor's h_high), like placing a clock on the house_wall.
    For "place_top" and "place_attach" the ornament's length and width must less than anchor's length and width.
    Output Format and Example:
    Provide the final list of entities in the following JSON format:
    [
        {{
        "name": "vase1",
        "description": "A modern ceramic vase with a slender body, featuring abstract geometric patterns in gray and white. Its shape is curvy.",
        "dimensions": [60, 60, 80],
        "placement_rule": "place_beside(table1)"
        }},
        {{
        "name": "statue1",
        "description": "A small marble statue of a seated figure with smooth contours and minimalist details.",
        "dimensions": [100, 90, 120],
        "placement_rule": "place_corner()"
        }}
    ]    
    Note: Please use the output example as a reference for the expected format, but do not include this example in your final response.
    """
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role":"user", "content":foreground_ornament_prompt},
        ],
        temperature = 0.7,
        max_tokens=2048,
        top_p=1.0,
        frequency_penalty=0.0,
        presence_penalty=0.0,
        stop="Condition:",
        n=1, 
    )

    return response.choices[0].message.content

def background_generator(imagery_descriptions, foreground_entities, bounding_boxes, client):
    background_prompt = f"""
    Task:
    You are an imaginative expert in creating stage backdrops. The stage backdrop is defined as a 1000x1000 cm canvas, with the top-left corner at (0,0) and the bottom-right corner at (999,999), where the y-coordinate increases downward.
    Please analyze the following script and corresponding imagery descriptions to predict a suitable scene description for the stage backdrop.

    imagery descriptions:{imagery_descriptions}
    Requirements:

    1.Avoid Foreground Entities and Bounding Boxes:
        Entities: {foreground_entities}
        Bounding Boxes: {bounding_boxes}
        The bounding box coordinates [x1, y1, x2, y2] represent the top-left (x1, y1) and bottom-right (x2, y2) corners of each entity's bounding box.
    2.Scene Creativity and Inspiration:
        Generate an imaginative scene description to enhance the overall atmosphere inspired by the imagery descriptions, but not limited to it. Feel free to explore unconventional ideas.
        Avoid using the same entities present in the foreground. The scene should introduce distinct, describable objects (natural, artificial, or imaginary).
    3.Entity Characteristics:
        Use the entity that you think best reflects the atmosphere described in imagery descriptions. Entities should not be abstract concepts and must be visually representable, and use entities that you think
        Scene descriptions should emphasize the overall atmosphere, avoiding a direct reproduction of script objects.
    4.Spatial Arrangement:
        Ensure that entities in the scene description do not overlap with the bounding boxes of foreground entities.
        Arrange all new entities logically within the canvas.
    Output Constraints:
        Keep the scene description under 100 words.
        Ensure the order of the coordinates array matches the order of entities description array to avoid confusion.
        Return the scene description followed by the coordinates and names of the new entities in the json format below.
    Output Example:
    [
        {{
            "scene_description": "A serene garden with two glowing lanterns and koi fish swimming beneath water lilies.",
            "entities_description": ["blue glowing lantern", "yellow glowing lantern","koi fish under water lily"],
            "coordinates": [[50, 50, 150, 150], [200, 312, 333, 422], [540, 728, 663, 956]]
        }}
    ]
    Note: Please use the output example as a reference for the expected format, but do not include this example in your final response.
    """
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role":"user", "content":background_prompt},
        ],
        temperature = 0.7,
        max_tokens=2048,
        top_p=1.0,
        frequency_penalty=0.0,
        presence_penalty=0.0,
        stop="Condition:",
        n=1, 
    )

    return response.choices[0].message.content


def extract_non_digit(text):
    for i, char in enumerate(text):
        if char.isdigit():
            return text[:i]  
    return text  


def initialize_models():
    pipe = StableDiffusionPipeline.from_pretrained(
        "j-min/reco_sd14_laion", 
        torch_dtype=torch.float32,
        use_safetensors=False  
    ).to("cuda")

    clip_model, _, clip_preprocess = open_clip.create_model_and_transforms(
        "ViT-L-14", pretrained="laion2b_s32b_b82k"
    )
    clip_tokenizer = open_clip.get_tokenizer("ViT-L-14")

    sbert_model = SentenceTransformer("all-mpnet-base-v2", device="cpu")

    object_retriever = ObjathorRetriever(
        clip_model=clip_model,
        clip_preprocess=clip_preprocess,
        clip_tokenizer=clip_tokenizer,
        sbert_model=sbert_model,
        retrieval_threshold=50 
    )

    return pipe, object_retriever

def main(args):
    
    os.makedirs(args.output_dir, exist_ok=True)

    client = OpenAI(api_key=args.openai_api_key)

    pipe, object_retriever = initialize_models()

    scene_list = scene_list_generator(args.text, client)
    scene_list = extract_json(scene_list)
    with open(os.path.join(args.output_dir, 'scene_list.json'), "w", encoding='utf-8') as f:
        json.dump(scene_list, f, ensure_ascii=False, indent=4)

    scene_data = scene_list[0]
    scene_descriptions = scene_data['scene_descriptions']
    imagery_descriptions = scene_data['imagery_descriptions']

    anchor_text = anchor_generater(scene_descriptions, client)
    anchor_text = extract_json(anchor_text)
    with open(os.path.join(args.output_dir, 'anchor_text.json'), "w", encoding='utf-8') as f:
        json.dump(anchor_text, f, ensure_ascii=False, indent=4)

    anchor_list = [item["anchor_entity"] for item in anchor_text]

    ornament_text = ornament_generator(scene_descriptions, json.dumps(anchor_list), client)
    ornament_text = extract_json(ornament_text)
    with open(os.path.join(args.output_dir, 'ornament_text.json'), "w", encoding='utf-8') as f:
        json.dump(ornament_text, f, ensure_ascii=False, indent=4)

    foreground_text = layout(anchor_text, ornament_text)
    with open(os.path.join(args.output_dir, 'foreground_layout.json'), "w", encoding='utf-8') as f:
        json.dump(foreground_text, f, ensure_ascii=False, indent=4)

    fore2back_layout = []
    foreground_entities_name = []
    for entity in foreground_text:
        fore2back_layout.append(calcuate_background_box(entity['position']))
        foreground_entities_name.append(entity['name'])
    
    fore2back_layout = process_boxes(fore2back_layout)

    prompt2reco = background_generator(
        imagery_descriptions, 
        foreground_entities_name,
        fore2back_layout,
        client
    )
    prompt2reco = extract_json(prompt2reco)
    with open(os.path.join(args.output_dir, 'prompt2reco.json'), "w", encoding='utf-8') as f:
        json.dump(prompt2reco, f, ensure_ascii=False, indent=4)

    for entity in foreground_text:
        candidates = object_retriever.retrieve(
            [f"a 3D model of {extract_non_digit(entity['name'])}, {entity['description']}"],
            threshold=27
        )
        entity['asset_id'] = random.choice(candidates[:10])[0] if candidates else ""

    with open(os.path.join(args.output_dir, 'final.json'), 'w', encoding='utf-8') as f:
        json.dump(foreground_text, f, indent=4, ensure_ascii=False)

    if prompt2reco:
        caption = prompt2reco[0]['scene_description']
        phrases = prompt2reco[0]['entities_description']
        boxes = prompt2reco[0]['coordinates']
        
        prompt = create_reco_prompt(caption, phrases, boxes, normalize_boxes=False)
        generated_image = pipe(prompt, guidance_scale=4).images[0]
        generated_image.save(os.path.join(args.output_dir, 'reco.png'))

    print(f"All files saved to {args.output_dir}")
        
if __name__ == '__main__':
    args = parse_arguments()
    main(args)