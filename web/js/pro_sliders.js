import { app } from "../../../scripts/app.js";

// 采样预设映射表
const STEPS_PRESET_MAP = {
    "4步加速": { steps: 4, cfg: 1.0 },
    "8步加速": { steps: 8, cfg: 1.0 },
    "flux中质量": { steps: 20, cfg: 3.5 },
    "flux高质量": { steps: 30, cfg: 4 },
    "qwen中质量": { steps: 20, cfg: 2.5 },
    "qwen高质量": { steps: 50, cfg: 4.0 },
};

// 尺寸预设映射表（长边与比例）
const SIZE_PRESET_MAP = {
    "4:3_1024": { longSide: 1024, ratio: 4/3 },
    "16:9_1024": { longSide: 1024, ratio: 16/9 },
    "4:3_1600": { longSide: 1600, ratio: 4/3 },
    "16:9_1600": { longSide: 1600, ratio: 16/9 },
    "4:3_2024": { longSide: 2024, ratio: 4/3 },
    "16:9_2024": { longSide: 2024, ratio: 16/9 },
    "4:3_2500": { longSide: 2500, ratio: 4/3 },
    "16:9_2500": { longSide: 2500, ratio: 16/9 },
};

app.registerExtension({
    name: "Comfy.LinuoProPack.PresetSync",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const result = onNodeCreated?.apply(this, arguments);
            setTimeout(() => {
                // ----- 采样预设联动 -----
                const presetWidget = this.widgets?.find(w => w.name === "采样预设" || w.name === "预设");
                const stepsWidget = this.widgets?.find(w => w.name === "自定义步数");
                const cfgWidget = this.widgets?.find(w => w.name === "自定义CFG");
                if (presetWidget && stepsWidget && cfgWidget) {
                    console.log(`PresetSync: 绑定采样预设 (节点 ${this.type})`);
                    const updateSteps = () => {
                        const preset = presetWidget.value;
                        const data = STEPS_PRESET_MAP[preset];
                        if (!data) return;
                        // 更新步数
                        if (stepsWidget.value !== data.steps) {
                            stepsWidget.value = data.steps;
                            if (stepsWidget.inputEl) {
                                stepsWidget.inputEl.value = data.steps;
                                stepsWidget.inputEl.dispatchEvent(new Event('change', { bubbles: true }));
                            }
                            if (stepsWidget.callback) stepsWidget.callback(data.steps);
                        }
                        // 更新 CFG
                        if (cfgWidget.value !== data.cfg) {
                            cfgWidget.value = data.cfg;
                            if (cfgWidget.inputEl) {
                                cfgWidget.inputEl.value = data.cfg;
                                cfgWidget.inputEl.dispatchEvent(new Event('change', { bubbles: true }));
                            }
                            if (cfgWidget.callback) cfgWidget.callback(data.cfg);
                        }
                    };
                    const origCallback = presetWidget.callback;
                    presetWidget.callback = function(value) {
                        if (origCallback) origCallback.call(this, value);
                        updateSteps();
                    };
                    setTimeout(updateSteps, 100);
                }

                // ----- 尺寸预设联动（仅针对 LinuoTxt2ImgParams 节点） -----
                const sizePresetWidget = this.widgets?.find(w => w.name === "尺寸预设");
                const orientationWidget = this.widgets?.find(w => w.name === "横竖屏切换");
                const widthWidget = this.widgets?.find(w => w.name === "自定义宽度");
                const heightWidget = this.widgets?.find(w => w.name === "自定义高度");
                if (sizePresetWidget && orientationWidget && widthWidget && heightWidget) {
                    console.log(`PresetSync: 绑定尺寸预设 (节点 ${this.type})`);
                    const updateSize = () => {
                        const preset = sizePresetWidget.value;
                        const data = SIZE_PRESET_MAP[preset];
                        if (!data) return;
                        const orientation = orientationWidget.value;
                        let w, h;
                        if (orientation === "横屏") {
                            w = data.longSide;
                            h = Math.round(data.longSide / data.ratio);
                        } else {
                            h = data.longSide;
                            w = Math.round(data.longSide / data.ratio);
                        }
                        // 确保8的倍数
                        w = Math.round(w / 8) * 8;
                        h = Math.round(h / 8) * 8;
                        if (widthWidget.value !== w) {
                            widthWidget.value = w;
                            if (widthWidget.inputEl) {
                                widthWidget.inputEl.value = w;
                                widthWidget.inputEl.dispatchEvent(new Event('change', { bubbles: true }));
                            }
                            if (widthWidget.callback) widthWidget.callback(w);
                        }
                        if (heightWidget.value !== h) {
                            heightWidget.value = h;
                            if (heightWidget.inputEl) {
                                heightWidget.inputEl.value = h;
                                heightWidget.inputEl.dispatchEvent(new Event('change', { bubbles: true }));
                            }
                            if (heightWidget.callback) heightWidget.callback(h);
                        }
                    };
                    // 监听尺寸预设变化
                    const origSizeCallback = sizePresetWidget.callback;
                    sizePresetWidget.callback = function(value) {
                        if (origSizeCallback) origSizeCallback.call(this, value);
                        updateSize();
                    };
                    // 监听横竖屏切换变化
                    const origOriCallback = orientationWidget.callback;
                    orientationWidget.callback = function(value) {
                        if (origOriCallback) origOriCallback.call(this, value);
                        updateSize();
                    };
                    setTimeout(updateSize, 100);
                }
            }, 200);
            return result;
        };
    }
});