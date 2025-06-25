/**
 * OpenChemIE 分子可视化组件
 * 专为化学结构展示设计的交互式可视化工具
 */

class MoleculeViewer {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        this.options = {
            width: options.width || 400,
            height: options.height || 300,
            backgroundColor: options.backgroundColor || '#f8f9fa',
            showLabels: options.showLabels !== false,
            interactive: options.interactive !== false,
            animationSpeed: options.animationSpeed || 300,
            ...options
        };
        
        this.molecules = [];
        this.selectedMolecule = null;
        this.isRendering = false;
        
        this.init();
    }
    
    init() {
        this.createSVGContainer();
        this.setupEventListeners();
        this.createTooltip();
    }
    
    createSVGContainer() {
        this.svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        this.svg.setAttribute('width', this.options.width);
        this.svg.setAttribute('height', this.options.height);
        this.svg.style.backgroundColor = this.options.backgroundColor;
        this.svg.style.borderRadius = '8px';
        this.svg.style.border = '1px solid #e9ecef';
        this.svg.style.cursor = 'pointer';
        
        // 添加渐变定义
        const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
        const gradient = document.createElementNS('http://www.w3.org/2000/svg', 'linearGradient');
        gradient.setAttribute('id', 'moleculeGradient');
        gradient.setAttribute('x1', '0%');
        gradient.setAttribute('y1', '0%');
        gradient.setAttribute('x2', '100%');
        gradient.setAttribute('y2', '100%');
        
        const stop1 = document.createElementNS('http://www.w3.org/2000/svg', 'stop');
        stop1.setAttribute('offset', '0%');
        stop1.setAttribute('stop-color', '#4a90e2');
        
        const stop2 = document.createElementNS('http://www.w3.org/2000/svg', 'stop');
        stop2.setAttribute('offset', '100%');
        stop2.setAttribute('stop-color', '#357abd');
        
        gradient.appendChild(stop1);
        gradient.appendChild(stop2);
        defs.appendChild(gradient);
        this.svg.appendChild(defs);
        
        this.container.appendChild(this.svg);
    }
    
    createTooltip() {
        this.tooltip = document.createElement('div');
        this.tooltip.className = 'molecule-tooltip';
        this.tooltip.style.cssText = `
            position: absolute;
            background: rgba(0, 0, 0, 0.8);
            color: white;
            padding: 8px 12px;
            border-radius: 4px;
            font-size: 12px;
            pointer-events: none;
            z-index: 1000;
            opacity: 0;
            transition: opacity 0.2s ease;
            backdrop-filter: blur(10px);
        `;
        document.body.appendChild(this.tooltip);
    }
    
    setupEventListeners() {
        this.svg.addEventListener('mousemove', this.handleMouseMove.bind(this));
        this.svg.addEventListener('mouseleave', this.hideTooltip.bind(this));
        this.svg.addEventListener('click', this.handleClick.bind(this));
    }
    
    addMolecule(moleculeData) {
        const molecule = {
            id: moleculeData.id || Date.now(),
            smiles: moleculeData.smiles,
            name: moleculeData.name || 'Unknown',
            confidence: moleculeData.confidence || 0,
            coordinates: moleculeData.coordinates || this.generateRandomCoordinates(),
            bonds: moleculeData.bonds || [],
            atoms: moleculeData.atoms || [],
            highlighted: false
        };
        
        this.molecules.push(molecule);
        this.renderMolecule(molecule);
        return molecule.id;
    }
    
    generateRandomCoordinates() {
        const padding = 50;
        const x = padding + Math.random() * (this.options.width - 2 * padding);
        const y = padding + Math.random() * (this.options.height - 2 * padding);
        return { x, y };
    }
    
    renderMolecule(molecule) {
        if (this.isRendering) return;
        this.isRendering = true;
        
        // 创建分子组
        const group = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        group.setAttribute('id', `molecule-${molecule.id}`);
        group.setAttribute('class', 'molecule-group');
        
        // 绘制分子骨架
        this.drawMoleculeSkeleton(group, molecule);
        
        // 添加标签
        if (this.options.showLabels) {
            this.addMoleculeLabel(group, molecule);
        }
        
        // 添加交互效果
        if (this.options.interactive) {
            this.addInteractiveEffects(group, molecule);
        }
        
        this.svg.appendChild(group);
        
        // 动画效果
        this.animateMoleculeEntry(group);
        
        this.isRendering = false;
    }
    
    drawMoleculeSkeleton(group, molecule) {
        const { x, y } = molecule.coordinates;
        const radius = 20;
        
        // 简化的分子表示 - 创建一个六边形代表分子
        const points = [];
        for (let i = 0; i < 6; i++) {
            const angle = (i * Math.PI) / 3;
            const px = x + radius * Math.cos(angle);
            const py = y + radius * Math.sin(angle);
            points.push(`${px},${py}`);
        }
        
        // 绘制分子环
        const polygon = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
        polygon.setAttribute('points', points.join(' '));
        polygon.setAttribute('fill', `url(#moleculeGradient)`);
        polygon.setAttribute('stroke', '#2c3e50');
        polygon.setAttribute('stroke-width', '2');
        polygon.setAttribute('opacity', '0.8');
        
        // 添加脉冲效果
        const animate = document.createElementNS('http://www.w3.org/2000/svg', 'animateTransform');
        animate.setAttribute('attributeName', 'transform');
        animate.setAttribute('type', 'scale');
        animate.setAttribute('values', '1;1.1;1');
        animate.setAttribute('dur', '2s');
        animate.setAttribute('repeatCount', 'indefinite');
        polygon.appendChild(animate);
        
        group.appendChild(polygon);
        
        // 添加中心点
        const centerDot = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        centerDot.setAttribute('cx', x);
        centerDot.setAttribute('cy', y);
        centerDot.setAttribute('r', '3');
        centerDot.setAttribute('fill', '#e74c3c');
        group.appendChild(centerDot);
    }
    
    addMoleculeLabel(group, molecule) {
        const { x, y } = molecule.coordinates;
        
        const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        label.setAttribute('x', x);
        label.setAttribute('y', y + 40);
        label.setAttribute('text-anchor', 'middle');
        label.setAttribute('font-family', 'Arial, sans-serif');
        label.setAttribute('font-size', '12');
        label.setAttribute('font-weight', 'bold');
        label.setAttribute('fill', '#2c3e50');
        label.textContent = molecule.name;
        
        group.appendChild(label);
        
        // 置信度指示器
        if (molecule.confidence > 0) {
            const confidenceBar = this.createConfidenceIndicator(x, y + 50, molecule.confidence);
            group.appendChild(confidenceBar);
        }
    }
    
    createConfidenceIndicator(x, y, confidence) {
        const group = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        
        // 背景条
        const bg = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        bg.setAttribute('x', x - 20);
        bg.setAttribute('y', y);
        bg.setAttribute('width', '40');
        bg.setAttribute('height', '4');
        bg.setAttribute('fill', '#ecf0f1');
        bg.setAttribute('rx', '2');
        group.appendChild(bg);
        
        // 置信度条
        const bar = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        bar.setAttribute('x', x - 20);
        bar.setAttribute('y', y);
        bar.setAttribute('width', 40 * confidence);
        bar.setAttribute('height', '4');
        bar.setAttribute('fill', this.getConfidenceColor(confidence));
        bar.setAttribute('rx', '2');
        group.appendChild(bar);
        
        return group;
    }
    
    getConfidenceColor(confidence) {
        if (confidence > 0.8) return '#27ae60';
        if (confidence > 0.6) return '#f39c12';
        return '#e74c3c';
    }
    
    addInteractiveEffects(group, molecule) {
        group.style.cursor = 'pointer';
        group.setAttribute('data-molecule-id', molecule.id);
        
        group.addEventListener('mouseenter', () => {
            this.highlightMolecule(molecule.id);
        });
        
        group.addEventListener('mouseleave', () => {
            this.unhighlightMolecule(molecule.id);
        });
    }
    
    animateMoleculeEntry(group) {
        group.style.opacity = '0';
        group.style.transform = 'scale(0.5)';
        group.style.transition = `all ${this.options.animationSpeed}ms ease-out`;
        
        setTimeout(() => {
            group.style.opacity = '1';
            group.style.transform = 'scale(1)';
        }, 50);
    }
    
    highlightMolecule(moleculeId) {
        const group = document.getElementById(`molecule-${moleculeId}`);
        if (group) {
            group.style.filter = 'drop-shadow(0 0 10px rgba(74, 144, 226, 0.6))';
            group.style.transform = 'scale(1.1)';
        }
    }
    
    unhighlightMolecule(moleculeId) {
        const group = document.getElementById(`molecule-${moleculeId}`);
        if (group) {
            group.style.filter = 'none';
            group.style.transform = 'scale(1)';
        }
    }
    
    handleMouseMove(event) {
        const rect = this.svg.getBoundingClientRect();
        const x = event.clientX - rect.left;
        const y = event.clientY - rect.top;
        
        const molecule = this.getMoleculeAt(x, y);
        if (molecule) {
            this.showTooltip(event.clientX, event.clientY, molecule);
        } else {
            this.hideTooltip();
        }
    }
    
    getMoleculeAt(x, y) {
        for (const molecule of this.molecules) {
            const dx = x - molecule.coordinates.x;
            const dy = y - molecule.coordinates.y;
            const distance = Math.sqrt(dx * dx + dy * dy);
            if (distance < 30) {
                return molecule;
            }
        }
        return null;
    }
    
    showTooltip(x, y, molecule) {
        this.tooltip.innerHTML = `
            <strong>${molecule.name}</strong><br>
            SMILES: ${molecule.smiles}<br>
            置信度: ${(molecule.confidence * 100).toFixed(1)}%
        `;
        this.tooltip.style.left = x + 10 + 'px';
        this.tooltip.style.top = y - 10 + 'px';
        this.tooltip.style.opacity = '1';
    }
    
    hideTooltip() {
        this.tooltip.style.opacity = '0';
    }
    
    handleClick(event) {
        const rect = this.svg.getBoundingClientRect();
        const x = event.clientX - rect.left;
        const y = event.clientY - rect.top;
        
        const molecule = this.getMoleculeAt(x, y);
        if (molecule) {
            this.selectMolecule(molecule.id);
            this.dispatchEvent('moleculeSelected', molecule);
        }
    }
    
    selectMolecule(moleculeId) {
        // 取消之前的选择
        if (this.selectedMolecule) {
            this.unhighlightMolecule(this.selectedMolecule);
        }
        
        this.selectedMolecule = moleculeId;
        this.highlightMolecule(moleculeId);
    }
    
    dispatchEvent(eventName, data) {
        const event = new CustomEvent(eventName, { detail: data });
        this.container.dispatchEvent(event);
    }
    
    clear() {
        this.molecules = [];
        this.selectedMolecule = null;
        while (this.svg.children.length > 1) { // 保留defs
            this.svg.removeChild(this.svg.lastChild);
        }
    }
    
    resize(width, height) {
        this.options.width = width;
        this.options.height = height;
        this.svg.setAttribute('width', width);
        this.svg.setAttribute('height', height);
    }
    
    exportAsSVG() {
        const serializer = new XMLSerializer();
        return serializer.serializeToString(this.svg);
    }
    
    exportAsPNG() {
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        const img = new Image();
        
        return new Promise((resolve) => {
            img.onload = () => {
                canvas.width = this.options.width;
                canvas.height = this.options.height;
                ctx.drawImage(img, 0, 0);
                resolve(canvas.toDataURL('image/png'));
            };
            
            const svgData = this.exportAsSVG();
            const blob = new Blob([svgData], { type: 'image/svg+xml' });
            img.src = URL.createObjectURL(blob);
        });
    }
}

// 分子可视化工具类
class MoleculeVisualizationTools {
    static createViewer(containerId, options) {
        return new MoleculeViewer(containerId, options);
    }
    
    static parseSMILES(smiles) {
        // 简化的SMILES解析（实际应用中需要更复杂的解析器）
        return {
            atoms: smiles.length,
            rings: (smiles.match(/[0-9]/g) || []).length / 2,
            branches: (smiles.match(/[\(\)]/g) || []).length / 2
        };
    }
    
    static generateMoleculePreview(smiles, size = 100) {
        const canvas = document.createElement('canvas');
        canvas.width = size;
        canvas.height = size;
        const ctx = canvas.getContext('2d');
        
        // 简单的分子预览图
        ctx.fillStyle = '#4a90e2';
        ctx.fillRect(0, 0, size, size);
        ctx.fillStyle = 'white';
        ctx.font = '12px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('MOL', size / 2, size / 2);
        
        return canvas.toDataURL();
    }
}

// 导出到全局
window.MoleculeViewer = MoleculeViewer;
window.MoleculeVisualizationTools = MoleculeVisualizationTools; 