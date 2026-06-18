import { app } from "../../../scripts/app.js";

app.registerExtension({
    name: "Comfy.LinuoProPack.PercentageLabel",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        const sliderNames = ["Slider_0_1", "Slider_0_10", "Slider_0_100", "Slider_Custom"];
        if (!sliderNames.includes(nodeData.name)) return;

        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const result = onNodeCreated?.apply(this, arguments);
            setTimeout(() => {
                let valWidget = null;
                if (nodeData.name === "Slider_Custom") {
                    valWidget = this.widgets?.find(w => w.name === "当前值");
                } else {
                    valWidget = this.widgets?.find(w => w.name === "value");
                }
                if (!valWidget || !valWidget.inputEl || valWidget.inputEl.type !== 'range') return;
                const slider = valWidget.inputEl;
                // 创建百分比标签
                const percentSpan = document.createElement('span');
                percentSpan.style.cssText = `
                    display: inline-block;
                    margin-left: 10px;
                    font-size: 12px;
                    color: #4a9eff;
                    font-weight: bold;
                    min-width: 45px;
                    text-align: right;
                `;
                const updatePercent = () => {
                    const min = parseFloat(slider.min) || 0;
                    const max = parseFloat(slider.max) || 1;
                    const val = parseFloat(slider.value);
                    const percent = ((val - min) / (max - min)) * 100;
                    percentSpan.textContent = `${Math.round(percent)}%`;
                };
                slider.parentNode.insertBefore(percentSpan, slider.nextSibling);
                slider.addEventListener('input', updatePercent);
                slider.addEventListener('change', updatePercent);
                updatePercent();
                // 监听 min/max 变化（自定义滑块）
                if (nodeData.name === "Slider_Custom") {
                    const minWidget = this.widgets?.find(w => w.name === "最小值");
                    const maxWidget = this.widgets?.find(w => w.name === "最大值");
                    if (minWidget && minWidget.inputEl) {
                        minWidget.inputEl.addEventListener('change', updatePercent);
                    }
                    if (maxWidget && maxWidget.inputEl) {
                        maxWidget.inputEl.addEventListener('change', updatePercent);
                    }
                }
            }, 200);
            return result;
        };
    }
});