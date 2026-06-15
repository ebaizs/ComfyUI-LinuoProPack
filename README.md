# ComfyUI-LinuoProPack
ComfyUI-LinuoProPack
## Linuo 专业插件包 
Linuo数值滑块 (0~1, 0~10, 0~100, 自定义范围)
<img width="960" height="471" alt="1" src="https://github.com/user-attachments/assets/29575b3d-1798-4783-bad0-ef540d55f28b" />

Linuo空Latent预设 (4:3/16:9 多种长边尺寸)

<img width="664" height="285" alt="image" src="https://github.com/user-attachments/assets/2b79da52-0df5-49e3-8062-d2726316757c" />

Linuo图像+遮罩按长边缩放 (可填充遮罩漏洞)

<img width="1057" height="563" alt="image" src="https://github.com/user-attachments/assets/77fd48cd-8471-4dea-aa7c-4c286658b3f2" />

Linuo出图参数预设 (步数/CFG)

<img width="546" height="234" alt="image" src="https://github.com/user-attachments/assets/08b9483e-ace6-4cf4-b198-4884aaecadd3" />

Linuo风格文本生成器 (输出完整提示词)

<img width="846" height="504" alt="image" src="https://github.com/user-attachments/assets/55962cfe-968a-4306-ac7f-8bae15b3eec4" />

Linuo风格条件混合器 (线性插值/加权拼接)

<img width="926" height="644" alt="image" src="https://github.com/user-attachments/assets/77a9f6ab-62be-411a-8093-af7f6955045d" />


Linuo模型任意选择器 (3输入)，Linuo条件任意选择器 (3输入)，Linuo通用任意选择器 (4输入)

<img width="891" height="510" alt="image" src="https://github.com/user-attachments/assets/f6f4aa66-9e0c-4635-8120-f5a43ebec6db" />

Linuo图生图参数、Linuo文生图参数、Linuo控制发散混合出图设置

<img width="937" height="558" alt="image" src="https://github.com/user-attachments/assets/fbe19854-d3ee-412a-b2e0-b204f96bf66a" />

**问：如何安装该插件？**  
答：将 `ComfyUI-LinuoProPack` 文件夹放入 `ComfyUI/custom_nodes/` 目录，重启 ComfyUI（或刷新浏览器）。插件会自动加载，所有节点会出现在右键菜单的 `Linuo/` 分类下。

**问：数值滑块有几种？如何自定义范围？**  
答：共有四种滑块：`0～1`、`0～10`、`0～100`、`自定义范围`。自定义范围节点可输入“最小值”和“最大值”，滑块步长会自动设为范围的 2%，当前值被钳位在范围内。
**问：空 Latent 预设支持哪些尺寸？**  
答：预设比例有 4:3 和 16:9，长边尺寸包括 1024、1600、2024、2500。支持横屏/竖屏切换，也可手动输入自定义宽高（自动对齐 8 的倍数）。

**问：如何缩放图像并同时处理遮罩？**  
答：使用 `图像+遮罩按长边缩放` 节点。输入图像和可选遮罩，设定目标长边像素数，选择缩放模式（lanczos/bilinear/bicubic）。勾选“填充漏洞”后，遮罩中的孔洞和断裂线会被自动填充为完整白色区域（优先使用 scipy 孔洞填充算法，未安装则回退到形态学闭运算）。

**问：风格文本生成器和风格条件混合器有什么区别？**  
答：  
- **风格文本生成器**：只输出两个拼接好的提示词字符串（“通用提示词 + 风格描述”），不涉及 CLIP 编码，适用于任何工作流（Flux/Qwen 等）。  
- **风格条件混合器**：直接接收 CLIP 模型，输出 CONDITIONING 张量。支持“线性插值”和“加权拼接”两种混合方式，强度参数控制风格 1 的占比。

**问：风格混合方式“线性插值”和“加权拼接”哪个效果更明显？**  
答：**加权拼接**效果更明显。它保留两个完整提示词序列，仅缩放强度，生成时两种风格可同时强烈展现；线性插值则平滑过渡，但极端强度下信息可能被稀释。可根据需要切换。

**问：模型任意选择器有什么用？**  
答：左侧有三个输入口（加速模型_nunchaku、加速模型_GGUF、标准模型），通过下拉菜单选择其中一个作为输出。方便在多种模型间快速切换，无需重新连线。

**问：条件任意选择器和通用任意选择器呢？**  
答：  
- **条件任意选择器**：三个 CONDITIONING 输入（混合条件、条件1、条件2），下拉选择输出。  
- **通用任意选择器**：四个任意类型输入（`*` 通配），下拉选择输出。适合切换 latent、图像、字符串等任意数据类型。

**问：出图参数预设节点支持哪些预设？**  
答：内置“4步加速”、“8步加速”、“flux中质量”、“flux高质量”、“qwen中质量”、“qwen高质量”以及“自定义”。自动输出 steps 和 cfg 值，可直接连接采样器。

**问：图生图参数节点做什么的？**  
答：整合了图像缩放（按长边）、VAE 编码、采样参数预设。输出 latent、steps、cfg 和缩放后图像，一个节点完成图生图的前置流程。

**问：插件里的所有节点名称都带“Linuo”前缀，会与其它插件冲突吗？**  
答：不会。显示名称均已加入 “Linuo” 标识，分类也在 `Linuo/` 子菜单下，不会覆盖原生节点或其他插件节点。

**问：可以保存工作流并在另一台电脑上加载吗？**  
答：可以。插件节点信息会完整保存到 JSON 文件中。另一台电脑安装相同版本的插件即可正常加载，所有参数和连线都会保留。

**问：如果不需要某类节点，可以禁用或删除吗？**  
答：不能直接禁用单个节点，但可以删除整个插件文件夹。若只希望隐藏，可注释 `NODE_CLASS_MAPPINGS` 中对应的条目，重启后该节点即不再显示。

**问：遇到报错或功能异常怎么办？**  
答：请检查 ComfyUI 控制台输出的错误信息。常见问题：`scipy` 未安装导致填充漏洞回退到闭运算（不影响主功能）；Python 版本不匹配导致滑块样式失效（需使用支持 `input` 事件的现代浏览器）。可更新插件或提交 Issue。

**问：插件会持续更新吗？**  
答：目前稳定版本已满足大部分需求。如有新功能建议或修复，可关注插件仓库更新。

<img width="952" height="606" alt="1" src="https://github.com/user-attachments/assets/fb6b4eb9-aeed-4991-a4d7-a5c7be2f517d" />
