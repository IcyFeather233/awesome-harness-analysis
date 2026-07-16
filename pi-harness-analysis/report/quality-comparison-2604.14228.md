# 与 2604.14228 的质量对照

基准：[Dive into Claude Code: The Design Space of Today's and Future AI Agent Systems](https://arxiv.org/html/2604.14228)，v2，2026-07-02。本页评价的是报告方法与表达，不把 Claude Code 和 Pi 的产品复杂度直接等同。

## 维度对照

| 维度 | 2604.14228 | 初版 Pi 报告 | 本轮改进后 | 仍然缺少 |
|---|---|---|---|---|
| 证据可追溯 | A/B/C tiers，正文引用文件/函数 | D/S/R/X/I + claim/HIR，严谨但阅读成本高 | 保留机器证据，正文图和设计问题仍可回到 ID | 源码链接还不是交互式 HTML tooltip |
| 动态验证 | 主要是固定源码快照和文档/社区材料 | 4 个 real-model 场景 + 131 个定向测试 | 不变，这是 Pi 报告相对更强的一项 | 缺 write/bash/sandbox/subagent/fault-injection 实跑 |
| 设计综合 | 五类 values -> 13 principles -> implementation | 以 subsystem 和事实为主，解释链较弱 | 新增六个 design questions 和 stance -> mechanism -> consequence | Pi 作者公开价值声明较少，不能安全复刻五价值框架 |
| 贯穿案例 | “Fix auth.test.ts” 跨 3-9 节反复出现 | 实验散落，没有统一阅读线 | 用 R-SCENARIO-002 贯穿 loop/context/tool/event | read-only 案例不足以覆盖写入、权限和恢复 |
| 系统总览图 | 7 个组件、单一主轴、图标和语义色 | 16 节点技术图，横向过宽、组序错误、回边交叉 | gpt-image 读者图将主路径压为六步，并以图标、短标签和虚线支路分离迁移/gate；SVG 保留证据 | 仍没有点击展开源码 |
| Turn flow 图 | 为每轮迭代定制纵向布局，读者快速理解循环 | 自动 HIR 分组把控制顺序打乱 | gpt-image 纵向图严格复现两轮 read trace；SVG 保留完整状态投影 | 只覆盖一个代表 trace，不是全状态机 |
| 图与证据关系 | caption 和正文说明，图本身不携带结构化 evidence | SVG/HIR metadata 强，但颜色几乎全被 evidence state 占用 | 技术 SVG + 叙事 SVG + 受事实约束的读者 PNG；prompt/hash/review metadata 可审计 | 需要 HTML viewer 才能把 metadata 变成可点交互 |
| 比较与外部有效性 | 对比 OpenClaw/Hermes，并连接相关工作与未来方向 | 单仓库深挖 | 新增 alternatives，但没有完整跨仓库 synthesis | 需要用相同 Skill 分析更多 harness 后再横向比较 |
| 失败与不确定性 | 有 limitations，但主要来自静态逆向边界 | 明确 blocked experiments、conditions 和最高价值 unknowns | 新章节继续保留，不被叙事图掩盖 | 高风险失败路径尚未在强隔离环境中执行 |
| 可复现性 | 论文源码和 figure assets 可用 | manifest/HIR/evidence/scenario/trace/scripts 完整 | 新增 story spec、叙事 renderer、link/SVG audit | 还没有 commit-to-commit architecture diff CI |

## 初版图片的具体问题

初版 8 张图是合格的 evidence views，但不适合直接作为论文正文图：

1. `attributes.layer` 按字符串排序，system overview 出现 context -> execution -> infrastructure -> interface 的阅读顺序。
2. 节点几乎全部是绿色 observed，状态编码压过了 interface/model/state/policy 等语义差异。
3. 所有 group 都是一列卡片，导致主路径弯折、toolResult 回边跨越多个 group。
4. 2000px 左右横图缩进 Markdown 后字体偏小，edge label 与 node/edge 局部相撞。
5. 节点显示 HIR type 对审计有用，对第一次阅读是额外噪声。
6. 自动图试图同时表达当前产品路径、新 Harness、恢复、状态和观测，没有单一视觉论点。

论文图更清楚的原因不是“更花哨”，而是每张图有不同的人工语义投影：system overview 只保留七个责任，turn flow 明确重复 iteration，extension 图围绕三个 injection points，context 图按加载时机和可变性组织。它没有把整个 call graph 交给一种布局算法。

## 本轮采用的改进

- 把 8 张 HIR 图定义为 technical evidence views，不再默认承担正文解释。
- 新增 `story-specs.json`，以人工语义选择 + 确定性 renderer 生成 5 张正文叙事图（总览、turn、context、extension、design space）。
- 新增 gpt-image-2 reader illustration 层，覆盖全部 8 张唯一正文图，以论文式图标、短标签和单一视觉论点降低阅读门槛；caption 同时链接确定性 evidence SVG。
- 对生成图执行语义拒绝机制：context v1 因把 tool result 画成直达 model 而被隔离，收紧 prompt 后的 v2 才进入报告。
- 叙事图中的每个实现节点保留 `hir_ids`，每条材料边保留 `evidence_ids`；concept 节点必须有 claim/evidence。
- 使用责任语义色，证据状态改由实线、虚线、点线和 caption 表达。
- 加入六个 design questions、真实 running example 和跨决策张力。
- 新增 output audit，检查 Markdown links、SVG title/description、PNG IHDR 尺寸、prompt/output 哈希、semantic review metadata、节点密度和极端 aspect ratio。
- 要求最终 raster inspection；XML 可解析不再等价于图像质量合格。

## 尚未追平论文的部分

1. **比较研究。** 当前只有 Pi 单项目，不能得出跨 harness recurring patterns；论文通过 OpenClaw/Hermes 对比解释 deployment context。
2. **文献与产品语境。** Pi 报告没有系统连接 coding-agent taxonomy、治理、长期开发者能力或实证研究。
3. **全路径 running example。** 当前例子真实但只读；论文案例可以在叙事上贯穿 permission、write、subagent 和 persistence，虽然不等于每条都动态验证。
4. **视觉出版物。** 当前是 Markdown + reader PNG + evidence SVG，仍没有统一的 HTML/PDF 排版、交叉引用编号、参考文献系统和响应式交互。
5. **强隔离故障实验。** 对 bash、write、tool timeout、container routing、subagent crash、JSONL corruption 的结论仍主要是静态或单元测试证据。

最合理的下一阶段不是继续增加自由文本，而是选择 disposable VM 中的真实 edit-and-test running example，补齐 side-effect/failure matrix，再用相同 codebook 独立分析第二、第三个 harness，最后做跨项目 design-space synthesis。
