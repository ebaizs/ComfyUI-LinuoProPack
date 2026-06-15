import torch
import folder_paths
import numpy as np
from torch.nn import functional as F
import comfy.utils

# ================= 1. 数值滑块节点 =================
class Slider_0_1:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"value": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01})}}
    RETURN_TYPES = ("FLOAT",)
    FUNCTION = "slider"
    CATEGORY = "Linuo/数值滑块"
    def slider(self, value): return (value,)

class Slider_0_10:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"value": ("FLOAT", {"default": 5.0, "min": 0.0, "max": 10.0, "step": 0.1})}}
    RETURN_TYPES = ("FLOAT",)
    FUNCTION = "slider"
    CATEGORY = "Linuo/数值滑块"
    def slider(self, value): return (value,)

class Slider_0_100:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"value": ("FLOAT", {"default": 50.0, "min": 0.0, "max": 100.0, "step": 1.0})}}
    RETURN_TYPES = ("FLOAT",)
    FUNCTION = "slider"
    CATEGORY = "Linuo/数值滑块"
    def slider(self, value): return (value,)

class Slider_Custom:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "最小值": ("FLOAT", {"default": 0.0, "step": 0.01}),
                "最大值": ("FLOAT", {"default": 1.0, "step": 0.01}),
                "当前值": ("FLOAT", {"default": 0.5, "min": -1e6, "max": 1e6, "step": 0.01}),
            }
        }
    RETURN_TYPES = ("FLOAT",)
    FUNCTION = "get_value"
    CATEGORY = "Linuo/数值滑块"
    def get_value(self, 最小值, 最大值, 当前值):
        clamped = max(最小值, min(最大值, 当前值))
        return (clamped,)

# ================= 2. 空 Latent 预设节点 =================
class EmptyLatentPreset:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "预设": (["4:3_1024", "16:9_1024", "4:3_1600", "16:9_1600", "4:3_2024", "16:9_2024", "4:3_2500", "16:9_2500", "自定义"], {"default": "16:9_1024"}),
                "横竖屏切换": (["横屏", "竖屏"], {"default": "横屏"}),
                "自定义宽度": ("INT", {"default": 1024, "min": 64, "max": 4096, "step": 8}),
                "自定义高度": ("INT", {"default": 576, "min": 64, "max": 4096, "step": 8}),
                "批次数量": ("INT", {"default": 1, "min": 1, "max": 64}),
            }
        }
    RETURN_TYPES = ("LATENT",)
    FUNCTION = "generate"
    CATEGORY = "Linuo/图像尺寸"
    def generate(self, 预设, 横竖屏切换, 自定义宽度, 自定义高度, 批次数量):
        if 预设 == "4:3_1024":
            long_side, ratio = 1024, 4/3
        elif 预设 == "16:9_1024":
            long_side, ratio = 1024, 16/9
        elif 预设 == "4:3_1600":
            long_side, ratio = 1600, 4/3
        elif 预设 == "16:9_1600":
            long_side, ratio = 1600, 16/9
        elif 预设 == "4:3_2024":
            long_side, ratio = 2024, 4/3
        elif 预设 == "16:9_2024":
            long_side, ratio = 2024, 16/9
        elif 预设 == "4:3_2500":
            long_side, ratio = 2500, 4/3
        elif 预设 == "16:9_2500":
            long_side, ratio = 2500, 16/9
        else:
            width = 自定义宽度
            height = 自定义高度
            if 横竖屏切换 == "竖屏":
                width, height = height, width
            latent = torch.zeros([批次数量, 4, height // 8, width // 8])
            return ({"samples": latent},)
        if 横竖屏切换 == "横屏":
            width = long_side
            height = int(long_side / ratio)
        else:
            height = long_side
            width = int(long_side / ratio)
        width = (width // 8) * 8
        height = (height // 8) * 8
        latent = torch.zeros([批次数量, 4, height // 8, width // 8])
        return ({"samples": latent},)

# ================= 3. 图像与遮罩按长边缩放 =================
def morphological_close(mask_tensor, kernel_size=5):
    if mask_tensor is None: return None
    if mask_tensor.dim() == 3: mask_tensor = mask_tensor.unsqueeze(1)
    mask_bin = (mask_tensor > 0.5).float()
    kernel = torch.ones(1, 1, kernel_size, kernel_size, dtype=mask_tensor.dtype, device=mask_tensor.device)
    padding = kernel_size // 2
    def dilate(x): return (F.conv2d(x, kernel, padding=padding) > 0).float()
    def erode(x):
        conv = F.conv2d(x, kernel, padding=padding)
        kernel_area = kernel_size * kernel_size
        return (conv == kernel_area).float()
    closed = erode(dilate(mask_bin))
    return closed.squeeze(1)

class ImageMaskScaleByLongSide:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "图像": ("IMAGE",),
                "长边数值": ("INT", {"default": 1024, "min": 64, "max": 4096, "step": 8}),
                "缩放模式": (["lanczos", "bilinear", "bicubic"], {"default": "lanczos"}),
                "填充漏洞": ("BOOLEAN", {"default": True, "label_on": "填充漏洞", "label_off": "不填充"}),
            },
            "optional": {"遮罩": ("MASK",),}
        }
    RETURN_TYPES = ("IMAGE", "MASK")
    RETURN_NAMES = ("image", "mask")
    FUNCTION = "scale"
    CATEGORY = "Linuo/图像处理"
    def scale(self, 图像, 长边数值, 缩放模式, 填充漏洞, 遮罩=None):
        def get_resize_mode(mode_str):
            if mode_str == "lanczos": return F.interpolate, {"mode": "bilinear", "antialias": True}
            elif mode_str == "bilinear": return F.interpolate, {"mode": "bilinear", "antialias": False}
            else: return F.interpolate, {"mode": "bicubic", "antialias": False}
        interp_fn, kwargs = get_resize_mode(缩放模式)
        original_h, original_w = 图像.shape[1], 图像.shape[2]
        if original_h >= original_w:
            new_h = 长边数值; new_w = int(original_w * (长边数值 / original_h))
        else:
            new_w = 长边数值; new_h = int(original_h * (长边数值 / original_w))
        new_w = (new_w // 8) * 8; new_h = (new_h // 8) * 8
        img = 图像.permute(0, 3, 1, 2)
        img_resized = interp_fn(img, size=(new_h, new_w), **kwargs).permute(0, 2, 3, 1)
        mask_resized = None
        if 遮罩 is not None:
            mask = 遮罩
            if mask.dim() == 2: mask = mask.unsqueeze(0).unsqueeze(0)
            elif mask.dim() == 3: mask = mask.unsqueeze(1)
            mask_resized = interp_fn(mask, size=(new_h, new_w), mode="bilinear", antialias=False).squeeze(1)
            mask_resized = torch.clamp(mask_resized, 0.0, 1.0)
            mask_binary = (mask_resized > 0.5).float()
            if 填充漏洞:
                try:
                    from scipy import ndimage
                    mask_np = mask_binary.cpu().numpy().astype(bool)
                    filled_np = np.zeros_like(mask_np)
                    for i in range(mask_np.shape[0]):
                        filled_np[i] = ndimage.binary_fill_holes(mask_np[i])
                    mask_resized = torch.from_numpy(filled_np.astype(np.float32)).to(mask_binary.device)
                except ImportError:
                    for _ in range(3):
                        mask_binary = morphological_close(mask_binary, kernel_size=21)
                    mask_resized = mask_binary
            else:
                mask_resized = mask_binary
        return (img_resized, mask_resized)

# ================= 4. 出图参数预设节点 =================
class SamplingParamsPreset:
    PRESET_MAP = {
        "4步加速": {"steps": 4, "cfg": 1.0},
        "8步加速": {"steps": 8, "cfg": 1.0},
        "flux中质量": {"steps": 20, "cfg": 3.5},
        "flux高质量": {"steps": 30, "cfg": 4},
        "qwen中质量": {"steps": 20, "cfg": 2.5},
        "qwen高质量": {"steps": 50, "cfg": 4.0},
    }
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "预设": (["4步加速", "8步加速", "flux中质量", "flux高质量", "qwen中质量", "qwen高质量", "自定义"], {"default": "flux中质量"}),
                "自定义步数": ("INT", {"default": 8, "min": 1, "max": 100, "step": 1}),
                "自定义CFG": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 30.0, "step": 0.1}),
            }
        }
    RETURN_TYPES = ("INT", "FLOAT")
    RETURN_NAMES = ("steps", "cfg")
    FUNCTION = "get_params"
    CATEGORY = "Linuo/采样参数"
    def get_params(self, 预设, 自定义步数, 自定义CFG):
        if 预设 == "自定义": return (自定义步数, 自定义CFG)
        else: return (self.PRESET_MAP[预设]["steps"], self.PRESET_MAP[预设]["cfg"])

# ================= 5. 装饰风格词库（从工作流中提取）=================
DECOR_STYLES = {
    "现代简约": "现代简约：以黑白灰为主色调，采用几何造型与极简线条设计。家具选用金属玻璃材质，灯具采用无主灯设计，配饰注重隐藏式收纳与智能家居。墙面使用纯色乳胶漆，地面铺装灰色地砖或深色木地板，整体呈现理性整洁、具有科技感的现代空间。",
    "垞寂风": "侘寂风格，整体以低饱和度灰调为主，墙面采用微水泥或哑光艺术漆，保留自然斑驳肌理，地面铺设浅灰或原木色地板。家具选用未经过多修饰的原木或深褐色胡桃木材质，造型简洁克制，搭配亚麻窗帘、藤编座椅等自然元素。空间注重留白与不对称布局，通过少量手工陶器、枯枝、棉麻织物或旧石器装饰体现岁月痕迹。灯光采用无主灯设计，以纸质暖光灯、隐藏式灯带营造柔和光影，突出质朴寂静的禅意氛围",
    "法式风格": "法式：法式风格以奶油白、浅灰为主色调，采用雕花家具与曲线造型。家具选用丝绸绒布材质，灯具采用水晶吊灯，配饰包含石膏线条、镜面与鲜花。墙面运用装饰线条，地面铺陈鱼骨拼木地板或大理石，整体呈现浪漫优雅、精致细腻的艺术氛围。",
    "意式极简风格": "意式极简风，整体以黑白灰为主色调，搭配少量香槟金或墨绿色点缀。家具线条利落（如皮质沙发、玻璃茶几），材质融合大理石、黄铜、哑光烤漆板，强调功能性与几何美感。墙面保留大面积留白，地面通铺哑光大理石或原木地板，软装以抽象艺术挂画、金属边框装饰为主，灯光采用隐藏式灯带或极简吊灯，营造高级感与空间留白的平衡。",
    "日式风格": "日式风格，\n整体以原木色、米白和浅灰为主色调，墙面采用环保乳胶漆或木饰面，地面铺设浅色木地板。家具以日式极简设计为主，搭配藤编座椅、亚麻窗帘、棉麻抱枕等自然元素，强调材质的原始质感。空间布局开放通透，通过绿植（琴叶榕、龟背竹）、手工陶器、棉麻编织物点缀生机，灯光采用暖光纸灯笼或隐藏式灯带，营造温暖治愈的自然氛围。",
    "后现代": "后现代：以对比色彩为主色调，采用解构主义与不规则造型。家具选用混合材质，灯具采用艺术装置设计，配饰强调个性表达与艺术性。墙面运用深色涂料，地面铺装个性地砖，整体打造打破常规、充满戏剧性的创意空间。",
    "宋式美学": "整体以低饱和度的米白、奶咖或浅灰为基调，墙面采用稻草漆或哑光乳胶漆，地面铺设深棕色木地板或青石板。家具选用胡桃木色，造型简洁内敛（如圈椅、条案），搭配藤编或棉麻软装。装饰元素以宋代文人雅趣为核心，悬挂水墨山水画、书法卷轴，搭配青瓷花瓶、枯山水盆景、松柏盆栽，灯光采用纸质暖光灯笼或无主灯设计，营造留白与禅意交织的静谧感。",
    "中古风": "中古风格，整体以大地色（棕、米、驼）为基底，搭配复古红、宝石蓝或芥末黄等高饱和度点缀色。家具选用胡桃木或柚木材质，造型简洁流畅，强调几何线条与有机曲线结合（如流线型沙发、细腿单椅），搭配金属（黄铜/不锈钢）灯具、藤编收纳筐等工业元素。墙面保留局部文化砖或仿古涂料肌理，地面铺设深色木地板或波点地毯，软装以抽象艺术挂画、龟背竹绿植、复古陶罐为主，灯光采用球形吊灯或飞碟型落地灯，营造复古与现代交融的怀旧氛围",
    "传统中式": "中式风格，整体以深棕、暗红、黑色为主色调，墙面采用雕花壁纸或仿古涂料，地面铺设深色木地板或青石砖。家具选用清式红木材质（如太师椅、八仙桌），搭配丝绸或刺绣软装。空间布局严格对称，通过屏风、博古架、雕花隔断划分区域，装饰元素包括龙凤图案、青花瓷、青铜鼎、红木雕花，灯光采用宫灯或暖光壁灯，营造庄重典雅的宫廷氛围",
    "新中式风格": "新中式：以胡桃木色与米白为主色调，融合深灰蓝与墨色点缀，采用对称布局与简化中式线条。家具选用实木框架搭配布艺软包，灯具采用圆形或方形的中式造型木质灯，配饰包含水墨画、青花瓷、博古架与枯山水元素。墙面运用木质线条装饰，地面铺陈深色木地板或灰色系地砖，整体营造典雅沉稳、富有文化底蕴的现代东方美学空间。",
    "原木奶油风格": " 原木奶油风，奶油白色调和浅色原木色为主，空间通透温馨，充满柔和的光线。\n  天然原木材质，棉麻布艺软装，微水泥墙面，营造温暖质朴的治愈氛围。\n柔和温暖的灯光，大量留白，搭配绿植点缀，宁静而富有生机。\n融入极简主义设计，线条干净利落，凸显现代与自然的融合。空间洋溢着温暖治愈的原木奶油风，以柔和的奶油白为基调，搭配浅色原木的温润质感。微水泥墙面与棉麻软装勾勒出细腻肌理，圆润流畅的家具线条在柔和的光线下更显温馨。整体通透开阔，辅以绿植点缀，营造出一个宁静、自然且充满呼吸感的治愈系居所",
    "北欧风格": "北欧：以白色、浅木色为主色调，采用有机曲线与自然光线设计。家具选用天然实木材质，灯具采用简约造型，配饰包含棉麻织物、陶瓷装饰与绿植。墙面使用白色乳胶漆，地面铺装浅色木地板，整体呈现明亮温馨、人性化的自然居住空间。",
    "美式风格": "美式：以大地色系、深蓝暗红为主色调，采用厚重家具与装饰线条。家具选用实木皮革材质，灯具采用复古吊灯，配饰包含照片墙、装饰镜与温馨布艺。墙面运用暖色系涂料，地面铺陈深色木地板或仿古地砖，整体营造舒适温馨、富有生活气息的家居环境。",
    "轻奢风格": "轻奢风格，整体以中性色调（米白、浅灰、驼色）为基底，搭配香槟金/黄铜色金属元素点缀。墙面采用哑光乳胶漆或岩板背景墙，地面通铺柔光大理石或木地板。家具线条简洁流畅，搭配丝绒沙发、皮质单椅、玻璃茶几等，材质融合大理石、黄铜、金属与天然木材。空间布局开放通透，通过隐藏式灯光、悬浮书架、开放式茶室等功能区强化实用性，细节处以艺术挂画、丝绒抱枕、水晶吊灯提升精致感，整体呈现低调奢华的现代感。",
}

# ================= 6. 风格文本生成器 =================
class StyleTextGenerator:
    @classmethod
    def INPUT_TYPES(cls):
        style_list = list(DECOR_STYLES.keys()) + ["自定义"]
        return {
            "required": {
                "通用提示词": ("STRING", {"multiline": True, "default": "", "placeholder": "输入通用提示词"}),
                "风格1预设": (style_list, {"default": "现代简约"}),
                "风格1自定义词": ("STRING", {"default": "", "placeholder": "自定义风格词（仅当上方选择'自定义'时生效）"}),
                "风格2预设": (style_list, {"default": "北欧风格"}),
                "风格2自定义词": ("STRING", {"default": "", "placeholder": "自定义风格词（仅当上方选择'自定义'时生效）"}),
            }
        }
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("风格1完整提示词", "风格2完整提示词")
    FUNCTION = "generate_texts"
    CATEGORY = "Linuo/提示词混搭"

    def get_style_text(self, preset, custom_text):
        if preset == "自定义":
            return custom_text.strip()
        else:
            return DECOR_STYLES.get(preset, "")

    def generate_texts(self, 通用提示词, 风格1预设, 风格1自定义词, 风格2预设, 风格2自定义词):
        style1_text = self.get_style_text(风格1预设, 风格1自定义词)
        style2_text = self.get_style_text(风格2预设, 风格2自定义词)
        prompt1 = f"{通用提示词}, {style1_text}" if style1_text else 通用提示词
        prompt2 = f"{通用提示词}, {style2_text}" if style2_text else 通用提示词
        return (prompt1, prompt2)

# ================= 7. 风格条件混合器（增强版）=================
class FenggehunheFixed:
    @classmethod
    def INPUT_TYPES(cls):
        style_list = list(DECOR_STYLES.keys()) + ["自定义"]
        return {
            "required": {
                "clip": ("CLIP",),
                "通用提示词": ("STRING", {"multiline": True, "default": "", "placeholder": "输入通用提示词"}),
                "风格1预设": (style_list, {"default": "现代简约"}),
                "风格1自定义词": ("STRING", {"default": "", "placeholder": "自定义风格词（仅当上方选择'自定义'时生效）"}),
                "风格2预设": (style_list, {"default": "北欧风格"}),
                "风格2自定义词": ("STRING", {"default": "", "placeholder": "自定义风格词（仅当上方选择'自定义'时生效）"}),
                "混合方式": (["加权拼合", "线性插值"], {"default": "加权拼合"}),
                "风格1强度": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01}),
                "输出模式": (["混合条件", "风格1条件", "风格2条件"], {"default": "混合条件"}),
            }
        }
    RETURN_TYPES = ("CONDITIONING",)
    RETURN_NAMES = ("CONDITIONING",)
    FUNCTION = "mix_styles"
    CATEGORY = "Linuo/提示词混搭"

    def get_style_text(self, preset, custom_text):
        if preset == "自定义":
            return custom_text.strip()
        else:
            return DECOR_STYLES.get(preset, "")

    def encode_prompt_fixed(self, clip, prompt):
        if clip is None:
            raise ValueError("CLIP模型输入不能为空")
        tokens = clip.tokenize(prompt)
        result = clip.encode_from_tokens(tokens, return_pooled=True)
        if len(result) == 2:
            cond, pooled = result
            if pooled is not None:
                return [[cond, {"pooled_output": pooled}]]
            else:
                return [[cond, {}]]
        else:
            return [[result, {}]]

    def blend_conditionings(self, cond1, cond2, strength, mode):
        if not cond1 or not cond2:
            return cond1 or cond2
        out_cond = []
        for c1, c2 in zip(cond1, cond2):
            t1, d1 = c1
            t2, d2 = c2
            len1 = t1.shape[1]
            len2 = t2.shape[1]

            if mode == "线性插值":
                if len1 != len2:
                    min_len = min(len1, len2)
                    t1 = t1[:, :min_len, :]
                    t2 = t2[:, :min_len, :]
                blended_t = t1 * strength + t2 * (1.0 - strength)
                blended_dict = {}
                if "pooled_output" in d1 and "pooled_output" in d2:
                    blended_dict["pooled_output"] = d1["pooled_output"] * strength + d2["pooled_output"] * (1.0 - strength)
                elif "pooled_output" in d1:
                    blended_dict["pooled_output"] = d1["pooled_output"]
                elif "pooled_output" in d2:
                    blended_dict["pooled_output"] = d2["pooled_output"]
            else:  # 加权拼合
                t1_scaled = t1 * strength
                t2_scaled = t2 * (1.0 - strength)
                blended_t = torch.cat([t1_scaled, t2_scaled], dim=1)
                blended_dict = {}
                if "pooled_output" in d1 and "pooled_output" in d2:
                    blended_dict["pooled_output"] = d1["pooled_output"] * strength + d2["pooled_output"] * (1.0 - strength)
                elif "pooled_output" in d1:
                    blended_dict["pooled_output"] = d1["pooled_output"] * strength
                elif "pooled_output" in d2:
                    blended_dict["pooled_output"] = d2["pooled_output"] * (1.0 - strength)
            out_cond.append([blended_t, blended_dict])
        return out_cond

    def mix_styles(self, clip, 通用提示词, 风格1预设, 风格1自定义词, 风格2预设, 风格2自定义词, 混合方式, 风格1强度, 输出模式):
        style1_text = self.get_style_text(风格1预设, 风格1自定义词)
        style2_text = self.get_style_text(风格2预设, 风格2自定义词)
        prompt1 = f"{通用提示词}, {style1_text}" if style1_text else 通用提示词
        prompt2 = f"{通用提示词}, {style2_text}" if style2_text else 通用提示词

        cond1 = self.encode_prompt_fixed(clip, prompt1)
        cond2 = self.encode_prompt_fixed(clip, prompt2)

        if 输出模式 == "风格1条件":
            return (cond1,)
        elif 输出模式 == "风格2条件":
            return (cond2,)
        else:
            mixed_cond = self.blend_conditionings(cond1, cond2, 风格1强度, 混合方式)
            return (mixed_cond,)

# ================= 8. 模型任意选择器（3输入）=================
class ModelSelector:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "加速模型_nunchaku": ("MODEL",),
                "加速模型_GGUF": ("MODEL",),
                "标准模型": ("MODEL",),
                "选择输出模型": (["加速模型_nunchaku", "加速模型_GGUF", "标准模型"], {"default": "加速模型_nunchaku"}),
            }
        }
    RETURN_TYPES = ("MODEL",)
    FUNCTION = "select"
    CATEGORY = "Linuo/任意选择器"

    def select(self, 加速模型_nunchaku, 加速模型_GGUF, 标准模型, 选择输出模型):
        if 选择输出模型 == "加速模型_nunchaku":
            return (加速模型_nunchaku,)
        elif 选择输出模型 == "加速模型_GGUF":
            return (加速模型_GGUF,)
        else:
            return (标准模型,)

# ================= 9. 条件任意选择器（3输入）=================
class ConditioningSelector:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "混合条件": ("CONDITIONING",),
                "条件1": ("CONDITIONING",),
                "条件2": ("CONDITIONING",),
                "选择输出条件": (["混合条件", "条件1", "条件2"], {"default": "混合条件"}),
            }
        }
    RETURN_TYPES = ("CONDITIONING",)
    FUNCTION = "select"
    CATEGORY = "Linuo/任意选择器"

    def select(self, 混合条件, 条件1, 条件2, 选择输出条件):
        if 选择输出条件 == "混合条件":
            return (混合条件,)
        elif 选择输出条件 == "条件1":
            return (条件1,)
        else:
            return (条件2,)

# ================= 10. 通用任意选择器（4输入）=================
class GenericSelector4:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "输入1": ("*",),
                "输入2": ("*",),
                "输入3": ("*",),
                "输入4": ("*",),
                "选择输出": (["输入1", "输入2", "输入3", "输入4"], {"default": "输入1"}),
            }
        }
    RETURN_TYPES = ("*",)
    FUNCTION = "select"
    CATEGORY = "Linuo/任意选择器"

    def select(self, 输入1, 输入2, 输入3, 输入4, 选择输出):
        if 选择输出 == "输入1":
            return (输入1,)
        elif 选择输出 == "输入2":
            return (输入2,)
        elif 选择输出 == "输入3":
            return (输入3,)
        else:
            return (输入4,)

# ================= 11. Linuo图生图参数 =================
class LinuoImg2ImgParams:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "图像": ("IMAGE",),
                "vae": ("VAE",),
                "长边数值": ("INT", {"default": 1024, "min": 64, "max": 4096, "step": 8}),
                "采样预设": (["4步加速", "8步加速", "flux中质量", "flux高质量", "qwen中质量", "qwen高质量", "自定义"], {"default": "flux中质量"}),
                "自定义步数": ("INT", {"default": 20, "min": 1, "max": 100, "step": 1}),
                "自定义CFG": ("FLOAT", {"default": 3.5, "min": 0.0, "max": 30.0, "step": 0.1}),
            }
        }
    RETURN_TYPES = ("LATENT", "INT", "FLOAT", "IMAGE")
    RETURN_NAMES = ("latent", "steps", "cfg", "缩放后图像")
    FUNCTION = "process"
    CATEGORY = "Linuo/参数整合"

    def process(self, 图像, vae, 长边数值, 采样预设, 自定义步数, 自定义CFG):
        original_h, original_w = 图像.shape[1], 图像.shape[2]
        if original_h >= original_w:
            new_h = 长边数值
            new_w = int(original_w * (长边数值 / original_h))
        else:
            new_w = 长边数值
            new_h = int(original_h * (长边数值 / original_w))
        new_w = (new_w // 8) * 8
        new_h = (new_h // 8) * 8
        img = 图像.permute(0, 3, 1, 2)
        img_resized = F.interpolate(img, size=(new_h, new_w), mode="bilinear", antialias=True)
        img_resized = img_resized.permute(0, 2, 3, 1)
        latent = vae.encode(img_resized[:, :, :, :3])
        if 采样预设 == "自定义":
            steps = 自定义步数
            cfg = 自定义CFG
        else:
            steps = SamplingParamsPreset.PRESET_MAP[采样预设]["steps"]
            cfg = SamplingParamsPreset.PRESET_MAP[采样预设]["cfg"]
        return ({"samples": latent}, steps, cfg, img_resized)

# ================= 12. Linuo文生图参数 =================
class LinuoTxt2ImgParams:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "采样预设": (["4步加速", "8步加速", "flux中质量", "flux高质量", "qwen中质量", "qwen高质量", "自定义"], {"default": "flux中质量"}),
                "自定义步数": ("INT", {"default": 20, "min": 1, "max": 100, "step": 1}),
                "自定义CFG": ("FLOAT", {"default": 3.5, "min": 0.0, "max": 30.0, "step": 0.1}),
                "尺寸预设": (["4:3_1024", "16:9_1024", "4:3_1600", "16:9_1600", "4:3_2024", "16:9_2024", "4:3_2500", "16:9_2500", "自定义"], {"default": "16:9_1024"}),
                "横竖屏切换": (["横屏", "竖屏"], {"default": "横屏"}),
                "自定义宽度": ("INT", {"default": 1024, "min": 64, "max": 4096, "step": 8}),
                "自定义高度": ("INT", {"default": 576, "min": 64, "max": 4096, "step": 8}),
                "批次数量": ("INT", {"default": 1, "min": 1, "max": 64}),
            }
        }
    RETURN_TYPES = ("LATENT", "INT", "FLOAT")
    RETURN_NAMES = ("latent", "steps", "cfg")
    FUNCTION = "process"
    CATEGORY = "Linuo/参数整合"

    def process(self, 采样预设, 自定义步数, 自定义CFG, 尺寸预设, 横竖屏切换, 自定义宽度, 自定义高度, 批次数量):
        if 尺寸预设 == "4:3_1024":
            long_side, ratio = 1024, 4/3
        elif 尺寸预设 == "16:9_1024":
            long_side, ratio = 1024, 16/9
        elif 尺寸预设 == "4:3_1600":
            long_side, ratio = 1600, 4/3
        elif 尺寸预设 == "16:9_1600":
            long_side, ratio = 1600, 16/9
        elif 尺寸预设 == "4:3_2024":
            long_side, ratio = 2024, 4/3
        elif 尺寸预设 == "16:9_2024":
            long_side, ratio = 2024, 16/9
        elif 尺寸预设 == "4:3_2500":
            long_side, ratio = 2500, 4/3
        elif 尺寸预设 == "16:9_2500":
            long_side, ratio = 2500, 16/9
        else:
            width = 自定义宽度
            height = 自定义高度
            if 横竖屏切换 == "竖屏":
                width, height = height, width
            latent = torch.zeros([批次数量, 4, height // 8, width // 8])
            if 采样预设 == "自定义":
                steps = 自定义步数
                cfg = 自定义CFG
            else:
                steps = SamplingParamsPreset.PRESET_MAP[采样预设]["steps"]
                cfg = SamplingParamsPreset.PRESET_MAP[采样预设]["cfg"]
            return ({"samples": latent}, steps, cfg)
        if 横竖屏切换 == "横屏":
            width = long_side
            height = int(long_side / ratio)
        else:
            height = long_side
            width = int(long_side / ratio)
        width = (width // 8) * 8
        height = (height // 8) * 8
        latent = torch.zeros([批次数量, 4, height // 8, width // 8])
        if 采样预设 == "自定义":
            steps = 自定义步数
            cfg = 自定义CFG
        else:
            steps = SamplingParamsPreset.PRESET_MAP[采样预设]["steps"]
            cfg = SamplingParamsPreset.PRESET_MAP[采样预设]["cfg"]
        return ({"samples": latent}, steps, cfg)

# ================= 13. Linuo控制发散混合出图设置 =================
class LinuoControlFusion:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "clip": ("CLIP",),
                "vae": ("VAE",),
                "线稿处理图": ("IMAGE",),
                "深度控制图": ("IMAGE",),
                "线稿图强度": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01}),
                "控制与发散分界点": ("FLOAT", {"default": 0.6, "min": 0.0, "max": 1.0, "step": 0.01}),
                "通用提示词": ("STRING", {"multiline": True, "default": "", "placeholder": "通用描述"}),
                "强控制提示词": ("STRING", {"multiline": True, "default": "", "placeholder": "强控制提示词"}),
                "发散提示词": ("STRING", {"multiline": True, "default": "", "placeholder": "发散提示词"}),
                "参考图2": ("IMAGE",),
                "参考图3": ("IMAGE",),
                "输出模式": (["先控制再发散", "先发散再控制", "纯强控制条件"], {"default": "先控制再发散"}),
            }
        }
    RETURN_TYPES = ("IMAGE", "CONDITIONING")
    RETURN_NAMES = ("强控制图像", "CONDITIONING")
    FUNCTION = "process"
    CATEGORY = "Linuo/参数整合"

    def blend_images(self, img1, img2, factor):
        return img1 * factor + img2 * (1.0 - factor)

    def encode_prompt(self, clip, prompt):
        if clip is None:
            raise ValueError("clip不能为空")
        tokens = clip.tokenize(prompt)
        result = clip.encode_from_tokens(tokens, return_pooled=True)
        if len(result) == 2:
            cond, pooled = result
            if pooled is not None:
                return [[cond, {"pooled_output": pooled}]]
            else:
                return [[cond, {}]]
        else:
            return [[result, {}]]

    def apply_timestep_range(self, cond, start=None, end=None):
        if cond is None:
            return None
        new_cond = []
        for c in cond:
            t, d = c
            new_d = d.copy()
            if start is not None:
                new_d["start_percent"] = start
            if end is not None:
                new_d["end_percent"] = end
            new_cond.append([t, new_d])
        return new_cond

    def combine_conditionings(self, cond1, cond2):
        if cond1 is None:
            return cond2
        if cond2 is None:
            return cond1
        return cond1 + cond2

    def process(self, clip, vae, 线稿处理图, 深度控制图, 线稿图强度, 控制与发散分界点,
                通用提示词, 强控制提示词, 发散提示词, 参考图2, 参考图3, 输出模式):
        control_img = self.blend_images(线稿处理图, 深度控制图, 线稿图强度)
        control_prompt = f"{通用提示词}, {强控制提示词}" if 强控制提示词 else 通用提示词
        diverge_prompt = f"{通用提示词}, {发散提示词}" if 发散提示词 else 通用提示词
        cond_control = self.encode_prompt(clip, control_prompt)
        cond_diverge = self.encode_prompt(clip, diverge_prompt)

        cond_control_range1 = self.apply_timestep_range(cond_control, end=控制与发散分界点)
        cond_diverge_range1 = self.apply_timestep_range(cond_diverge, start=控制与发散分界点)
        mixed_cond1 = self.combine_conditionings(cond_control_range1, cond_diverge_range1)

        cond_control_range2 = self.apply_timestep_range(cond_control, start=控制与发散分界点)
        cond_diverge_range2 = self.apply_timestep_range(cond_diverge, end=控制与发散分界点)
        mixed_cond2 = self.combine_conditionings(cond_control_range2, cond_diverge_range2)

        if 输出模式 == "先控制再发散":
            final_cond = mixed_cond1
        elif 输出模式 == "先发散再控制":
            final_cond = mixed_cond2
        else:
            final_cond = cond_control
        return (control_img, final_cond)

# ================= 节点注册 =================
NODE_CLASS_MAPPINGS = {
    "Slider_0_1": Slider_0_1,
    "Slider_0_10": Slider_0_10,
    "Slider_0_100": Slider_0_100,
    "Slider_Custom": Slider_Custom,
    "EmptyLatentPreset": EmptyLatentPreset,
    "ImageMaskScaleByLongSide": ImageMaskScaleByLongSide,
    "SamplingParamsPreset": SamplingParamsPreset,
    "StyleTextGenerator": StyleTextGenerator,
    "风格条件混合器 (修复版)": FenggehunheFixed,
    "ModelSelector": ModelSelector,
    "ConditioningSelector": ConditioningSelector,
    "GenericSelector4": GenericSelector4,
    "Linuo图生图参数": LinuoImg2ImgParams,
    "Linuo文生图参数": LinuoTxt2ImgParams,
    "Linuo控制发散混合出图设置": LinuoControlFusion,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Slider_0_1": "Linuo数值滑块 (0～1)",
    "Slider_0_10": "Linuo数值滑块 (0～10)",
    "Slider_0_100": "Linuo数值滑块 (0～100)",
    "Slider_Custom": "Linuo数值滑块 (自定义范围)",
    "EmptyLatentPreset": "Linuo空Latent预设 (比例/横竖屏)",
    "ImageMaskScaleByLongSide": "Linuo图像+遮罩按长边缩放 (可填充漏洞)",
    "SamplingParamsPreset": "Linuo出图参数预设 (步数/CFG)",
    "StyleTextGenerator": "Linuo风格文本生成器 (仅文本)",
    "风格条件混合器 (修复版)": "Linuo风格条件混合器 (增强版)",
    "ModelSelector": "Linuo模型任意选择器 (3输入)",
    "ConditioningSelector": "Linuo条件任意选择器 (3输入)",
    "GenericSelector4": "Linuo通用任意选择器 (4输入)",
    "Linuo图生图参数": "Linuo图生图参数 (整合缩放+编码+参数)",
    "Linuo文生图参数": "Linuo文生图参数 (整合尺寸+参数)",
    "Linuo控制发散混合出图设置": "Linuo控制发散混合出图设置 (含输出模式选择)",
}

WEB_DIRECTORY = "./web"
__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']