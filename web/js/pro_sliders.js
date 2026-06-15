import { app } from "../../../scripts/app.js";

app.registerExtension({
    name: "Comfy.LinuoProPack.Dynamic",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        // ---------- 自定义滑块：动态步长（幅度2%）----------
        if (nodeData.name === "Slider_Custom") {
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                const result = onNodeCreated?.apply(this, arguments);
                setTimeout(() => {
                    const minWidget = this.widgets?.find(w => w.name === "最小值");
                    const maxWidget = this.widgets?.find(w => w.name === "最大值");
                    const valWidget = this.widgets?.find(w => w.name === "当前值");
                    
                    const updateStepAndClamp = () => {
                        if (!minWidget || !maxWidget || !valWidget) return;
                        let minVal = parseFloat(minWidget.value);
                        let maxVal = parseFloat(maxWidget.value);
                        if (minVal >= maxVal) maxVal = minVal + 0.001;
                        const range = maxVal - minVal;
                        const step = range * 0.02;
                        valWidget.options.step = step;
                        valWidget.options.min = minVal;
                        valWidget.options.max = maxVal;
                        if (valWidget.inputEl) {
                            valWidget.inputEl.step = step;
                            valWidget.inputEl.min = minVal;
                            valWidget.inputEl.max = maxVal;
                            updateSliderFill(valWidget.inputEl, minVal, maxVal);
                        }
                        if (valWidget.sliderEl) {
                            valWidget.sliderEl.step = step;
                            valWidget.sliderEl.min = minVal;
                            valWidget.sliderEl.max = maxVal;
                            updateSliderFill(valWidget.sliderEl, minVal, maxVal);
                        }
                        let curVal = parseFloat(valWidget.value);
                        if (curVal < minVal) valWidget.value = minVal;
                        if (curVal > maxVal) valWidget.value = maxVal;
                    };
                    
                    if (minWidget) minWidget.callback = updateStepAndClamp;
                    if (maxWidget) maxWidget.callback = updateStepAndClamp;
                    updateStepAndClamp();
                }, 50);
                return result;
            };
        }

        // ---------- 空Latent预设：动态显示自定义宽高 ----------
        if (nodeData.name === "EmptyLatentPreset") {
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                const result = onNodeCreated?.apply(this, arguments);
                setTimeout(() => {
                    const presetWidget = this.widgets?.find(w => w.name === "预设");
                    const orientationWidget = this.widgets?.find(w => w.name === "横竖屏切换");
                    const widthWidget = this.widgets?.find(w => w.name === "自定义宽度");
                    const heightWidget = this.widgets?.find(w => w.name === "自定义高度");

                    const toggleCustomInputs = () => {
                        const isCustom = presetWidget.value === "自定义";
                        widthWidget.visible = isCustom;
                        heightWidget.visible = isCustom;
                        if (this.onResize) this.onResize();
                        if (this.graph) this.graph.setDirtyCanvas(true);
                    };

                    const updateDimensions = () => {
                        if (presetWidget.value !== "自定义") {
                            let presetVal = presetWidget.value;
                            let orientation = orientationWidget.value;
                            let longSide = 1024;
                            let ratio = 16/9;
                            if (presetVal === "4:3_1024") { longSide = 1024; ratio = 4/3; }
                            else if (presetVal === "16:9_1024") { longSide = 1024; ratio = 16/9; }
                            else if (presetVal === "4:3_1600") { longSide = 1600; ratio = 4/3; }
                            else if (presetVal === "16:9_1600") { longSide = 1600; ratio = 16/9; }
                            else if (presetVal === "4:3_2024") { longSide = 2024; ratio = 4/3; }
                            else if (presetVal === "16:9_2024") { longSide = 2024; ratio = 16/9; }
                            else if (presetVal === "4:3_2500") { longSide = 2500; ratio = 4/3; }
                            else if (presetVal === "16:9_2500") { longSide = 2500; ratio = 16/9; }
                            let w, h;
                            if (orientation === "横屏") {
                                w = longSide;
                                h = Math.floor(longSide / ratio);
                            } else {
                                h = longSide;
                                w = Math.floor(longSide / ratio);
                            }
                            w = (Math.floor(w / 8)) * 8;
                            h = (Math.floor(h / 8)) * 8;
                            widthWidget.value = w;
                            heightWidget.value = h;
                        }
                        toggleCustomInputs();
                    };

                    if (presetWidget) presetWidget.callback = updateDimensions;
                    if (orientationWidget) orientationWidget.callback = updateDimensions;
                    updateDimensions();
                }, 50);
                return result;
            };
        }

        // ---------- 为所有滑块节点添加横向条状填充样式 ----------
        function updateSliderFill(inputEl, minVal, maxVal) {
            if (!inputEl) return;
            const val = parseFloat(inputEl.value);
            const percent = (val - minVal) / (maxVal - minVal) * 100;
            // 设置背景为线性渐变，填充部分为蓝色（可自定义颜色）
            inputEl.style.background = `linear-gradient(to right, #4a9eff 0%, #4a9eff ${percent}%, #e0e0e0 ${percent}%, #e0e0e0 100%)`;
        }

        function styleSliderWidget(widget, node) {
            if (!widget || !widget.inputEl) return;
            const inputEl = widget.inputEl;
            if (inputEl.type !== 'range') return;
            // 获取当前 min/max
            let minVal = parseFloat(widget.options.min);
            let maxVal = parseFloat(widget.options.max);
            if (isNaN(minVal)) minVal = widget.min !== undefined ? widget.min : 0;
            if (isNaN(maxVal)) maxVal = widget.max !== undefined ? widget.max : 1;
            // 初始填充
            updateSliderFill(inputEl, minVal, maxVal);
            // 监听 input 事件动态更新填充
            inputEl.addEventListener('input', () => {
                updateSliderFill(inputEl, minVal, maxVal);
            });
            // 如果 widget 有回调（如值变化），也更新填充
            const originalCallback = widget.callback;
            widget.callback = function() {
                if (originalCallback) originalCallback.apply(this, arguments);
                updateSliderFill(inputEl, minVal, maxVal);
            };
        }

        // 针对所有数值滑块节点
        const sliderNodeNames = ["Slider_0_1", "Slider_0_10", "Slider_0_100", "Slider_Custom"];
        if (sliderNodeNames.includes(nodeData.name)) {
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                const result = onNodeCreated?.apply(this, arguments);
                setTimeout(() => {
                    // 找到 value 或 当前值 widget
                    let valWidget = null;
                    if (nodeData.name === "Slider_Custom") {
                        valWidget = this.widgets?.find(w => w.name === "当前值");
                    } else {
                        valWidget = this.widgets?.find(w => w.name === "value");
                    }
                    if (valWidget) {
                        styleSliderWidget(valWidget, this);
                        // 如果 min/max 可能动态变化（Slider_Custom），需要额外监听
                        if (nodeData.name === "Slider_Custom") {
                            const minWidget = this.widgets?.find(w => w.name === "最小值");
                            const maxWidget = this.widgets?.find(w => w.name === "最大值");
                            if (minWidget && maxWidget) {
                                const updateRangeAndFill = () => {
                                    let minVal = parseFloat(minWidget.value);
                                    let maxVal = parseFloat(maxWidget.value);
                                    if (isNaN(minVal)) minVal = 0;
                                    if (isNaN(maxVal)) maxVal = 1;
                                    valWidget.options.min = minVal;
                                    valWidget.options.max = maxVal;
                                    if (valWidget.inputEl) {
                                        valWidget.inputEl.min = minVal;
                                        valWidget.inputEl.max = maxVal;
                                        updateSliderFill(valWidget.inputEl, minVal, maxVal);
                                    }
                                };
                                minWidget.callback = updateRangeAndFill;
                                maxWidget.callback = updateRangeAndFill;
                            }
                        }
                    }
                }, 100);
                return result;
            };
        }
    }
});