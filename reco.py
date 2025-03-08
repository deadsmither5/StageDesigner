import torch
from diffusers import StableDiffusionPipeline

def create_reco_prompt(
    caption: str = '',
    phrases=[],
    boxes=[],
    normalize_boxes=True,
    image_resolution=512,
    num_bins=1000,
    ):
    """
    method to create ReCo prompt

    caption: global caption
    phrases: list of regional captions
    boxes: list of regional coordinates (unnormalized xyxy)
    """

    SOS_token = '<|startoftext|>'
    EOS_token = '<|endoftext|>'
    
    box_captions_with_coords = []
    
    box_captions_with_coords += [caption]
    box_captions_with_coords += [EOS_token]

    for phrase, box in zip(phrases, boxes):
                    
        if normalize_boxes:
            box = [float(x) / image_resolution for x in box]

        # quantize into bins
        quant_x0 = int(round((box[0] * (num_bins - 1))))
        quant_y0 = int(round((box[1] * (num_bins - 1))))
        quant_x1 = int(round((box[2] * (num_bins - 1))))
        quant_y1 = int(round((box[3] * (num_bins - 1))))
        
        # ReCo format
        # Add SOS/EOS before/after regional captions
        box_captions_with_coords += [
            f"<bin{str(quant_x0).zfill(3)}>",
            f"<bin{str(quant_y0).zfill(3)}>",
            f"<bin{str(quant_x1).zfill(3)}>",
            f"<bin{str(quant_y1).zfill(3)}>",
            SOS_token,
            phrase,
            EOS_token
        ]

    text = " ".join(box_captions_with_coords)
    return text
if __name__ == '__main__': 
    a = [
            {
                "scene description": "An art style serene garden with two glowing lanterns and koi fish swimming beneath water lilies.",
                "entities description": ["red lantern", "yellow glowing lantern","fish under water lily"],
                "coordinates": [[63, 50, 150, 192], [200, 312, 333, 422], [540, 728, 663, 956]]
            }
        ]
        
    caption = a[0]['scene description']
    phrases = a[0]['entities description']
    boxes =  a[0]['coordinates']
    prompt = create_reco_prompt(caption, phrases, boxes, normalize_boxes=False)
    print(prompt)

    pipe = StableDiffusionPipeline.from_pretrained(
        "j-min/reco_sd14_laion", 
        torch_dtype=torch.float32,
        use_safetensors=False  
    ).to("cuda")


    generated_image = pipe(
        prompt,
        guidance_scale=4).images[0]
    generated_image.save("/home/ganzhaoxing/artist/generation_data/test.jpg")