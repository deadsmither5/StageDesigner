import bpy
import numpy as np
import math
import gzip
import pickle
import json
import mathutils
import os
import shutil
import argparse
import sys

def get_render_arguments():
    parser = argparse.ArgumentParser(description='3D stage')
    parser.add_argument('--output_dir', required=True, help='Output directory path')
    parser.add_argument('--asset_root', 
                        default=os.path.expanduser("~"),  # 自动获取用户主目录
                        help='Root directory for 3D assets (default: $HOME)')
    
    if '--' in sys.argv:
        argv = sys.argv[sys.argv.index('--') + 1:]
    else:
        argv = []
        
    return parser.parse_args(argv)

args = get_render_arguments()

def load_pickled_3d_asset(file_path, size, position, orientation):
    with gzip.open(file_path, 'rb') as f:
        loaded_object_data = pickle.load(f)

    mesh = bpy.data.meshes.new(name='LoadedMesh')
    obj = bpy.data.objects.new('LoadedObject', mesh)
    bpy.context.scene.collection.objects.link(obj)

    obj.data = mesh
    triangles = np.array(loaded_object_data['triangles']).reshape(-1, 3)
    vertices = [[v['x'], v['z'], v['y']] for v in loaded_object_data['vertices']]
    mesh.from_pydata(vertices, [], triangles)
    uvs = [[uv['x'], uv['y']] for uv in loaded_object_data['uvs']]
    mesh.update()

    if not mesh.uv_layers:
        mesh.uv_layers.new(name="UVMap")
    uv_layer = mesh.uv_layers["UVMap"]

    for poly in mesh.polygons:
        for loop_index in poly.loop_indices:
            vertex_index = mesh.loops[loop_index].vertex_index
            uv_layer.data[loop_index].uv = uvs[vertex_index]

    material = bpy.data.materials.new(name="AlbedoMaterial")
    obj.data.materials.append(material)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    principled_bsdf = nodes.get("Principled BSDF")

    texture_node = nodes.new(type='ShaderNodeTexImage')
    image_path = fr"{os.path.dirname(file_path)}\albedo.jpg"
    image = bpy.data.images.load(image_path)
    texture_node.image = image
    material.node_tree.links.new(texture_node.outputs["Color"], principled_bsdf.inputs["Base Color"])

    image_path = fr"{os.path.dirname(file_path)}\normal.jpg"
    img_normal = bpy.data.images.load(image_path)
    normal_node = material.node_tree.nodes.new(type='ShaderNodeTexImage')
    normal_node.image = img_normal
    normal_node.image.colorspace_settings.name = 'Non-Color'

    normal_map_node = material.node_tree.nodes.new(type='ShaderNodeNormalMap')
    material.node_tree.links.new(normal_node.outputs["Color"], normal_map_node.inputs["Color"])
    material.node_tree.links.new(normal_map_node.outputs["Normal"], principled_bsdf.inputs["Normal"])

    mesh.update()
    bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_MASS', center='BOUNDS')
    if orientation == 'front':
        obj.rotation_euler = (math.radians(0), math.radians(0), math.radians(180))
    elif orientation == 'left':
        obj.rotation_euler = (math.radians(0), math.radians(0), math.radians(90))
        x,y,z = size
        size = [y,x,z]
    elif orientation == 'right':
        obj.rotation_euler = (math.radians(0), math.radians(0), math.radians(270))        
        x,y,z = size
        size = [y,x,z]
    scale_factors = [target / current for target, current in zip(size, obj.dimensions)]
    obj.scale = scale_factors
    obj.location = mathutils.Vector(position)
    bpy.context.view_layer.update()
    return obj

def calculate_dimensions_and_location(position):
    x_left, y_left, x_right, y_right, h_low, h_high = [x / 100 for x in position]
    width, depth, height = x_right - x_left, y_right - y_left, h_high - h_low
    center_x, center_y, center_z = (x_left + x_right) / 2 - 5.12, -(y_left + y_right) / 2, h_low
    return [width, depth, height], [center_x, center_y, center_z]

def get_scene_objects():
   
    return set(bpy.context.scene.objects)

def delete_objects(objects):

    bpy.ops.object.select_all(action='DESELECT')  
    for obj in objects:
        obj.select_set(True) 
    bpy.ops.object.delete()  


bpy.context.scene.render.engine = 'CYCLES'  
bpy.context.preferences.addons['cycles'].preferences.compute_device_type = 'CUDA'  
bpy.context.preferences.addons['cycles'].preferences.get_devices()

for device in bpy.context.preferences.addons['cycles'].preferences.devices:
    device.use = True  

bpy.context.scene.cycles.device = 'GPU'

for name in ["立方体.001","立方体.002","立方体.003","立方体.004"] :       
    obj = bpy.data.objects.get(name)  
 
    obj.scale.x *= 0.77
 
camera = bpy.context.scene.camera

if not camera:
    bpy.ops.object.camera_add(location=(0, 0, 0)) 
    camera = bpy.context.active_object
    camera.name = "Camera"
    camera.location = (0, -37.2892, 8.5)
    camera.rotation_euler = (1.4570, 0.0000, 0.0026)
    camera.data.lens = 35.0
    camera.data.sensor_width = 36.0
    camera.data.sensor_height = 24.0
    camera.data.clip_start = 0.1  
    camera.data.clip_end = 1000.0  
    bpy.context.scene.camera = camera  

def render(file_path,original_objects):

    bpy.ops.mesh.primitive_plane_add(size=10.24, location=(0, 0, 5.12))
    background_plane = bpy.context.object
    background_plane.name = "Background Plane"
    background_plane.rotation_euler = (1.5708, 0, 0)    

    image_path = os.path.join(file_path,'reco.png')
    bg_image = bpy.data.images.load(image_path)

    background_material = bpy.data.materials.new(name="BackgroundMaterial")
    background_material.use_nodes = True
    bsdf = background_material.node_tree.nodes.get("Principled BSDF")
    tex_image = background_material.node_tree.nodes.new('ShaderNodeTexImage')
    tex_image.image = bg_image
    background_material.node_tree.links.new(bsdf.inputs['Base Color'], tex_image.outputs['Color'])
    background_plane.data.materials.append(background_material)

  
    with open(os.path.join(file_path,'final.json'), 'r', encoding='utf-8') as f:
        entities = json.load(f)
        for entity in entities:
            if entity['asset_id'] == "":
                continue
            orientation = entity['orientation']
            position = entity['position']
            size, location = calculate_dimensions_and_location(position)
            asset_path = os.path.join(
                args.asset_root,
                ".objathor-assets/2023_09_23/assets",
                entity['asset_id'],
                f"{entity['asset_id']}.pkl.gz"
            )
            load_pickled_3d_asset(asset_path, size, location, orientation)
     
    # scene = bpy.context.scene

    # scene.render.resolution_x = 1560
 
    bpy.context.view_layer.update()

original_objects = get_scene_objects()    
for root, dirs, files in os.walk(args.output_dir):  
    for file in files:
        if file == 'final.json':
            render(root, original_objects)