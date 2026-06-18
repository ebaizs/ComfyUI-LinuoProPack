import { app } from "../../../scripts/app.js";

// 预设映射表（与后端 PRESET_MAP 保持一致）
const PRESET_MAP = {
    "4步加速": { steps: 4, cfg: 1.0 },
    "8步加速": { steps: 8, cfg: 1.0 },
    "flux中质量": { steps: 20, cfg: 3.5 },
    "flux高质量": { steps: 30, cfg: 4 },
    "qwen中质量": { steps: 20, cfg: 2.5 },
    "qwen高质量": { steps: 50, cfg: 4.0 },
};

app.registerExtension({
    name: "Comfy.LinuoProPack.PresetSync",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const result = onNodeCreated?.apply(this, arguments);
            setTimeout(() => {
                // 查找预设 widget，支持两种名称
                const presetWidget = this.widgets?.find(w => w.name === "预设" || w.name === "采样预设");
                const stepsWidget = this.widgets?.find(w => w.name === "自定义步数");
                const cfgWidget = this.widgets?.find(w => w.name === "自定义CFG");
                if (!presetWidget || !stepsWidget || !cfgWidget) {
                    // 不是目标节点，跳过
                    return;
                }
                console.log(`PresetSync: 绑定节点 ${this.type} (ID: ${this.id})，预设控件名: ${presetWidget.name}`);

                const updatePresetValues = () => {
                    const preset = presetWidget.value;
                    if (preset === "自定义") {
                        // 用户选择自定义时不自动修改
                        return;
                    }
                    const presetData = PRESET_MAP[preset];
                    if (!presetData) return;
                    // 更新步数
                    if (stepsWidget.value !== presetData.steps) {
                        stepsWidget.value = presetData.steps;
                        if (stepsWidget.inputEl) {
                            stepsWidget.inputEl.value = presetData.steps;
                            stepsWidget.inputEl.dispatchEvent(new Event('change', { bubbles: true }));
                        }
                        if (stepsWidget.callback) stepsWidget.callback(presetData.steps);
                    }
                    // 更新 CFG
                    if (cfgWidget.value !== presetData.cfg) {
                        cfgWidget.value = presetData.cfg;
                        if (cfgWidget.inputEl) {
                            cfgWidget.inputEl.value = presetData.cfg;
                            cfgWidget.inputEl.dispatchEvent(new Event('change', { bubbles: true }));
                        }
                        if (cfgWidget.callback) cfgWidget.callback(presetData.cfg);
                    }
                };

                const originalCallback = presetWidget.callback;
                presetWidget.callback = function (value) {
                    if (originalCallback) originalCallback.call(this, value);
                    updatePresetValues();
                };
                // 初始执行一次，填充默认预设的值
                setTimeout(updatePresetValues, 100);
            }, 200);
            return result;
        };
    }
});