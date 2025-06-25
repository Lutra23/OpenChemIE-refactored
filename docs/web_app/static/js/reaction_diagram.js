/**
 * OpenChemIE 反应流程图组件
 * 专为化学反应可视化设计的交互式图表工具
 */

class ReactionDiagram {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        this.options = {
            width: options.width || 800,
            height: options.height || 400,
            backgroundColor: options.backgroundColor || '#f8f9fa',
            showArrows: options.showArrows !== false,
            animateFlow: options.animateFlow !== false,
            autoLayout: options.autoLayout !== false,
            theme: options.theme || 'light',
            ...options
        };
        
        this.reactions = [];
        this.selectedReaction = null;
        this.isLayouting = false;
        
        this.init();
    }
    
    init() {
        this.createSVGContainer();
        this.setupEventListeners();
        this.createTooltip();
        this.loadTheme();
    }
    
    createSVGContainer() {
        this.svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        this.svg.setAttribute('width', this.options.width);
        this.svg.setAttribute('height', this.options.height);
        this.svg.style.backgroundColor = this.options.backgroundColor;
        this.svg.style.borderRadius = '12px';
        this.svg.style.border = '1px solid #e9ecef';
        this.svg.style.overflow = 'hidden';
        
        // 创建定义部分
        this.createDefinitions();
        
        // 创建层级
        this.createLayers();
        
        this.container.appendChild(this.svg);
    }
    
    createDefinitions() {
        const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
        
        // 箭头标记
        const arrowMarker = document.createElementNS('http://www.w3.org/2000/svg', 'marker');
        arrowMarker.setAttribute('id', 'arrowhead');
        arrowMarker.setAttribute('markerWidth', '10');
        arrowMarker.setAttribute('markerHeight', '7');
        arrowMarker.setAttribute('refX', '10');
        arrowMarker.setAttribute('refY', '3.5');
        arrowMarker.setAttribute('orient', 'auto');
        
        const arrowPath = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
        arrowPath.setAttribute('points', '0 0, 10 3.5, 0 7');
        arrowPath.setAttribute('fill', '#3498db');
        arrowMarker.appendChild(arrowPath);
        
        // 渐变效果
        const gradient = document.createElementNS('http://www.w3.org/2000/svg', 'linearGradient');
        gradient.setAttribute('id', 'reactionGradient');
        gradient.setAttribute('x1', '0%');
        gradient.setAttribute('y1', '0%');
        gradient.setAttribute('x2', '100%');
        gradient.setAttribute('y2', '0%');
        
        const stop1 = document.createElementNS('http://www.w3.org/2000/svg', 'stop');
        stop1.setAttribute('offset', '0%');
        stop1.setAttribute('stop-color', '#3498db');
        stop1.setAttribute('stop-opacity', '0.1');
        
        const stop2 = document.createElementNS('http://www.w3.org/2000/svg', 'stop');
        stop2.setAttribute('offset', '100%');
        stop2.setAttribute('stop-color', '#2980b9');
        stop2.setAttribute('stop-opacity', '0.3');
        
        gradient.appendChild(stop1);
        gradient.appendChild(stop2);
        
        // 发光效果
        const glowFilter = document.createElementNS('http://www.w3.org/2000/svg', 'filter');
        glowFilter.setAttribute('id', 'glow');
        
        const feGaussianBlur = document.createElementNS('http://www.w3.org/2000/svg', 'feGaussianBlur');
        feGaussianBlur.setAttribute('stdDeviation', '3');
        feGaussianBlur.setAttribute('result', 'coloredBlur');
        
        const feMerge = document.createElementNS('http://www.w3.org/2000/svg', 'feMerge');
        const feMergeNode1 = document.createElementNS('http://www.w3.org/2000/svg', 'feMergeNode');
        feMergeNode1.setAttribute('in', 'coloredBlur');
        const feMergeNode2 = document.createElementNS('http://www.w3.org/2000/svg', 'feMergeNode');
        feMergeNode2.setAttribute('in', 'SourceGraphic');
        
        feMerge.appendChild(feMergeNode1);
        feMerge.appendChild(feMergeNode2);
        glowFilter.appendChild(feGaussianBlur);
        glowFilter.appendChild(feMerge);
        
        defs.appendChild(arrowMarker);
        defs.appendChild(gradient);
        defs.appendChild(glowFilter);
        this.svg.appendChild(defs);
    }
    
    createLayers() {
        // 背景层
        this.backgroundLayer = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        this.backgroundLayer.setAttribute('class', 'background-layer');
        
        // 连接线层
        this.connectionLayer = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        this.connectionLayer.setAttribute('class', 'connection-layer');
        
        // 分子层
        this.moleculeLayer = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        this.moleculeLayer.setAttribute('class', 'molecule-layer');
        
        // 条件层
        this.conditionLayer = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        this.conditionLayer.setAttribute('class', 'condition-layer');
        
        // 标注层
        this.annotationLayer = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        this.annotationLayer.setAttribute('class', 'annotation-layer');
        
        this.svg.appendChild(this.backgroundLayer);
        this.svg.appendChild(this.connectionLayer);
        this.svg.appendChild(this.moleculeLayer);
        this.svg.appendChild(this.conditionLayer);
        this.svg.appendChild(this.annotationLayer);
    }
    
    loadTheme() {
        const themes = {
            light: {
                background: '#ffffff',
                primary: '#3498db',
                secondary: '#2ecc71',
                text: '#2c3e50',
                border: '#bdc3c7'
            },
            dark: {
                background: '#2c3e50',
                primary: '#3498db',
                secondary: '#e74c3c',
                text: '#ecf0f1',
                border: '#34495e'
            },
            scientific: {
                background: '#f7f9fc',
                primary: '#4a90e2',
                secondary: '#7ed321',
                text: '#4a4a4a',
                border: '#d0d0d0'
            }
        };
        
        this.currentTheme = themes[this.options.theme] || themes.light;
    }
    
    createTooltip() {
        this.tooltip = document.createElement('div');
        this.tooltip.className = 'reaction-tooltip';
        this.tooltip.style.cssText = `
            position: absolute;
            background: rgba(44, 62, 80, 0.95);
            color: white;
            padding: 12px 16px;
            border-radius: 8px;
            font-size: 13px;
            pointer-events: none;
            z-index: 1000;
            opacity: 0;
            transition: all 0.3s ease;
            backdrop-filter: blur(10px);
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
            max-width: 300px;
        `;
        document.body.appendChild(this.tooltip);
    }
    
    setupEventListeners() {
        this.svg.addEventListener('mousemove', this.handleMouseMove.bind(this));
        this.svg.addEventListener('mouseleave', this.hideTooltip.bind(this));
        this.svg.addEventListener('click', this.handleClick.bind(this));
        
        // 响应式调整
        window.addEventListener('resize', this.handleResize.bind(this));
    }
    
    addReaction(reactionData) {
        const reaction = {
            id: reactionData.id || Date.now(),
            reactants: reactionData.reactants || [],
            products: reactionData.products || [],
            conditions: reactionData.conditions || [],
            yield: reactionData.yield || null,
            time: reactionData.time || null,
            temperature: reactionData.temperature || null,
            catalyst: reactionData.catalyst || null,
            coordinates: reactionData.coordinates || this.generateAutoLayout(),
            confidence: reactionData.confidence || 0
        };
        
        this.reactions.push(reaction);
        this.renderReaction(reaction);
        return reaction.id;
    }
    
    generateAutoLayout() {
        if (!this.options.autoLayout) {
            return {
                reactants: { x: 100, y: 200 },
                arrow: { x: 400, y: 200 },
                products: { x: 700, y: 200 },
                conditions: { x: 400, y: 150 }
            };
        }
        
        // 智能布局算法
        const reactionCount = this.reactions.length;
        const verticalSpacing = this.options.height / (reactionCount + 1);
        const y = verticalSpacing * (reactionCount + 1);
        
        return {
            reactants: { x: this.options.width * 0.15, y },
            arrow: { x: this.options.width * 0.5, y },
            products: { x: this.options.width * 0.85, y },
            conditions: { x: this.options.width * 0.5, y: y - 40 }
        };
    }
    
    renderReaction(reaction) {
        if (this.isLayouting) return;
        this.isLayouting = true;
        
        const group = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        group.setAttribute('id', `reaction-${reaction.id}`);
        group.setAttribute('class', 'reaction-group');
        
        // 渲染反应物
        this.renderReactants(group, reaction);
        
        // 渲染箭头
        this.renderArrow(group, reaction);
        
        // 渲染产物
        this.renderProducts(group, reaction);
        
        // 渲染条件
        this.renderConditions(group, reaction);
        
        // 渲染连接线
        this.renderConnections(group, reaction);
        
        this.svg.appendChild(group);
        
        // 添加入场动画
        this.animateReactionEntry(group);
        
        this.isLayouting = false;
    }
    
    renderReactants(group, reaction) {
        const { x, y } = reaction.coordinates.reactants;
        
        reaction.reactants.forEach((reactant, index) => {
            const reactantGroup = this.createMoleculeNode(
                reactant,
                { x: x - index * 60, y: y + index * 30 },
                'reactant'
            );
            group.appendChild(reactantGroup);
        });
    }
    
    renderProducts(group, reaction) {
        const { x, y } = reaction.coordinates.products;
        
        reaction.products.forEach((product, index) => {
            const productGroup = this.createMoleculeNode(
                product,
                { x: x + index * 60, y: y + index * 30 },
                'product'
            );
            group.appendChild(productGroup);
        });
    }
    
    createMoleculeNode(molecule, position, type) {
        const group = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        group.setAttribute('class', `molecule-node ${type}`);
        
        // 分子圆圈
        const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        circle.setAttribute('cx', position.x);
        circle.setAttribute('cy', position.y);
        circle.setAttribute('r', '25');
        circle.setAttribute('fill', this.getMoleculeColor(type));
        circle.setAttribute('stroke', this.currentTheme.border);
        circle.setAttribute('stroke-width', '2');
        circle.setAttribute('opacity', '0.8');
        
        // 悬停效果
        circle.setAttribute('filter', 'url(#glow)');
        
        // 分子标签
        const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        label.setAttribute('x', position.x);
        label.setAttribute('y', position.y + 5);
        label.setAttribute('text-anchor', 'middle');
        label.setAttribute('font-family', 'Arial, sans-serif');
        label.setAttribute('font-size', '10');
        label.setAttribute('font-weight', 'bold');
        label.setAttribute('fill', 'white');
        label.textContent = molecule.name || 'MOL';
        
        // 分子名称
        const nameLabel = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        nameLabel.setAttribute('x', position.x);
        nameLabel.setAttribute('y', position.y + 45);
        nameLabel.setAttribute('text-anchor', 'middle');
        nameLabel.setAttribute('font-family', 'Arial, sans-serif');
        nameLabel.setAttribute('font-size', '12');
        nameLabel.setAttribute('fill', this.currentTheme.text);
        nameLabel.textContent = molecule.name || 'Unknown';
        
        group.appendChild(circle);
        group.appendChild(label);
        group.appendChild(nameLabel);
        
        // 交互效果
        this.addMoleculeInteraction(group, molecule);
        
        return group;
    }
    
    getMoleculeColor(type) {
        const colors = {
            reactant: '#3498db',
            product: '#2ecc71',
            catalyst: '#f39c12',
            solvent: '#9b59b6'
        };
        return colors[type] || '#95a5a6';
    }
    
    renderArrow(group, reaction) {
        const { x, y } = reaction.coordinates.arrow;
        const startX = reaction.coordinates.reactants.x + 50;
        const endX = reaction.coordinates.products.x - 50;
        
        // 箭头路径
        const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        const pathData = `M ${startX} ${y} Q ${x} ${y - 20} ${endX} ${y}`;
        path.setAttribute('d', pathData);
        path.setAttribute('stroke', this.currentTheme.primary);
        path.setAttribute('stroke-width', '3');
        path.setAttribute('fill', 'none');
        path.setAttribute('marker-end', 'url(#arrowhead)');
        
        // 箭头动画
        if (this.options.animateFlow) {
            const totalLength = path.getTotalLength();
            path.style.strokeDasharray = totalLength;
            path.style.strokeDashoffset = totalLength;
            
            const animate = document.createElementNS('http://www.w3.org/2000/svg', 'animate');
            animate.setAttribute('attributeName', 'stroke-dashoffset');
            animate.setAttribute('from', totalLength);
            animate.setAttribute('to', '0');
            animate.setAttribute('dur', '2s');
            animate.setAttribute('repeatCount', 'indefinite');
            path.appendChild(animate);
        }
        
        group.appendChild(path);
    }
    
    renderConditions(group, reaction) {
        const { x, y } = reaction.coordinates.conditions;
        
        if (reaction.conditions.length === 0) return;
        
        // 条件框
        const conditionBox = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        const boxWidth = 120;
        const boxHeight = 30;
        
        conditionBox.setAttribute('x', x - boxWidth / 2);
        conditionBox.setAttribute('y', y - boxHeight / 2);
        conditionBox.setAttribute('width', boxWidth);
        conditionBox.setAttribute('height', boxHeight);
        conditionBox.setAttribute('fill', 'url(#reactionGradient)');
        conditionBox.setAttribute('stroke', this.currentTheme.border);
        conditionBox.setAttribute('stroke-width', '1');
        conditionBox.setAttribute('rx', '8');
        
        // 条件文本
        const conditionText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        conditionText.setAttribute('x', x);
        conditionText.setAttribute('y', y + 3);
        conditionText.setAttribute('text-anchor', 'middle');
        conditionText.setAttribute('font-family', 'Arial, sans-serif');
        conditionText.setAttribute('font-size', '10');
        conditionText.setAttribute('fill', this.currentTheme.text);
        
        const conditionsStr = reaction.conditions.slice(0, 2).map(c => c.text || c.name).join(', ');
        conditionText.textContent = conditionsStr.length > 15 ? conditionsStr.substring(0, 15) + '...' : conditionsStr;
        
        group.appendChild(conditionBox);
        group.appendChild(conditionText);
        
        // 额外信息
        this.addConditionDetails(group, reaction, x, y + 25);
    }
    
    addConditionDetails(group, reaction, x, y) {
        const details = [];
        if (reaction.temperature) details.push(`${reaction.temperature}°C`);
        if (reaction.time) details.push(reaction.time);
        if (reaction.yield) details.push(`${reaction.yield}%`);
        
        if (details.length > 0) {
            const detailText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            detailText.setAttribute('x', x);
            detailText.setAttribute('y', y);
            detailText.setAttribute('text-anchor', 'middle');
            detailText.setAttribute('font-family', 'Arial, sans-serif');
            detailText.setAttribute('font-size', '9');
            detailText.setAttribute('fill', this.currentTheme.text);
            detailText.setAttribute('opacity', '0.7');
            detailText.textContent = details.join(' • ');
            
            group.appendChild(detailText);
        }
    }
    
    renderConnections(group, reaction) {
        // 这里可以添加更复杂的连接线逻辑
        // 比如反应机理、副反应等
    }
    
    addMoleculeInteraction(group, molecule) {
        group.style.cursor = 'pointer';
        group.setAttribute('data-molecule-data', JSON.stringify(molecule));
        
        group.addEventListener('mouseenter', () => {
            group.style.transform = 'scale(1.1)';
            group.style.transition = 'transform 0.2s ease';
        });
        
        group.addEventListener('mouseleave', () => {
            group.style.transform = 'scale(1)';
        });
    }
    
    animateReactionEntry(group) {
        group.style.opacity = '0';
        group.style.transform = 'translateY(20px)';
        group.style.transition = 'all 0.6s ease-out';
        
        setTimeout(() => {
            group.style.opacity = '1';
            group.style.transform = 'translateY(0)';
        }, 100);
    }
    
    handleMouseMove(event) {
        const rect = this.svg.getBoundingClientRect();
        const x = event.clientX - rect.left;
        const y = event.clientY - rect.top;
        
        const element = document.elementFromPoint(event.clientX, event.clientY);
        const moleculeGroup = element.closest('.molecule-node');
        
        if (moleculeGroup) {
            const moleculeData = JSON.parse(moleculeGroup.getAttribute('data-molecule-data'));
            this.showTooltip(event.clientX, event.clientY, moleculeData);
        } else {
            this.hideTooltip();
        }
    }
    
    showTooltip(x, y, data) {
        let content = `<strong>${data.name || 'Unknown Molecule'}</strong>`;
        if (data.smiles) content += `<br>SMILES: ${data.smiles}`;
        if (data.formula) content += `<br>分子式: ${data.formula}`;
        if (data.mw) content += `<br>分子量: ${data.mw}`;
        
        this.tooltip.innerHTML = content;
        this.tooltip.style.left = x + 15 + 'px';
        this.tooltip.style.top = y - 15 + 'px';
        this.tooltip.style.opacity = '1';
        this.tooltip.style.transform = 'translateY(0)';
    }
    
    hideTooltip() {
        this.tooltip.style.opacity = '0';
        this.tooltip.style.transform = 'translateY(-10px)';
    }
    
    handleClick(event) {
        const element = event.target;
        const reactionGroup = element.closest('.reaction-group');
        
        if (reactionGroup) {
            const reactionId = reactionGroup.id.replace('reaction-', '');
            this.selectReaction(reactionId);
        }
    }
    
    selectReaction(reactionId) {
        // 取消之前的选择
        if (this.selectedReaction) {
            const prevGroup = document.getElementById(`reaction-${this.selectedReaction}`);
            if (prevGroup) {
                prevGroup.style.filter = 'none';
            }
        }
        
        this.selectedReaction = reactionId;
        const group = document.getElementById(`reaction-${reactionId}`);
        if (group) {
            group.style.filter = 'drop-shadow(0 0 15px rgba(52, 152, 219, 0.6))';
        }
        
        // 触发选择事件
        const reaction = this.reactions.find(r => r.id.toString() === reactionId);
        if (reaction) {
            this.dispatchEvent('reactionSelected', reaction);
        }
    }
    
    dispatchEvent(eventName, data) {
        const event = new CustomEvent(eventName, { detail: data });
        this.container.dispatchEvent(event);
    }
    
    handleResize() {
        // 响应式调整
        const containerWidth = this.container.offsetWidth;
        if (containerWidth !== this.options.width) {
            this.options.width = containerWidth;
            this.svg.setAttribute('width', containerWidth);
            this.relayout();
        }
    }
    
    relayout() {
        // 重新布局所有反应
        this.reactions.forEach((reaction, index) => {
            reaction.coordinates = this.generateAutoLayout();
            const group = document.getElementById(`reaction-${reaction.id}`);
            if (group) {
                group.remove();
                this.renderReaction(reaction);
            }
        });
    }
    
    clear() {
        this.reactions = [];
        this.selectedReaction = null;
        
        // 清除所有层
        [this.moleculeLayer, this.connectionLayer, this.conditionLayer, this.annotationLayer].forEach(layer => {
            while (layer.firstChild) {
                layer.removeChild(layer.firstChild);
            }
        });
    }
    
    exportAsSVG() {
        const serializer = new XMLSerializer();
        return serializer.serializeToString(this.svg);
    }
    
    setTheme(themeName) {
        this.options.theme = themeName;
        this.loadTheme();
        this.relayout();
    }
}

// 反应图表工具类
class ReactionDiagramTools {
    static createDiagram(containerId, options) {
        return new ReactionDiagram(containerId, options);
    }
    
    static parseReactionSMARTS(smarts) {
        // 简化的SMARTS解析
        const parts = smarts.split('>>');
        return {
            reactants: parts[0] ? parts[0].split('.') : [],
            products: parts[1] ? parts[1].split('.') : []
        };
    }
    
    static calculateReactionBalance(reaction) {
        // 简化的反应平衡计算
        const reactantAtoms = reaction.reactants.reduce((sum, r) => sum + (r.atoms || 0), 0);
        const productAtoms = reaction.products.reduce((sum, p) => sum + (p.atoms || 0), 0);
        
        return {
            balanced: reactantAtoms === productAtoms,
            atomDifference: productAtoms - reactantAtoms
        };
    }
}

// 导出到全局
window.ReactionDiagram = ReactionDiagram;
window.ReactionDiagramTools = ReactionDiagramTools; 