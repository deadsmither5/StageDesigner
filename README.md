# StageDesigner: Artistic Stage Generation for Scenography via Theater Scripts (CVPR 2025)

<div align = 'center'>
<b>Zhaoxing Gan¹, Mengtian Li¹²†, Ruhua Chen³, Zhongxia Ji³,  
Sichen Guo³, Huanling Hu¹, Guangnan Ye¹†, Zuo Hu³</b>

¹Fudan University, ²Shanghai University, ³Shanghai Theatre Academy  

📧 zxgan23@m.fudan.edu.cn, mtli@shu.edu.cn, yegn@fudan.edu.cn, {chenruhua, zhongxia.ji, huzuo}@sta.edu.cn  
</div>


<h5 align="center">
<img src="https://github.com/deadsmither5/StageDesigner/blob/main/teaser.png" width="800px"/><br/>
</h5>

 
## Installation
After cloning this repo, you can install the required dependencies using the following commands:
```
conda create --name StageDesigner python=3.10
conda activate StageDesigner
pip install -r requirements.txt
```

## Usage
You can genrate a stage with your text using the following commands:
```
python stage_generator.py \
  --text "A modern art gallery with a rotating sculpture at its center." \
  --openai_api_key <sk-your-key-here> \
  --output_dir <your-path>
```

## Rendering in blender
After generating the stage, you can get the rendered 3D scene in blender using the following commands: 
```
blender --background <Your Path>/StageDesigner/base_stage/model.blend --python <Your Path>/StageDesigner/utils/blender_render.py \
-- --output_dir <same as in usage> --asset_root <home path of .objathor-assets default ~>
```
## Dataset: 
### Retrieve 3D Assets
Download the objaverse 3D assets in [<span style="color:blue">HOLODECK</span>](https://github.com/allenai/Holodeck), by default these will save to ~/.objathor-assets/2023_09_23.
### StagePro-V1
If you want to use the StagePro-v1 dataset for non-commercial use, please fill the [<span style="color:blue">release agreement</span>](https://github.com/deadsmither5/StageDesigner/blob/main/release%20agreement.pdf) and sent email to zxgan23@m.fudan.edu.cn

## Citation
Please cite the paper if you feel it is useful.