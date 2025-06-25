# OpenChemIE 智能化升级 – 版本化任务计划 (DEV_PLAN)

> 本文件按照 **Version 1.0 / 2.0 / 3.0** 三个阶段组织，采用 `TASKxxx` 编号描述最小可行任务，便于 Taskmaster-AI 或人工开发者逐项执行、追踪与验收。

---

## 📚 版本索引
- [Version 1.0 – Minimal Viable Product](#version-10--minimal-viable-product)
- [Version 2.0 – Local LLM Integration](#version-20--local-llm-integration)
- [Version 3.0 – Multimodal Enhancement & Optimization](#version-30--multimodal-enhancement--optimization)

---

## Version 1.0 – Minimal Viable Product

### TASK001 – 初始化开发环境与依赖锁定
- **Version**: 1.0  
- **Status**: 计划中

#### 子任务
1. 在 `requirements.txt` 使用 `~=` 锁定核心依赖版本。
2. 生成 `requirements-lock.txt` (`pip-compile`).
3. 创建 **DevContainer** (Ubuntu 22.04 + Python 3.10)。
4. 配置 `pre-commit` (black, ruff, isort, mypy)。

#### 🤖 AI Assistant Prompt (完整示例)
```prompt
You are an advanced AI pair-programmer working on OpenChemIE.
Goal: 完成 TASK001 的全部子任务并推送到 Git 仓库。
Constraints:
1. Preserve existing project structure.
2. Use ~= for version pinning; freeze to requirements-lock.txt via pip-compile.
3. Ensure pre-commit hooks run without error on initial commit.
4. All changes must pass CI (pytest, lint) before merge.
Output: Git diff with added files & updated requirements.
Failure policy: 如果任何步骤失败，自动回滚并输出故障原因。
```

#### 验收标准
- `pip install -r requirements-lock.txt` 可完整复现环境。
- `pre-commit run --all-files` 无错误。
- DevContainer 启动后 `python --version` == 3.10.x。

#### 注意事项
- 锁定文件须加入版本控制（避免 `.gitignore` 排除）。
- Windows 用户需单独测试 PowerShell 安装脚本。

---

### TASK002 – 代码结构重组：模块化 Skeleton
- **Version**: 1.0  
- **Status**: 计划中

#### 子任务
1. 创建 `openchemie/core/`, `openchemie/models/`, `openchemie/pipelines/`, `openchemie/llm/` 目录。
2. 将现有 `interface.py` 内容拆分为 `core/base.py` 与示例管线文件。
3. 更新 `__init__.py` 导出公共接口。
4. 调整单元测试路径。

#### 🤖 AI Assistant Prompt
```prompt
Objective: Refactor interface.py into modular skeleton.
Steps:
- Move abstracts to core/base.py
- Keep API routers unchanged.
- Ensure existing unit tests still pass.
Return: Patch ready to commit.
```

#### 验收标准
- 所有 `pytest` 测试通过。
- `openchemie` 目录符合新的层级结构。

#### 注意事项
- 保留历史 import 兼容性（添加临时别名）。

---

### TASK003 – DeviceManager 抽象
- **Version**: 1.0  
- **Status**: 计划中

#### 子任务
1. 实现 `DeviceManager` 检测 CUDA/MPS/CPU。
2. 提供 `allocate_model()` API 支持显存检查。
3. 编写单元测试模拟不同硬件环境。

#### 🤖 AI Assistant Prompt
```prompt
Implement DeviceManager with auto GPU/CPU switch.
Include memory threshold config and unit tests (pytest, monkeypatch torch.cuda.is_available).
```

#### 验收标准
- `pytest tests/device_manager.py` 100% 通过。

#### 注意事项
- 兼容无 CUDA 环境。

---

### TASK004 – ProcessorRegistry 插件机制
- **Version**: 1.0  
- **Status**: 计划中

#### 子任务
1. 新建 `openchemie/core/registry.py`，实现 `ProcessorRegistry`（`register()`, `get()`, `list()`）。
2. 支持 `@processor_registry.register("name")` 装饰器简化注册。
3. 在 `openchemie/pipelines/__init__.py` 中示例注册 `PdfPipelineProcessor`。
4. 编写单元测试 `tests/test_registry.py`，覆盖率 ≥ 90%。

#### 🤖 AI Assistant Prompt
```prompt
Objective: Implement dynamic plugin registry (TASK004).
Steps:
1. Create ProcessorRegistry with thread-safe register/get/list.
2. Provide decorator for syntactic sugar.
3. Add example processor registration in pipelines package.
4. Write pytest unit tests with >90% coverage.
Constraints: Keep backward compatibility, no external deps.
Rollback: On import/test failure, revert and output traceback.
```

#### 验收标准
- 动态注册、检索、列出功能通过测试。  
- 装饰器注册语法可在示例中正常使用。  
- `pytest -q` 全部通过，覆盖率报告 ≥ 90%。

#### 注意事项
- 防止循环依赖导致的 ImportError。
- Registry 推荐单例实现，避免多重实例化。

---

### TASK005 – 单元测试基线 & CI 管道
- **Version**: 1.0  
- **Status**: 计划中

#### 子任务
1. 初始化 `tests/` 目录与 `conftest.py`。
2. 添加示例测试 `tests/test_smoke.py` 验证 API 根路由返回 200。
3. 配置 `pytest.ini`（含 `addopts = -q --cov=openchemie --cov-report=term-missing`）。
4. 在 `.github/workflows/ci.yml` 设置 GitHub Actions：`lint -> test -> build-docker` 三阶段。

#### 🤖 AI Assistant Prompt
```prompt
Goal: Establish testing baseline & CI (TASK005).
Deliverables:
- pytest config & smoke test.
- GitHub Actions workflow (Python 3.10, cache deps).
- Coverage threshold 70% (fail below).
Ensure: workflow green on first run.
```

#### 验收标准
- 本地 `pytest` 运行通过，初始覆盖率 ≥ 70%。
- GitHub Actions 执行成功，无失败步骤。

#### 注意事项
- 使用 `actions/setup-python` 缓存依赖缩短时间。  
- Docker build 步骤可使用 `--target test` 精简镜像体积。

---

### TASK006 – Docker & DevContainer 配置
- **Version**: 1.0  
- **Status**: 计划中

#### 子任务
1. 精简 `infra/Dockerfile.api`，采用多阶段构建，最终镜像 < 1.5 GB。
2. 更新 `infra/docker-compose.yml`，支持 GPU 与 CPU 两种 profile (`--profile gpu`).
3. 创建 `.devcontainer/devcontainer.json`，映射 `Dockerfile.dev`。
4. 编写文档 `docs/DEPLOY_DOCKER.md`，说明本地与生产部署步骤。

#### 🤖 AI Assistant Prompt
```prompt
TASK006: Optimize Docker & DevContainer.
Requirements:
- Multi-stage build; final image <1.5GB.
- docker-compose gpu profile uses nvidia runtime.
- DevContainer launches api + redis services.
- Provide deployment docs.
```

#### 验收标准
- `docker compose build` 完成且镜像体积满足要求。
- 在 VS Code Remote Containers 中可成功启动并访问 API `/docs`。

#### 注意事项
- 确保 `.dockerignore` 排除 `models/` 巨大文件夹。  
- GPU profile 仅在检测到 `nvidia-smi` 时启用。

---

## Version 2.0 – Local LLM Integration

### TASK201 – Ollama + Qwen2.5-7B 部署脚本
- **Version**: 2.0  
- **Status**: 计划中

#### 子任务
1. 编写 `scripts/install_ollama.sh`，自动安装 Ollama (Linux/macOS)。
2. 编写 `scripts/download_models.sh` 下载 `qwen2.5:7b` 并校验 SHA256。
3. 在 `infra/docker-compose.yml` 新增 `ollama` 服务。
4. 更新 README 部署指南。

#### 🤖 AI Assistant Prompt
```prompt
Objective: Provide reproducible Ollama + Qwen2.5-7B deployment (TASK201).
Steps: write install & model scripts, compose service, docs.
Ensure scripts idempotent, exit on error.
```

#### 验收标准
- 运行脚本后 `ollama list` 包含 `qwen2.5:7b`。  
- `docker compose up -d ollama` 启动成功并可通过 11434 端口访问。

#### 注意事项
- 国内用户需提供镜像加速源。  
- 脚本需使用 `set -euo pipefail`。

---

### TASK202 – LocalLLMClient 封装
- **Version**: 2.0  
- **Status**: 计划中

#### 子任务
1. 创建 `openchemie/llm/client.py`，封装 async Ollama HTTP 调用。
2. 实现 `query()` 与 `batch_query()`；支持温度、top_p 参数。
3. 添加重试与超时逻辑 (`tenacity`).
4. 编写单元测试使用 `httpx.MockTransport`。

#### 🤖 AI Assistant Prompt
```prompt
TASK202: Implement LocalLLMClient.
Interfaces: query(), batch_query().
Handle retries (3) & 30-s timeout.
Mock Ollama API in tests.
```

#### 验收标准
- `pytest tests/test_llm_client.py` 全部通过。
- 能在 2s 内完成批量 5 条 mock 请求。

#### 注意事项
- 避免在客户端中硬编码模型名；通过参数注入。

---

### TASK203 – 智能 R 基团识别器
- **Version**: 2.0  
- **Status**: 计划中

#### 子任务
1. 新建 `openchemie/llm/rgroup_extractor.py`。
2. 设计 prompt 模板支持条件式定义。
3. 调用 LocalLLMClient 完成解析并返回结构化 JSON。
4. 编写 20 条样例的集成测试。

#### 🤖 AI Assistant Prompt
```prompt
Design & implement intelligent R-group extractor using Qwen2.5 (TASK203).
Return JSON: name, definition, conditions, confidence.
```

#### 验收标准
- 20 条样例平均 F1 ≥ 0.88。

#### 注意事项
- 为每条返回增加 `confidence` 字段，便于后续质量评估。

---

### TASK204 – 反应条件语义解析器
- **Version**: 2.0  
- **Status**: 计划中

#### 子任务
1. 建立 prompt 模板解析催化剂、气氛等信息。
2. 支持返回机制推断字段 `mechanism`。
3. 添加降级逻辑：LLM 失败回退规则解析。
4. 测试覆盖 30 条标准反应描述。

#### 🤖 AI Assistant Prompt
```prompt
TASK204: Build SemanticReactionConditionParser.
Parse catalyst, atmosphere, parameters, mechanism.
Provide graceful fallback.
```

#### 验收标准
- F1 ≥ 0.80 在测试集。

#### 注意事项
- 正则回退需与旧版逻辑兼容。

---

### TASK205 – 共指关系增强器
- **Version**: 2.0  
- **Status**: 计划中

#### 子任务
1. 实现 `ContextualCoreferenceResolver` 调用 LLM。
2. 支持 `resolve_advanced_coreferences()` API。
3. 集成至现有提取流水线。
4. 编写长文本性能基准。

#### 🤖 AI Assistant Prompt
```prompt
TASK205: Implement advanced coreference resolver using LLM.
Focus on "the product" ambigious terms.
```

#### 验收标准
- 在基准文档集上共指准确率提升 ≥15%。

#### 注意事项
- 注意内存占用，长文切片处理。

---

### TASK206 – 降级/回退机制实现
- **Version**: 2.0  
- **Status**: 计划中

#### 子任务
1. 在 `openchemie/settings.py` 增加 `LLM_FALLBACK_ENABLED`。
2. 在各 LLM 模块包裹 `try/except`，回退旧算法。
3. 记录降级事件日志到 `logs/llm_fallback.log`。
4. 单元测试模拟 LLM 超时触发回退。

#### 🤖 AI Assistant Prompt
```prompt
TASK206: Implement robust fallback when LLM fails.
Log fallback events and continue pipeline.
```

#### 验收标准
- 模拟失败时仍可返回旧算法结果。
- 日志记录包含 timestamp / module / reason。

#### 注意事项
- 避免吞并原始异常，便于调试。

---

### TASK207 – LLM 性能基准与监控
- **Version**: 2.0  
- **Status**: 计划中

#### 子任务
1. 使用 `locust` 或 `pytest-benchmark` 评估 QPS & latency。
2. 整合 `prometheus_client` 输出 `/metrics`。
3. 在 Grafana 导入默认仪表板。
4. 写性能报告 `docs/perf/llm_baseline.md`。

#### 🤖 AI Assistant Prompt
```prompt
TASK207: Benchmark & monitor LLM service.
Provide Prometheus metrics and Grafana dashboard JSON.
```

#### 验收标准
- QPS ≥ 5 (batch size 1) on RTX 4060。
- `/metrics` 暴露主要指标。

#### 注意事项
- 基准需排除首次加载的冷启动时间。

---

## Version 3.0 – Multimodal Enhancement & Optimization

### TASK301 – Gemini 多模态校验集成
- **Version**: 3.0  
- **Status**: 计划中

#### 子任务
1. 在 `openchemie/llm/multimodal_validator.py` 集成 Google GenerativeAI SDK。
2. 封装 `validate_extraction(pdf, json)` 方法。
3. 处理 `403/429` 错误并降级本地评估。
4. 单元测试使用 mock SDK。

#### 🤖 AI Assistant Prompt
```prompt
TASK301: Integrate Gemini 2.5 Flash for multimodal validation.
Ensure cost control via feature toggle.
```

#### 验收标准
- 成功返回置信度评分 JSON。
- 调用次数计数器可在 `/metrics` 查看。

#### 注意事项
- 默认关闭云端验证，需显式 `--enhanced` 参数。

---

### TASK302 – MultimodalValidator 服务
- **Version**: 3.0  
- **Status**: 计划中

#### 子任务
1. 新建 FastAPI 路由 `/validate/multimodal/`。
2. 支持文件上传 + 结果 JSON 输入。
3. 返回校正建议及图表差异。
4. 前端提供 REST 调用示例。

#### 🤖 AI Assistant Prompt
```prompt
TASK302: Build REST service wrapping MultimodalValidator.
```

#### 验收标准
- Swagger 文档自动生成并可调试。

#### 注意事项
- 上传文件大小限制 10 MB。

---

### TASK303 – 前端结果对比视图
- **Version**: 3.0  
- **Status**: 计划中

#### 子任务
1. 在 Vue3 新建组件 `ResultComparer.vue`。
2. 使用 ECharts 渲染差异雷达图。
3. 支持 JSON diff 高亮。
4. 编写单元测试使用 Vitest。

#### 🤖 AI Assistant Prompt
```prompt
TASK303: Implement interactive result comparison view using Vue3 + ECharts.
```

#### 验收标准
- 能加载 API 结果并显示差异图表。

#### 注意事项
- 保证移动端响应式布局。

---

### TASK304 – 质量评估仪表板
- **Version**: 3.0  
- **Status**: 计划中

#### 子任务
1. 在 Grafana 创建 Extraction Quality Dashboard。
2. 指标：molecular_confidence, reaction_confidence, overall_confidence。
3. 导出 JSON 配置到 `infra/grafana_dashboards/`。
4. 文档 `docs/monitoring/quality_dashboard.md`。

#### 🤖 AI Assistant Prompt
```prompt
TASK304: Build Grafana dashboard for extraction quality metrics.
```

#### 验收标准
- Dashboard JSON 被 Grafana 成功导入。

#### 注意事项
- 使用变量支持多环境切换。

---

### TASK305 – 内存复用与批处理调度优化
- **Version**: 3.0  
- **Status**: 计划中

#### 子任务
1. 实现 `MemoryManager` 卸载最少使用模型。
2. 根据 PDF 页数动态调整并发数。
3. 在批处理服务加入 `semaphore` 控制。
4. 基准测试显存占用与吞吐。

#### 🤖 AI Assistant Prompt
```prompt
TASK305: Optimize memory reuse & batch scheduler.
```

#### 验收标准
- GPU/CPU 内存占用下降 ≥ 20%。
- Batch TPS 提升 ≥ 30%。

#### 注意事项
- 避免频繁加载/卸载导致抖动。

---

### TASK306 – 生产部署流水线 & 监控
- **Version**: 3.0  
- **Status**: 计划中

#### 子任务
1. 在 GitHub Actions 添加 `release.yml`，推送 tag 时构建并发布 Docker 镜像。
2. 使用 `infra/k8s/` Helm Chart 部署到生产集群。
3. 配置 Prometheus Operator 抓取 `/metrics`。
4. 编写 `runbook.md` 描述故障排查流程。

#### 🤖 AI Assistant Prompt
```prompt
TASK306: Build production-grade deployment pipeline & monitoring.
```

#### 验收标准
- Tag push 自动发布并可在集群访问。
- Prometheus & Grafana 展板显示实时指标。

#### 注意事项
- Helm Chart 需支持 CPU/GPU 选项。

---

> **更新记录**  
> 2025-03-01 – 重构为版本化 TASK 格式 (by AI Assistant) 