import bpy
import numpy as np
import math
import gzip
import pickle
import json
import mathutils
import os
import shutil

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
    """获取当前场景的所有物体"""
    return set(bpy.context.scene.objects)

def delete_objects(objects):
    """删除指定的物体"""
    bpy.ops.object.select_all(action='DESELECT')  # 清除选择
    for obj in objects:
        obj.select_set(True)  # 选择要删除的物体
    bpy.ops.object.delete()  # 删除选中的物体

# 设置为 Cycles 渲染引擎（支持 GPU 渲染）
bpy.context.scene.render.engine = 'CYCLES'  

# 启用 GPU 渲染
bpy.context.preferences.addons['cycles'].preferences.compute_device_type = 'CUDA'  # 或 'OPTIX' / 'OPENCL'

# 获取所有设备并启用它们
bpy.context.preferences.addons['cycles'].preferences.get_devices()
for device in bpy.context.preferences.addons['cycles'].preferences.devices:
    device.use = True  # 启用所有可用的 GPU 设备

# 设置当前场景使用 GPU 设备
bpy.context.scene.cycles.device = 'GPU'

for name in ["立方体.001","立方体.002","立方体.003","立方体.004"] :       
    obj = bpy.data.objects.get(name)  # 替换为你的物体名称   
    # 缩放物体
    obj.scale.x *= 0.77

    
# 设置相机
camera = bpy.context.scene.camera

# 如果场景中没有相机，就添加一个
if not camera:
    bpy.ops.object.camera_add(location=(0, 0, 0))  # 创建新的相机
    camera = bpy.context.active_object
    camera.name = "Camera"

    # 设置相机位置
    camera.location = (0, -37.2892, 8.5)

    # 设置相机旋转 (欧拉角: XYZ)
    camera.rotation_euler = (1.4570, 0.0000, 0.0026)

    # 设置相机的焦距（毫米）
    camera.data.lens = 35.0

    # 设置传感器的宽度和高度（毫米）
    camera.data.sensor_width = 36.0
    camera.data.sensor_height = 24.0

    # 设置相机的剪切平面范围
    camera.data.clip_start = 0.1  # 近剪切平面
    camera.data.clip_end = 1000.0  # 远剪切平面

    # 设置相机为当前场景的活动相机
    bpy.context.scene.camera = camera  

def render(file_path,original_objects):#file_path like: "/home/ganzhaoxing/artist/generation_data/1960s/The Younger Generation"
    # 背景板设置
    bpy.ops.mesh.primitive_plane_add(size=10.24, location=(0, 0, 5.12))
    background_plane = bpy.context.object
    background_plane.name = "Background Plane"
    background_plane.rotation_euler = (1.5708, 0, 0)    
    # 背景材质
    image_path = os.path.join(file_path,'reco.png')
    bg_image = bpy.data.images.load(image_path)

    background_material = bpy.data.materials.new(name="BackgroundMaterial")
    background_material.use_nodes = True
    bsdf = background_material.node_tree.nodes.get("Principled BSDF")
    tex_image = background_material.node_tree.nodes.new('ShaderNodeTexImage')
    tex_image.image = bg_image
    background_material.node_tree.links.new(bsdf.inputs['Base Color'], tex_image.outputs['Color'])
    background_plane.data.materials.append(background_material)

    # 加载前景实体
    with open(os.path.join(file_path,'final.json'), 'r', encoding='utf-8') as f:
        entities = json.load(f)
        for entity in entities:
            if entity['asset_id'] == "":
                continue
            orientation = entity['orientation']
            position = entity['position']
            size, location = calculate_dimensions_and_location(position)
            asset_path = f"/home/ganzhaoxing/.objathor-assets/2023_09_23/assets/{entity['asset_id']}/{entity['asset_id']}.pkl.gz"
            load_pickled_3d_asset(asset_path, size, location, orientation)
            source_folder = f"/home/ganzhaoxing/.objathor-assets/2023_09_23/assets/{entity['asset_id']}"  # 文件夹 b 的完整路径
            destination_folder = f"/home/ganzhaoxing/artist/paper_image/assets/{entity['asset_id']}"  # 复制到 c 下的目标路径

            # 执行复制
            try:
                shutil.copytree(source_folder, destination_folder)
                print(f"文件夹 '{source_folder}' 已成功复制到 '{destination_folder}'")
            except FileExistsError:
                print(f"目标文件夹 '{destination_folder}' 已存在，复制未执行")
            except Exception as e:
                print(f"复制时发生错误: {e}")
    # scene = bpy.context.scene

    # # 设置渲染分辨率
    # scene.render.resolution_x = 1560
        
    # 更新 Blender 视图层
    bpy.context.view_layer.update()

    # 渲染并保存图像

    print("新物体已删除，场景恢复至初始状态。")

original_objects = get_scene_objects()    
#1960s/The Sugarcane Field    /1980s/Medea generation_data/1980s/Medea
for root, dirs ,files in os.walk('/home/ganzhaoxing/artist/generation_data/1980s/Medea'):
    for file in files:
        if file == 'final.json':
            render(root,original_objects)
