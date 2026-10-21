#!/usr/bin/env python3
"""Compile the maintained Pi analysis report and current claim index."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "report"
SOURCE = "https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/"
REPORTS = {}

REPORTS['index.md'] = r"""# Pi Agent Harness 分析报告：从一次请求看懂它怎样工作

打开 Pi，输入一句话：

> 看一下这个项目的配置，告诉我服务监听哪个端口。

屏幕上很快出现一次文件读取，接着是回答：“8080。”这个过程看起来像模型自己打开了文件。但在模型提出读取请求之后，还需要程序找到工具、检查参数、访问文件，再把内容交回模型。我们看到的一次回答，实际上已经经过了几次不同的交接。

Pi 把这套运行程序称为 agent harness。要理解它，可以先跟着这条请求走一遍，再看任务变长、遇到错误或需要换一个方向时，系统会怎样处理。下文基于 Pi `v0.80.7` 的当前 Coding Agent 实现；读取配置等场景是串讲源码的示例，实际实验记录放在文末的查证入口。

## 模型提出动作，Pi 把动作做完

模型收到请求时，除了你的问题，还会收到系统提示、已有消息，以及当前可以使用的工具说明。Pi 新会话默认开放 `read`、`bash`、`edit` 和 `write`：读取文件、执行命令、修改文本和写入文件。仓库里还定义了其他工具，只是默认没有全部启用。

对于端口问题，模型可能先返回一个 `read` 调用，参数是配置文件路径。这条响应表达了“接下来需要读取什么”。Pi 接手之后才会去查找工具、校验参数、执行读取，并把结果包装成一条与该调用关联的消息，也就是 `toolResult`。

假设文件中写着 `{"port": 8080}`。Pi 把这段结果加入上下文，再请求一次模型。第二次，模型已经有了文件内容，才给出“服务监听 8080 端口”的回答。

因此，一次用户提问可以包含多次模型请求。在 Pi 的低层循环里，一轮模型响应加上它提出的工具处理叫一个 `turn`。上面的例子有两个 turn：第一轮要求读文件并取得结果，第二轮根据结果回答。模型如果在一条响应中提出多个工具调用，它们也可以属于同一个 turn。

这条闭环在源码中由 `runAgentLoop` 执行。围绕它，`Agent` 管理当前消息、工具配置和输入队列，`AgentSession` 则负责把用户输入、扩展、重试和会话管理接起来。先记住这层关系就够了：循环负责持续推进模型和工具之间的交接，产品层负责组织整次运行。[循环与实际 read 轨迹](00-task-walkthrough.md)

## 两个文件一起读，结果怎样接回来

把问题稍微扩大一点：你让 Pi 同时检查配置文件和启动脚本。模型可能一次提出两个读取调用。Pi 默认允许工具并行执行，其中一个文件先读完，界面就可以先显示它的结束通知。

但下一次模型请求里的结果顺序，仍按模型最初提出调用的顺序组织。

![Pi 工具调用、并行完成与结果回填的顺序](../diagrams/generated/pi-tool-order-v2.png)

*图中的 A、B 是顺序示例：完成通知可以是 B、A，回填给模型的结果仍是 A、B。时间条不表示实测耗时。*

这让界面进度和对话历史各自遵循合适的顺序：界面反映哪个操作先结束，模型看到的消息则保留稳定的调用与结果关系。如果批次中有工具声明需要串行，或配置要求串行，Pi 会让整个批次按顺序执行。

工具执行前还有准备步骤。名称不存在、参数不合法，或者扩展明确阻断调用时，Pi 可以直接返回错误结果，跳过真正的执行函数。一个容易忽略的细节是，`tool_execution_start` 事件在这些检查之前就已经发出。它表示开始处理一次调用，不能单凭这个事件认定文件已被修改或命令已经启动。

如果测试命令确实执行了，但返回失败，错误通常会作为工具结果交回模型。模型读到报错后，可以修改代码，再提出新的测试调用。这仍是刚才那条模型—工具循环。[工具批次与事件顺序](03-core-loop.md)

## 你中途说一句话，Pi 会在什么时候听见

假设 Pi 正在检查文件，你发现它方向不对，补充一句：“先看启动脚本，端口可能被环境变量覆盖了。”在默认交互键位下，此时按 Enter 提交，界面就明确把这条普通消息送入 steering 队列。当前模型响应及其工具批次处理完后，循环检查队列，把消息放到下一次模型请求中；入队本身不会撤销已经发出的工具操作。

如果想排在当前工作之后，例如“这一轮完成后，再检查一下文档里的端口说明”，可以用 Alt+Enter 提交。界面会选择 follow-up 队列，等当前工具和 steering 消息都处理完、循环准备停下时再取出。

决定队列的是提交方式，Pi 不会请求 LLM 根据句子意思分类。同一句“忙完之后，再检查文档”，按 Enter 仍进入 steering，按 Alt+Enter 才进入 follow-up。前一种情况下，模型较早收到消息后，也许会理解“忙完之后”并选择稍后执行；那属于模型收到内容后的行动选择，和程序何时递交消息是两个阶段。

通过 SDK 或 RPC 接入时，由调用方明确指定模式或调用相应的入队方法。快捷键可以自定义；Pi 空闲时，Alt+Enter 则像普通 Enter 一样提交新请求。

两种队列让用户选择何时影响运行：及时调整接下来的方向，或把输入排到当前循环准备结束时。Haochuan 从交互角度讨论过这一区分；具体入口、参数和消费时机见[双队列的实现](03-core-loop.md#双队列对应两种交互意图)。

## 停下来之前，产品层还要处理什么

正常情况下，模型给出回答，工具和输入队列也都耗尽，低层循环就发出 `agent_end`。不过，一次低层运行也可能因为 Pi 请求 LLM 服务失败而结束。

这里需要分清网络错误发生在哪里。如果模型让 bash 执行 curl 下载文件，curl 超时或连接失败，通常会变成错误的 `toolResult`，再交回模型。模型可以决定换地址、检查网络，或者提出 `sleep 10` 后再下载的新命令；这仍是正常工具循环中的下一次决策。

另一种情况是 Pi 自己向 LLM 服务发请求，服务返回了临时的不可用错误。此时轮到 `AgentSession` 处理：它检查最后的错误状态，用代码规则判断错误是否可重试，再看开关和次数限制。默认设置下，连续失败可以额外重试三次，分别等待 2、4、8 秒。等待期间可以取消；后续收到非 error 的响应时，计数会重置。

这一步不需要让 LLM 判断“要不要再试”。分类器检查的是最后的 assistant 错误状态，不会扫描全部工具输出，看到“network error”就重试。符合规则的模型服务或传输错误可以重试，配额和账单限制则会被排除。上下文溢出有另一条压缩恢复路径，也不直接套用普通重试。

因此，同一条用户请求中可能出现这样的过程：第一次低层运行因模型 API 请求失败而发出 `agent_end`，产品层等待后再次调用 `Agent.continue()`，重新请求模型。这不会直接重跑上一条 bash，也不会把用户任务从头执行；模型恢复响应后仍可自行提出新的工具调用。直到重试、压缩和排队输入等后续工作都处理完，`AgentSession` 才发出 `agent_settled`。

这也解释了为什么“运行结束”和“任务做对”要分别检查。重试耗尽后报错退出，产品层同样需要收尾；模型给出一个错误的端口，也可能正常结束。事件告诉我们程序走到了哪里，回答是否正确还要看文件和任务要求。模型 API 错误后的自动重发与模型看到工具失败后主动调整动作，由不同的机制决定。命令自身也可能有重试，例如 curl 的重试选项；那段时间 Pi 通常仍在等待本次 bash 完成。[三层重试的例子](10-implementation-details.md#bash-联网失败和模型-api-失败分别怎么处理)

## 模型看到的历史，是每次请求选出来的

现在假设对话已经持续了一段时间：Pi 读过配置、跑过测试，你还尝试过两种修复方式。会话里积累的内容，已经比最初那句提问丰富得多。

Pi 会保存发生过的消息和其他记录，但模型每次请求使用的是经过选择的视图。完整记录可以包含多条分支，当前只沿其中一条继续；较早的内容也可能已经被压缩摘要代表。随后，扩展可以调整请求用的消息，类型转换函数再把它们整理成模型接口接受的形式。

![Pi 从会话记录选择分支，再构造模型请求](../diagrams/generated/pi-context-views-v3.png)

*消息经过分支选择、变换和类型转换；system prompt 与 active tools 在请求组装处单独加入。有压缩记录时，当前视图包含摘要与保留片段。*

一个具体例子是扩展补充的“不要修改公共 API”。Pi 内部可以把它记成 `custom` 消息，同时保留扩展类型、显示选项和附加数据。发送前，`convertToLlm` 取出它的正文，包装成 pi-ai 的 `user` 消息。因此，模型消息中的 user 角色也可能承载程序加入的上下文，不一定是人刚刚键入的文字。

另一个例子是你直接在 Pi 中执行 `!npm test`。应用记录里可以分别保存命令、输出、退出码和取消状态；转换函数再把这些字段组织成模型可读的文本。模型主动调用 bash 工具时，得到的则是与工具调用关联的 `toolResult`。两条路径都涉及 shell，但消息的来源和表示不同。

还有一些扩展记录只是内部状态，例如计数器或界面标记。普通 custom entry 默认不进入模型上下文；需要注入内容时，扩展使用另一种 custom message entry。甚至 `display: false` 也只是界面属性，不能据此推断模型看不到内容。

这些转换都是普通 TypeScript 代码。恢复会话、切换分支或压缩时，Pi 会重建相应的消息视图；正常循环则在内存中追加消息，并在每次模型请求前进行转换。排查“模型为什么没看到某条信息”时，需要沿着这条路径检查，仅仅在 session 文件里找到它还不够。[三层视图与消息转换例子](04-context-memory-compaction.md)

消息到达模型 API 后，还要经过模型服务的编码。Pi 适配器先把 system prompt、消息和工具定义组织成请求字段；服务端再按模型的对话模板加入角色边界、工具说明和生成前缀，随后转成 token 输入。Qwen3.8-27B 与 DeepSeek V4 Flash 的公开实现使用不同的标记和工具调用格式。模型生成的调用经过解析回到 Pi，真正的文件读取仍由 Pi 执行。这个交接解释了为什么同一份 messages 可以对应不同的模型输入。[从 API 请求到模型输入的完整例子](18-model-input-encoding.md)

## 对话太长时，摘要怎样接上后续工作

排查启动问题的时间一长，配置文件、命令输出和修改记录会不断进入对话。Pi 会把较早内容总结成摘要，保留一段近期消息，让后续请求继续容纳新的工作。

哪些原文留下，先由代码按预算和消息结构决定。当前默认 `keepRecentTokens` 是 20000：程序从最新消息往前累计估算 token，找到保留近期片段的切分位置。它按体积选择连续片段，不会先让模型给每条消息打重要性分数；工具结果也不能成为保留片段的第一条，以免失去对应的工具调用。

假设这次选中了最近约两万 token 的消息，之前的内容就交给模型总结。摘要提示词要求记录用户目标和约束、工作进度、关键决定、下一步，以及继续任务需要的文件路径和错误信息。若一次排查本身就很长，切分位置落在任务中途，Pi 还会为被切掉的任务前半段生成摘要，交代原始要求和早期进展，让留下来的后半段有上下文可接。

下面用一个教学例子表示压缩后的对话；消息编号和体积只用于说明过程：

```text
原来：消息 1～80 + 消息 81～100
之后：前面工作的摘要 + 保留原文的消息 81～100
```

摘要成功后，`AgentSession` 保存带有摘要和保留起点的压缩记录，再重建当前上下文。旧消息仍可留在会话文件中。较早的重要要求要靠摘要传递，近期细节则继续保有原文；摘要是否遗漏关键约束，需要检查内容，不能只看“压缩完成”事件。[切分边界与摘要生成](04-context-memory-compaction.md#哪些消息保留原文哪些送去总结)

假如摘要正在生成，你补充一句：“生产环境设置了 PORT=8080，接下来检查 Docker 配置。”终端会先把这句话放进压缩期间的输入队列。正在进行的摘要调用继续处理之前准备好的材料，新要求等压缩结束再提交。下一次处理任务的模型请求就可以看到：

```text
压缩摘要 + 保留的近期消息 + “PORT=8080，请检查 Docker 配置”
```

如果上一轮已经完成，这条输入可以启动后续工作；如果正在为溢出错误做恢复，它会按提交时的 steering / follow-up 类型进入相应队列，由恢复后的循环消费。接收输入和开始处理输入发生在不同时间。[压缩期间的队列时间线](04-context-memory-compaction.md#压缩期间提交的新输入怎样接上来)

Pi 还区分接近阈值时的预防性压缩，以及上下文溢出后的恢复。阈值检查发生在特定运行边界，检查之后仍可能加入大段输入或工具输出，估算也可能与实际用量有差异，所以提前压缩不能排除所有溢出。已完成的回答不会因为阈值压缩而重新生成；需要恢复的溢出响应才按规则尝试压缩后续跑。[为什么仍然需要溢出恢复](04-context-memory-compaction.md#已经有阈值检查为什么还会溢出)

## 关掉进程之后，对话怎样继续

要让这段工作延续到下次启动，Pi 用 `SessionManager` 管理会话记录。记录以 JSONL 保存，也就是每行一个 JSON 对象；其中的 `id` 和 `parentId` 把历史连接成树，当前的 `leaf` 表示继续对话的位置。

这使得尝试另一种思路时，不必删掉原来的路径。比如，你先尝试修改配置，随后回到共同历史，改为检查启动参数。两条路径都可以留在会话树中，模型沿当前选中的分支继续。切换时还可以附带支线摘要，把有用的信息带回来。Armin 的使用记录把这种能力用于临时探索：先解决支线问题，再回到主线。[会话分支与使用案例](08-sessions-persistence-recovery.md#会话树怎样支持临时探索)

会话分支管理的是对话。支线里如果已经修改了文件，回到旧 leaf 后，文件仍然是修改后的内容；工作区版本需要用 Git 等方式另行管理。这个区别在尝试不同修复方案时尤其重要。

文件的创建时机也有一个细节：新建且尚未写过的持久会话，通常先把 user 和配置 entry 留在内存，直到首条 assistant entry 出现后才创建文件并写入已有记录，之后再逐条追加。

![Pi 新会话从内存记录到首次写入文件的过程](../diagrams/generated/pi-session-first-write-v3.png)

*图示新建、尚未写过文件的会话。已有空文件初始化和格式迁移有另外的处理路径。*

重新打开会话时，Pi 根据记录重建当前分支、模型设置和压缩后的消息视图。历史实验中，两个独立进程通过同一 session 恢复了之前保存的合成信息。这验证了正常保存后的恢复路径；它没有替代进程崩溃、半写入文件或工作区漂移的故障检查。[持久化与恢复细节](08-sessions-persistence-recovery.md)

## 工作流需要改变时，扩展接在哪里

读到这里，Pi 的运行主线已经比较清楚：准备请求、调用模型、执行工具、处理结果，再管理继续和结束。Extensions 可以在这些交接位置参与处理。

例如，项目需要限制某类文件修改，可以在工具执行前检查调用并阻断；需要给下一次请求补充项目状态，可以调整请求消息；工具返回了丰富的结构化数据，也可以分别安排模型看到的内容和界面显示的数据。扩展因此能改动运行行为，而不只是增加一个菜单命令。

这种能力依赖明确的生命周期。`AgentSession.reload()` 会刷新设置和资源、重建 extension runner 与工具注册表，再按条件发送重新启动通知。扩展若需要跨 reload 保留状态，可以利用会话记录；旧的内存 closure 不会因此自动变成持久状态。[扩展状态与 reload](05-models-tools-extensions.md#扩展怎样形成可迭代的工作流)

运行权限也需要放在同一张图景里理解。Pi 默认工具和 extensions 使用启动进程的权限。Project trust 管的是项目启动资源加载，工具 hook 管的是经过它的调用，实际文件和网络隔离则由部署环境提供。一个确认对话框并不会自动覆盖扩展自己发起的所有副作用。[信任与执行边界](06-permissions-sandbox-workspace.md)

Mario 的设计回顾强调对上下文和交互过程的控制。对应到当前代码，这个方向体现为请求、工具、状态和生命周期上的多个可调整入口。它能解释为什么读 Pi 时，除了看循环本身，还需要看这些交接位置由谁持有、何时更新。

## 把这些机制放回最初的请求

现在再看“读取配置，告诉我端口”这件事，可以把职责放回源码中的几个对象。

`AgentSession` 接收并准备输入，组织 extensions 和产品级收尾。`Agent` 保存当前消息、工具配置和队列，由 `runAgentLoop` 推进一轮轮模型与工具处理。模型请求经过 `ModelRegistry` 和兼容适配入口，消息记录则交给 `SessionManager` 管理。

![Pi 当前 AgentSession 路径的整体职责](../diagrams/generated/pi-system-overview-session-only.png)

*循环分别请求模型和调度工具，再接收各自的结果；会话管理保存记录。图中聚合了职责，具体事件和落盘时机在前文展开。*

如果请求成功，一次用户输入可以经过多个 turn 后结束；如果遇到可重试错误，产品层可能启动另一段低层运行；如果历史太长，后续请求会改用摘要与保留片段。最终看到的回答，来自模型选择动作与程序维护这些状态和边界的共同过程。

## 继续阅读与查证

正文以读取配置等例子串起机制。另有一条保留的真实 read 轨迹：模型读取合成文件中的 `314159` 后，在第二轮给出答案。网络失败和配置修改等叙述用于说明源码规则，未拼接进这条真实轨迹。

分析固定于 `v0.80.7 / 818d674` 的当前产品路径。历史真实模型记录与本地受控测试支持的范围不同，详见下列资料；本次只是重组文章，没有新增运行实验。

- [专题阅读与查证索引](reading-guide.md)：按问题进入源码、消息示例和实现细节。
- [真实请求轨迹](00-task-walkthrough.md)、[实验记录](11-runtime-experiments.md)与[复现方法](13-coverage-reproducibility.md)：查看实际验证过什么。
- [外部解读与源码对照](17-external-perspectives.md)：查看作者、使用者文章及其版本边界。
- [结论与证据索引](14-source-claim-index.md)、[术语表](16-glossary.md)：查找具体字段、事件和源码位置。

文中插图沿用同一组已复核的机制说明。[图像元数据](../diagrams/generated/metadata.json)保留对应证据、生成参数和审核记录。
"""

REPORTS['00-task-walkthrough.md'] = r"""# 一次请求的运行过程

![Pi read 场景的两轮模型与工具处理](../diagrams/generated/pi-observed-turn.png)

图按时间顺序展示历史 R-002：第一次响应请求 read，工具结果进入第二次模型请求，随后依次结束低层运行和产品收尾。AgentSession 是产品编排层，toolResult 是工具返回的消息。证据：S-001、S-002、R-002；图中未加入该场景没有触发的压缩或重试。图片经本次复核后继续使用，[提示词与审核记录](../diagrams/generated/metadata.json)。

这里用历史 `R-SCENARIO-002` 串起当前 Coding Agent 的主路径。场景只开放 `read`，要求读取合成文件并返回其中的 `314159`。归一化轨迹记录了两轮模型处理、一次工具调用和最终 settled；源码补充轨迹中看不到的状态所有权。[R: R-002]

## 从输入到第一次模型请求

CLI 创建或打开 session 后，print/JSON 模式调用 `AgentSession.prompt()`。产品层依次处理 extension command、`input` hook、skill/template 展开；若已有运行，则把新输入交给指定队列。普通空闲路径检查模型和鉴权，必要时处理旧上下文，然后构造 user message，追加待发送的消息和 `before_agent_start` 返回的内容。[S: S-002]

`AgentSession._runAgentPrompt()` 调用 `Agent.prompt()`。后者建立当前 context/config 快照，交给 `runAgentLoop()`。每次模型请求前，消息先经过 `transformContext`，再经 `convertToLlm` 转为 provider 支持的消息；system prompt 和 active tools 一并传入模型适配层。[S: S-001, S-022, S-024]

本场景关闭了 skills、extensions、prompt templates 和 context files。上面这些入口是源码中的完整输入路径，真实轨迹实际经过的是其中的最小配置。

## 模型请求读取文件之后

模型第一轮返回 assistant message，其中包含 `read` 调用。低层循环等这条 assistant message 完成后才组织工具批次。

1. 发出 `tool_execution_start`，按名称查找工具并校验参数。
2. 执行可选的 `beforeToolCall`；在产品层，它对应 extension 的 `tool_call` hook。
3. 调用 `read.execute`，获得文件内容，之后应用可选的 result hook。
4. 发出执行结束事件，构造对应的 `toolResult`，把它交回消息处理和上下文。
5. 进入下一轮模型请求。此时模型能看到前一条工具调用和它的结果。[S: S-001, S-003, S-018]

`Agent` 在 `message_end` 时更新内存消息。`AgentSession` 等待 extension 的消息处理后把消息交给 `SessionManager`。本场景使用 `--no-session`，因此有内存消息处理而没有普通会话文件写入。[S: S-019; R: R-002]

## 第二次请求为何会发生

工具批次完成后，低层循环把 `toolResult` 加入 context，并检查是否还需继续。这个 read 场景继续请求模型，第二条 assistant message 给出最终文本。没有新的工具调用或排队输入后，低层循环发出 `agent_end`；产品层处理完后续工作，再发出 `agent_settled`。[R: R-002; S: S-001, S-002]

| 轨迹中的步骤 | 消息或状态变化 |
|---|---|
| 用户输入 | user message 进入本次运行 |
| 第一次 assistant 完成 | 历史中增加带 `read` 调用的 assistant message |
| read 结束 | 增加包含合成文件值的 toolResult |
| 第二次 assistant 完成 | 增加最终回答 |
| `agent_end` / `agent_settled` | 低层运行结束，再完成产品层收尾 |

完整事件见[归一化轨迹](../traces/normalized/R-002-read-tool.normalized.jsonl)。归一化文件保留事件类型和统计字段；合成文本及工具结果位于对应 raw 记录。它没有捕获完整 HTTP 请求包，因此“请求怎样构造”同时依据源码解释。

## 接下来需要分开的路径

压缩、重试、动态工具更新和分支恢复在其他章节单独解释。该 read 场景没有触发这些行为。新的本地 mock/faux 测试进一步检查了并行结果顺序、异步事件处理、压缩后续行为和会话树重建，见[实验记录](11-runtime-experiments.md)。
"""

REPORTS['01-scope-method.md'] = r"""# 范围与方法

本报告分析 `earendil-works/pi` 的 `v0.80.7`，commit 为 `818d67457cdd6b60bce6b121d16b23141c252dd8`。2026-10-20 复核时，本地 checkout 与该 commit 一致，工作区干净。本轮聚焦当前 Coding Agent 的 `AgentSession → Agent → runAgentLoop` 路径，以及直接支撑它的模型、工具、上下文和会话服务。

## 本次做了什么

重新跟踪了 `AgentSession → Agent → runAgentLoop`，检查工具 preflight/执行/回填、消息事件与持久化的顺序、模型兼容入口、动态配置刷新、压缩条件，以及 session 文件创建和分支重建。随后在固定源码的临时副本中执行定向测试，产物保存到 `traces/checks/`。其中 mock/faux 用确定性的测试响应替代真实模型，以便触发指定分支；preflight 指执行工具前的查找、参数校验和 hook 判断。

历史报告中的真实 SiFlow 文本、read 和跨进程 resume 场景继续保留。本次没有重新调用外部模型。`manifest.execution` 描述历史运行配置，`manifest.review` 描述本次复核，二者的证据时间和验证范围分别记录。

## 证据怎样阅读

| 标记 | 来源 | 阅读方式 |
|---|---|---|
| D | 目标仓库文档 | 支持公开说明的行为或产品立场 |
| S | 固定版本源码 | 支持实现路径、数据结构与触发条件 |
| R | 历史真实模型运行 | 支持指定配置中实际出现的路径 |
| X | mock/faux、定向或故障测试 | 支持执行过的具体断言 |
| I | 分析推断 | 与实现事实分开陈述 |

`C-xxx` 是结论编号，链接到支持它的证据。`runtime_verified` 表示相应路径有运行证据，并不表示组件的全部配置都经过测试。报告以机制解释为主，设计评价留给后续分析。

## 对旧分析的实质修订

模型入口分别说明 `ModelRegistry/compat` 及其内置模型分派。`compat` 自身还会在内置模型路径中使用 `Models`，因此两者的关系需要按分派条件解释，详见[模型接口](05-models-tools-extensions.md)。这一处已同步修正 C-019、HIR 和[冲突记录](../evidence/conflicts.jsonl)。

压缩章节补上两种此前容易混淆的情况：成功 stop 响应 usage 越界时压缩但不重答；threshold 压缩后如果有排队输入，仍可继续处理。持久化章节补上首条 assistant 才触发新文件写入的条件。事件章节区分工具开始通知与 handler 真实执行。

## 本次运行环境

使用官方 Node 22.19.0，并按官方 SHASUMS256 校验归档。测试复用本机已有依赖；源码由 `git archive` 导出到临时目录，缓存关闭，临时配置和测试数据分开保存。测试子进程没有继承模型凭据环境变量，选用 mock/faux；这里采用临时目录隔离，未配置 OS 网络沙箱。脚本及各组命令、返回码和结果见[复现方法](13-coverage-reproducibility.md)。

本次不覆盖跨平台 sandbox、真实长上下文质量、生产运行频率、subagent 文件竞争或实际进程崩溃恢复。这些问题保留在[待验证路径](12-failure-modes-open-questions.md)，不影响已查明的具体源码顺序。

## 外部阅读的使用方式

本次检索筛选 16 篇作者文章、使用记录和技术解读，阅读了其中 15 篇的相关正文；1 篇只取得元数据与搜索摘要。来源、日期、版本和采用方式记录在 [external-sources.json](../evidence/external-sources.json)。多篇文章转述同一作者，不计为相互独立的验证。

作者关于自身设计目的的陈述记为 D；社区和使用者的解释记为署名观点或 I。实现细节仍以本地 `818d674` 的源码为依据。阅读促成了工具结果分流、reload 顺序和压缩预算的补充核查，新增 C-027 至 C-029；本轮没有新增运行实验或性能比较。
"""

REPORTS['02-interfaces-lifecycle.md'] = r"""# 入口、对象与生命周期

Pi 的 interactive、print/JSON 和 RPC 模式在 `main.ts` 分派，使用共同的 Coding Agent session 构建路径。模式层负责输入输出，`AgentSessionRuntime` 负责当前 session 及与 cwd 关联的服务，`createAgentSession()` 组合 `Agent`、`SessionManager`、设置、资源和模型注册表。[S: S-013, S-014, S-024]

## 对象怎样组合

`AgentSessionRuntime` 面对的是打开、替换、fork 和导入 session 等产品操作。发生 session/cwd 切换时，它负责清理并重建相关服务。`AgentSession` 面对的是一个已建立的 session，负责其 prompt、extensions、工具配置和运行收尾。

`Agent` 持有当前消息、model、tools、thinking level、输入队列和活动运行的取消信号。它把这些数据组成快照传给低层循环，并根据循环发出的事件更新自身状态。`SessionManager` 则持有记录树与文件索引；当前模型看到的消息是从树中选择和转换得到的视图。[S: S-008, S-019]

源码入口：[main.ts](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/main.ts#L650)、[sdk.ts](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/sdk.ts#L301)、[Agent](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/agent/src/agent.ts#L184)。

## 输入不一定立即成为模型请求

`AgentSession.prompt()` 先尝试执行 extension command；被处理后可直接返回。随后 `input` hook 可以处理或变换输入，skill/template 再展开文本。若 session 正在运行，调用方须指定 `steer` 或 `followUp`，输入进入对应队列；普通 prompt 不会同时启动第二套运行。这里按调用参数分流，不分析句子语义来猜队列。默认交互界面在运行中用 Enter 选择 steer、Alt+Enter 选择 followUp，详见[队列选择机制](03-core-loop.md#双队列对应两种交互意图)。[S: S-002, S-033]

空闲路径检查模型和鉴权，检查是否需要发送前压缩，构造 user message，追加 `nextTurn` 消息，再处理 `before_agent_start` 返回的消息及 system prompt。最后进入 `_runAgentPrompt()`。此处的源码顺序解释了同一段用户文字为何可能先被命令或 extension 消费。[S: S-002]

## 三个结束时刻

`turn_end` 结束一轮 assistant 响应及其工具处理。低层循环发出 `agent_end` 时，其事件流已到末尾；`Agent` 仍会等待监听者，再清理运行状态。`AgentSession` 随后检查重试、压缩和剩余队列，必要时再次调用 `Agent.continue()`，最后发出 `agent_settled`。[S: S-001, S-019; X: X-005]

`agent_settled` 表示产品层暂时没有这次运行的后续工作。成功回答、不可恢复错误和取消都可能走到收尾，所以自动化消费者还须检查最后的响应、错误或任务产物。

## 用一个读文件例子区分这些事件

假设用户要求“读取 `config.json`，告诉我端口”。下面按源码规则示意一次正常执行；它是教学例子，历史真实 read 场景另见[请求过程](00-task-walkthrough.md)。

```text
用户提交一次请求
│
├─ turn 1
│  模型回复：调用 read 读取 config.json
│  Pi 执行 read，得到 {"port": 8080}
│  工具结果进入上下文
│  → turn_end
│
├─ turn 2
│  模型看到结果，回复：服务监听 8080 端口
│  没有新的工具调用或排队输入
│  → turn_end
│
├─ agent_end：本次低层循环结束
├─ AgentSession 检查重试、压缩及剩余队列
└─ agent_settled：产品层完成收尾
```

这里是一条用户请求、两个 turn、一次低层运行。一轮 assistant 响应提出多个工具调用时，这些调用也可以属于同一个 turn。[S: S-001]

| 事件 | 回答的问题 |
|---|---|
| turn_end | 这一轮模型响应及工具处理结束了吗？ |
| agent_end | 这一次低层循环结束了吗？ |
| agent_settled | 产品层的这次运行收尾了吗？ |

产品层压缩可能单独调用模型生成摘要；这种辅助调用不直接计作上面低层循环的 turn。若重试次数耗尽，Pi 报错并收尾，也可以发出 `agent_settled`。这些事件说明运行阶段，端口答得对不对仍须检查回答与文件内容。[S: S-002, S-019, S-021]

## 模式层的区别

| 模式 | 输入与输出 |
|---|---|
| Interactive | TUI 输入、交互操作与 extension UI |
| Print | 等待调用完成后输出最终内容 |
| JSON | 在 stdout 输出 session header 与结构化事件 |
| RPC | 消费命令并返回带 id 的响应，同时转发 session 事件 |

历史真实运行覆盖 JSON 路径；其他入口的共享关系由源码确认。当前产品的运行状态与收尾顺序见 [AgentSession 的状态与运行收尾](10-implementation-details.md)。
"""

REPORTS['03-core-loop.md'] = r"""# 核心循环与工具执行

`runAgentLoop()` 接收本次输入、当前 context、模型及工具配置、事件接收函数和取消信号。它为消息数组建立本轮视图，发出起始事件，然后交给 `runLoop()`。`Agent` 是这个循环的状态包装，产品层的压缩和重试由 `AgentSession` 在其外部处理。[S: S-001, S-002, S-019]

## 一轮模型处理的顺序

1. 把待注入的 steering/follow-up 消息加入当前 context。
2. 先运行 `transformContext`，再运行 `convertToLlm`，与 system prompt 和 tools 组成请求。
3. 消费 provider stream：开始时加入部分 assistant message，delta 更新它，结束时用最终 message 替换。
4. 若 stop reason 是 `error` 或 `aborted`，结束本次低层运行。
5. 从完整 assistant message 取出 `toolCall`，组织工具批次并生成 `toolResult`。
6. 回填结果，发出 `turn_end`，调用 `prepareNextTurn` 刷新下一请求需要的配置。
7. 检查 host 的停止条件及 steering；内层可结束时，再检查 follow-up 队列。[S: S-001]

源码：[runLoop](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/agent/src/agent-loop.ts#L161)。这里的工具执行发生在 assistant response 完成之后；工具参数的流式增量本身不会立即触发 handler。

## 工具处理包含准备和执行两个阶段

每个调用先发出 `tool_execution_start`，再查找名称、执行可选的 `prepareArguments`、校验 schema、调用 `beforeToolCall` 并检查 abort。未知工具、非法参数、hook block 或准备阶段异常可以直接生成错误结果，不进入 `execute`。[S: S-018]

准备通过后，`execute` 获得 call id、校验后的参数、取消信号和进度回调。handler 抛出的异常被包装为错误结果；实际执行的调用随后进入 `afterToolCall`，允许调整 content、details、terminate 和 isError。最后发出结束事件并生成协议消息。

因此 `tool_execution_start` 的准确含义是“开始处理这个调用”。判断命令或文件操作是否发生，要结合 execute 计数、实际输出或副作用记录。`length` 截断路径也会发出 start/end，同时返回“未执行”的错误内容。[C: C-021; S: S-018]

## 并发完成与消息顺序

![并行工具为何有执行完成顺序和回填顺序两种顺序？](../diagrams/generated/pi-tool-order-v2.png)

A、B 是说明顺序的示例：B 可以先完成，但 toolResult 按模型调用次序 A、B 回填。时间条不表示实测耗时；tool_execution_start 只表示开始处理调用。证据：S-018、X-004。[提示词、生成参数与复核记录](../diagrams/generated/metadata.json)。

默认并行路径先按调用顺序完成各项准备，再启动允许执行的函数。`tool_execution_end` 可按实际完成顺序出现；`Promise.all` 保存原调用位置，随后按位置生成 `toolResult` 消息。

例如模型依次请求 A、B，B 先完成时，结束通知可以是 B、A，但下一轮模型看到的结果仍是 A、B。界面进度与模型上下文因此有不同的排序依据。本次 `X-004` 重新执行了相关定向测试。[C: C-015; S: S-018; X: X-004]

若全局 `toolExecution` 为 sequential，或批次中任一命中工具声明 `executionMode=sequential`，整个批次进入串行路径。串行路径每次准备并执行一个调用，处理结果后再进入下一个。

## 继续、终止与排队输入

有工具调用通常会触发下一次模型请求。一个特殊条件是已处理批次中的所有结果都声明 `terminate=true`，这会关闭工具引起的 follow-up；它仍需结合 steering、follow-up 和 host 停止条件判断整个运行是否结束。普通工具错误通常作为 `isError` 结果回到模型，使其有机会继续处理。bash 内部命令的网络错误也走这条路径；产品层重试 LLM API 请求是另一层处理，见[具体例子](10-implementation-details.md#bash-联网失败和模型-api-失败分别怎么处理)。[S: S-018, S-034]

steering 在当前 assistant 及其工具批次完成后的边界注入；它不会仅因入队就打断正在执行的工具。follow-up 在工具与 steering 都耗尽后取出。`Agent.continue()` 若发现最后一条是 assistant，会先尝试消费队列；没有可消费输入才拒绝从该状态继续。[S: S-001; X: X-004]

## 双队列对应两种交互意图

[Haochuan 的源码解读](https://blog.haochuanz.net/posts/agent-harness-04-pi)把两类队列理解为用户控制运行节奏的接口。[I: I-002]

在当前默认交互界面中，队列由提交动作选择；在 SDK/RPC 中，则由调用方指定。默认路径没有按消息语义调用 LLM 分类这一步。以下说明普通文本输入，extension command 或 input hook 可以提前处理输入。[S: S-002, S-033]

| Pi 正在运行时的默认操作 | 界面传入的参数 | 入队结果 |
|---|---|---|
| Enter 提交 | streamingBehavior: "steer" | steering 队列，在当前 turn 边界后注入 |
| Alt+Enter 提交 | streamingBehavior: "followUp" | follow-up 队列，在工具与 steering 耗尽时消费 |

对应的两种调用形式是：

```ts
session.prompt(text, { streamingBehavior: "steer" })
session.prompt(text, { streamingBehavior: "followUp" })
```

`AgentSession.prompt()` 检查 `isStreaming` 后，按 `options.streamingBehavior` 选择 `_queueSteer()` 或 `_queueFollowUp()`。运行中的普通 prompt 没有提供这个参数时会报错。SDK 也提供 `session.steer()`、`session.followUp()`，RPC 提供 `steer`、`follow_up` 命令。[S: S-033]

### 同一句话可以进入不同队列

以“忙完之后，再检查文档”为例：按 Enter 会进入 steering，消息可能在下一次模型请求中就出现；模型收到后是否按文字要求推迟执行，是模型的行动选择。按 Alt+Enter 则进入 follow-up，程序把消息本身延后递交。

因此，程序控制“何时让模型看到消息”，模型在看到消息后判断“如何回应和行动”。即使文字写着“立即改变方向”，用 follow-up 方式提交也会先按该队列的时机等待。[S: S-001, S-033]

### 空闲、压缩与可配置键位

这些按键是默认绑定，可以通过 keybindings 调整。空闲时，Alt+Enter 会调用普通提交入口，开始处理新请求。压缩期间，交互层先保存消息及其 steer/followUp 模式，之后再按该模式递交；类型仍来自用户的提交动作。[S: S-033]

队列的消费时机由低层 loop 控制：steering 不自动撤销已经执行的动作，follow-up 也不必等到产品层 `agent_settled` 才被消费。它可以在同一低层运行发出 `agent_end` 前进入下一轮。[S: S-001; X: X-004]

源码：[Enter 的运行中提交](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/modes/interactive/interactive-mode.ts#L2800)、[handleFollowUp](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/modes/interactive/interactive-mode.ts#L3669)、[AgentSession 分流](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/agent-session.ts#L1120)。

## 消息如何同步到 session

`Agent.processEvents()` 先把最终消息放入 live state，再逐个等待监听者。`AgentSession` 先等待 extension 的 `message_end`，必要时就地替换同一个消息对象，再通知外部监听者并追加 session entry。这样低层循环、产品层和持久化可以处理同一最终消息。[S: S-019]

本次异步 hook 回归测试检查了 assistant/toolResult 记录顺序，以及 `tool_call` hook 运行时 assistant 消息已进入会话分支。外部 session listener 则在 append 前被通知，不能仅凭回调开始就判断磁盘已经更新。[C: C-022; X: X-005]
"""

REPORTS['04-context-memory-compaction.md'] = r"""# 上下文、消息转换与压缩

Pi 同时维护持久会话记录、当前分支的应用消息和本次模型请求的消息视图。它们之间通过选路、hook 和类型转换连接。理解这几个阶段，才能判断一条信息何时进入模型、何时留在文件中。[S: S-008, S-022]

## 持久历史、当前分支与本次请求

Pi 需要管理会话记录、恢复状态和显示过程；模型每次请求只接收经过选择与转换的内容。同一条信息在这些层次中的表示和用途可能不同。

| 层次 | 包含什么 | 回答的问题 |
|---|---|---|
| 持久历史 | 已保存的消息、不同分支、模型切换、压缩记录和扩展数据等 entry | 之前记录了什么？ |
| 当前分支 | 从当前 leaf 沿 parentId 选出的一条路径；运行时还会追加新的内存记录 | 现在沿哪段对话继续？ |
| 本次请求视图 | 按压缩边界选出的消息，经过扩展处理和类型转换，再与 system prompt、tools 组装 | 这一次模型实际收到什么？ |

例如，你先尝试方案 A，随后回到共同历史，改试方案 B。下面是教学示意：

```text
共同历史：分析登录问题
    ├─ 方案 A
    │   ├─ 阅读相关文件
    │   └─ 得到一大段失败日志
    │
    └─ 方案 B
        └─ 继续分析 ← 当前 leaf
```

完整历史可以保留两条分支。沿 B 继续时，重建路径通常选择“共同历史 + B 分支”，不会因为 A 的日志仍在文件中，就自动把它们全部加入本次请求。如果切换时生成分支摘要，一部分信息可以通过摘要带回。[S: S-008]

同一分支还可能经过压缩。例如，较早消息已经被总结，近期片段被保留：

```text
保存的记录：早期消息 + 近期消息 + compaction entry
请求用消息：压缩摘要 + 保留的近期消息 + 之后的新消息
```

旧消息可以继续保存在会话文件中，当前请求用摘要代表其中一部分。`buildSessionContext()` 负责结合分支和压缩边界构建应用消息，后面才进行消息变换与类型转换。[S: S-008, S-022]

这是数据视图之间的关系。恢复会话、切换分支或压缩时会重建相应上下文；正常 loop 在内存中追加消息，每次模型请求再转换当前消息列表。它不要求每次请求都从磁盘重读完整 session。文件首次创建和追加时机见[会话持久化](08-sessions-persistence-recovery.md)。

## 为什么先看上下文控制面

[Mario 的设计回顾](https://mariozechner.at/posts/2025-11-30-pi-coding-agent/)把可检查、可控制的模型上下文列为开发 Pi 的动机。[D: D-011]

这个角度适合用来阅读 `AgentSession`：先找信息在哪个阶段进入，再看谁能改写它。`before_agent_start`、`context`、active tools 和会话分支分别作用于不同位置；“系统提示短”只描述其中一部分，不能代表安装扩展后的整次请求有多大。[S: S-002, S-004, S-008, S-023]

## 信息从哪里进入

system prompt 由 `buildSystemPrompt()` 组合默认或自定义提示、工具说明、project instructions、skills 索引和 cwd。skills 索引在有 read 工具时加入；`/skill:name` 在输入处理时读取正文并展开成用户侧文本。AGENTS/CLAUDE 项目指令与受 project trust 控制的 `.pi` 启动资源有不同的加载边界，见[信任与执行](06-permissions-sandbox-workspace.md)。[S: S-002, S-004, S-005, S-006]

当前分支由 `SessionManager.buildSessionContext()` 生成。工具结果进入后续消息，extension 的 `before_agent_start` 可追加 custom messages 或覆盖本次 system prompt；`context` hook 则在每次 provider 请求前处理消息视图。[S: S-001, S-003, S-008]

## 应用消息怎样变成 provider messages

![持久历史怎样变成本次模型请求，system prompt 和 tools 在哪里加入？](../diagrams/generated/pi-context-views-v3.png)

会话记录先选出当前分支，有压缩记录时组合最新摘要与保留消息，再经过消息变换和类型转换；system prompt 与 active tools 在请求组装处单独加入。图示源码中的视图转换，不表示压缩触发频率。证据：S-001、S-004、S-008、S-022。[提示词、生成参数与复核记录](../diagrams/generated/metadata.json)。

低层循环依次调用 `transformContext → convertToLlm`。前者允许 extension 调整请求用的消息；后者通过普通 TypeScript 分支转换类型、整理字段和过滤消息，不调用 LLM。转换结果是 pi-ai 的 `Message[]`，provider 适配器之后才将其变成具体 API 的请求格式。system prompt 和 active tools 在消息转换后单独加入请求 context。[S: S-001, S-022]

| 应用消息 | `convertToLlm` 的处理 |
|---|---|
| user / assistant / toolResult | 保留 pi-ai 标准消息，之后由 provider 适配器继续转换 |
| custom | 将内容包装成 user message |
| bashExecution | 把命令、输出和状态组织成 user 文本；excludeFromContext 为 true 时过滤 |
| compactionSummary | 给已有摘要加上说明与 summary 标签，再包装为 user message |
| branchSummary | 给分支摘要加上相应说明，再包装为 user message |

以下例子省略时间戳等字段，用于说明转换过程，不是新增运行轨迹。

### 扩展消息：界面隐藏与模型可见是两个属性

扩展可以注入这样一条应用消息：

```json
{
  "role": "custom",
  "customType": "project-rule",
  "content": "不要修改公共 API。",
  "display": false,
  "details": {"source": "project-settings"}
}
```

转换后，消息正文成为：

```json
{
  "role": "user",
  "content": [{"type": "text", "text": "不要修改公共 API。"}]
}
```

`display: false` 控制 TUI 显示，不能据此判断模型看不到内容。`customType`、`display` 和 `details` 没有被自动展开到这条 user 消息中。转换后的 `role: "user"` 表示模型消息格式中的位置，内容也可能来自扩展，而不一定由人刚刚输入。[S: S-022]

还要分清持久记录的 `type` 和应用消息的 `role`：

| 持久记录 | 重建与发送路径 |
|---|---|
| `type: "custom"` 的 CustomEntry | 保存扩展状态，例如计数器；默认不参与模型上下文 |
| `type: "custom_message"` 的 CustomMessageEntry | 先重建为 `role: "custom"` 的应用消息，再由 convertToLlm 转为 user message |

扩展因此可以保存内部状态，也可以显式注入给模型看的内容，两种记录有不同的入口。[S: S-008, S-022]

### Bash 执行记录：用户命令与模型工具调用分别表示

用户直接输入 `!npm test` 时，可以产生这种内部记录：

```json
{
  "role": "bashExecution",
  "command": "npm test",
  "output": "1 test failed",
  "exitCode": 1,
  "cancelled": false,
  "truncated": false
}
```

转换函数将命令、输出和退出状态整理成 user 文本。例如，下面用 JSON 转义表示换行，代码围栏也是正文的一部分：

```json
{
  "role": "user",
  "content": [{
    "type": "text",
    "text": "Ran `npm test`\n```\n1 test failed\n```\n\nCommand exited with code 1"
  }]
}
```

若记录带 `excludeFromContext: true`，例如 `!!` 命令对应的排除语义，`convertToLlm` 会过滤这条消息。记录仍可供应用管理，但不通过这条转换路径进入请求。

模型主动请求 bash 工具时，返回的是与 tool call 关联的 `toolResult`；上面的 `bashExecution` 描述用户直接执行命令的记录。不能把所有 Bash 输出都当作转换后的 user message。[S: S-022]

### 压缩摘要：包装已有文本，而不是再次总结

应用消息可以用专门的类型保存摘要：

```json
{
  "role": "compactionSummary",
  "summary": "正在修复登录问题，已排除数据库连接故障。",
  "tokensBefore": 80000
}
```

`convertToLlm` 把 summary 包装成一条 user message，其文本类似：

```text
The conversation history before this point was compacted into the following summary:

<summary>
正在修复登录问题，已排除数据库连接故障。
</summary>
```

`tokensBefore` 用于程序记录压缩前状态，不会自动成为摘要正文。摘要文字在更早的压缩步骤中生成；这里仅添加说明和标签。`branchSummary` 也采用相似的文本包装方式。[S: S-022]

源码：[消息定义与转换](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/messages.ts#L33)、[会话记录到应用消息](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/session-manager.ts#L375)、[请求组装](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/agent/src/agent-loop.ts#L282)。[C: C-025]

## 排查模型为什么没看到一条信息

沿数据经过的位置依次检查：

1. 信息是否已经进入会话记录，还是只在界面或扩展内部？
2. 记录是否属于当前 leaf 选出的分支？
3. 原始消息是否已被压缩摘要代表？
4. `transformContext` 是否过滤、替换或追加了消息？
5. `convertToLlm` 保留了哪些字段，是否过滤了整条消息？
6. provider 适配器最终怎样组织实际请求？

确认“文件里有这条记录”只回答了第一个阶段的一部分。请求视图还经过分支选择、摘要与消息转换；需要对照这些阶段或捕获的请求，判断模型实际收到的内容。[S: S-001, S-008, S-022, S-026]

## 压缩前先判断响应与历史边界

`AgentSession._checkCompaction()` 在低层运行结束后和发送新 prompt 前调用。它先检查开关和 abort 条件，再检查模型是否相同、assistant 响应是否早于最新 compaction boundary。旧模型的 overflow 和压缩边界之前的 usage 不能直接用于触发当前上下文的同一条恢复分支。[S: S-021]

接下来分两类处理：

- Overflow：当前模型报告上下文越界或 usage 超过窗口。若响应已经以 `stop` 完成，则压缩但不重答。需要恢复的错误响应最多进行一次 compact-and-retry，避免同一次恢复无限循环。
- Threshold：上下文接近配置阈值时压缩。已完成回答不会因此重新生成；如果压缩期间有输入入队，产品层仍可继续消费这些输入。

发生错误或 usage 为零时，代码会从最后有效的 usage 估算上下文，并检查估算来源是否已经被此前压缩淘汰。本次 `X-008` 执行了 15 项 faux/controller 用例；`X-005` 另覆盖压缩后队列续跑。[C: C-024]

## 已经有阈值检查，为什么还会溢出

Threshold 根据已有用量或估算，在接近窗口上限时预先腾空间；Overflow 则处理已经收到的越界信号。提前检查仍有时间和信息上的边界。

当前默认路径主要在发送新 prompt 前、一次低层运行结束后检查压缩。发送新 prompt 前的检查发生在构造并加入这次新用户消息之前；一次低层运行内部可以连续处理多个工具批次，默认的逐轮刷新 hook 也没有在每次工具结果返回后执行相同的压缩检查。因此，上一次检查之后，新的输入或工具输出仍可能让下一次请求突然变大。[S: S-021]

例如，假设窗口是 100,000 token，预留 16,384，触发阈值就是 83,616。检查时用量为 75,000，尚未触发；后续加入约 30,000 token 的材料，下一次请求就可能越过窗口。这个数值例子只说明检查间隙的增长，不是测得的 Pi 运行轨迹。用量估算与 provider 实际计数的差异，也会让预防性判断存在误差。

源码中的 overflow 分支还包含“响应已经成功 stop，但报告的输入用量超过本地配置窗口”的情况。这时只压缩、不重答；需要恢复的溢出响应才使用一次 compact-and-retry 的限额。因此，两条分支分别处理提前腾空间和收到越界信号后的状态，不能把所有 overflow 都理解成 API 已经拒绝请求。[S: S-021]

## 两个压缩预算各控制什么

当前设置中 `reserveTokens` 默认 16384，`keepRecentTokens` 默认 20000。前者进入 `contextTokens > contextWindow - reserveTokens` 的触发判定；后者用于向后估算需要保留的近期片段。改变预留预算不等于改变同样数量的保留消息。[C: C-029; S: S-028, S-029]

`findCutPoint()` 使用逐条消息的 `estimateTokens()` 累计保留片段的估算体积。触发检查使用的 `estimateContextTokens()` 则会优先利用最近有效 assistant usage，并估算后续新增消息；两处估算服务于不同阶段。切分还受合法消息边界约束，保留量不是 provider tokenizer 的精确测量。[S: S-021, S-029]

这两类预算在部分解读中被混称为 reserve。对照配置 getter 和切点函数，可以把“什么时候压缩”与“保留哪段历史”分开验证，详见[外部来源核对](17-external-perspectives.md)。

## 哪些消息保留原文，哪些送去总结

默认路径先由代码选出近期连续片段，再由 LLM 提炼较早消息的内容。以下示例沿用“排查启动问题”的任务，数字与切点用于解释源码，不代表新增实验。[S: S-029, S-035]

假设当前分支积累了约 80,000 token 的对话。`findCutPoint()` 从最新 entry 往前走，把其中上下文可见消息的估算体积逐项相加，达到 `keepRecentTokens` 后选择合法切点。默认预算是 20,000，因此可以先把结果理解成：

```text
较早的连续消息，约 60,000 token │ 最近的连续消息，约 20,000 token
          交给模型生成摘要     │          保留原文
```

这里按 token 体积选择，而不是固定保留多少条消息。`estimateTokens()` 对文本主要采用字符数除以 4 的启发式估算，图片等内容另有估算处理；再加上边界调整，实际保留量不保证恰好等于预算。较早的重要要求也可能落进摘要区域，其后续可见性依赖摘要是否准确保留它。[S: S-029]

### 工具调用与结果不能从中间拆开

假设某段消息是：

```text
assistant：调用 read("config.ts")
toolResult：文件内容……
assistant：根据配置，接下来检查启动脚本……
```

代码不允许把 `toolResult` 当作保留片段的第一条消息。找到预算位置后，它会选择该位置或更靠后的合法切点：若从包含工具调用的 assistant 消息开始保留，后续结果也保留；若切到后面的 assistant 消息，前面那组调用和结果一起进入待压缩部分。这样不会只留下一个失去对应调用的工具结果。[S: S-029]

### 一次任务太长时，给保留的后半段补上来由

合法切点可以是 assistant 消息，所以一次用户要求产生的长执行过程，也可能被分成两段：

```text
更早的对话
用户：帮我修复启动问题
assistant：读取配置、修改启动脚本
toolResult：修改完成
                           ← 从这里开始保留原文
assistant：执行测试
toolResult：端口冲突
assistant：继续排查……
```

这时 `prepareCompaction()` 找到该段交互的起始输入，将“更早的对话”和“本次任务被切掉的前半段”分别准备。常规压缩路径为前者生成历史摘要，再为后者生成专门的前缀摘要，交代原始要求、早期进展，以及理解后半段需要的信息。两份摘要合并到同一条 compaction 记录中，后面接保留的原文。[S: S-035]

```text
历史摘要 + 本次任务前半段摘要 + 本次任务后半段原始消息
```

源码称这种情况为 `split turn`。压缩模块在这里按 user、Bash 执行记录或其他用户侧消息寻找交互起点；它与低层循环中“一次模型响应及其工具处理”的 turn 不是同一个计数单位。一次用户任务可以跨过多个低层 turn。

### 模型负责把旧内容写成什么摘要

普通历史摘要的提示词要求覆盖目标、用户约束与偏好、已完成和进行中的工作、阻碍、关键决定、下一步及必要上下文，并要求保留准确的路径、函数名和错误信息。长任务的前缀摘要则侧重原始要求与后半段需要的背景。代码还会从工具调用中提取读过、修改过的文件路径并附到摘要中。[S: S-035]

已有压缩记录时，准备阶段取出上次摘要与之前保留的起点；历史摘要更新路径会把旧摘要和本次需要总结的消息一起交给模型。后续压缩通常是在已有摘要上继续整理，不需要每次重读所有已被摘要代表的原始消息。摘要是有损的信息整理，提示词要求保留某项内容，并不等于它一定完整保留了该项内容。

以上描述默认摘要生成路径。扩展可以在 `session_before_compact` 中取消或提供压缩结果，具体配置需要沿扩展路径另查。[S: S-021]

源码：[切点与消息体积](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/compaction/compaction.ts#L240)、[摘要提示词](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/compaction/compaction.ts#L441)、[压缩准备与分段摘要](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/compaction/compaction.ts#L633)。

## 摘要怎样替换当前消息

`_runAutoCompaction()` 从当前 branch 准备压缩。`session_before_compact` 可以取消或提供摘要；常规路径则调用模型生成 summary。成功后按以下顺序处理：

1. 追加带 `summary`、`firstKeptEntryId`、`tokensBefore` 的 compaction entry。
2. 从当前会话树重建 context。
3. 用重建结果替换 `agent.state.messages`。
4. 发出压缩完成通知，并按恢复标记或剩余队列决定是否继续。[S: S-021]

重建结果包含最新摘要、从 `firstKeptEntryId` 开始保留的旧消息，以及压缩 entry 之后的新消息。旧记录仍在 session 文件中；当前请求使用的是选出的有效视图。错误响应也可能保留在历史中，但在重试前从 live context 移除。[S: S-008, S-010]

## 压缩后的消息列表长什么样

压缩成功后，Pi 把最新摘要放在消息列表前面，接上从 `firstKeptEntryId` 开始保留的消息，再接压缩记录之后加入的消息。近期消息分别保留角色、内容和调用关联关系。摘要内部可以合并历史总结与长任务前半段总结，但整段会话仍是一个消息数组。[S: S-008, S-022, S-035]

例如，较早的排查过程已经总结；近期原文保留了读启动脚本的调用、结果和回答；之后你又要求检查 Docker 配置。省略时间戳和 usage 等字段，内部列表可以表示为：

```js
[
  {
    role: "compactionSummary",
    summary: "正在排查启动端口，之前已检查项目配置……"
  },
  {
    role: "assistant",
    content: [{
      type: "toolCall", id: "call_1", name: "read",
      arguments: { path: "scripts/start.sh" }
    }]
  },
  {
    role: "toolResult", toolCallId: "call_1", toolName: "read",
    content: [{ type: "text", text: "启动脚本内容……" }]
  },
  {
    role: "assistant",
    content: [{ type: "text", text: "启动脚本会读取 PORT 环境变量。" }]
  },
  {
    role: "user",
    content: [{ type: "text", text: "生产环境 PORT=8080，请检查 Docker 配置。" }]
  }
]
```

发送前，`convertToLlm` 将第一条摘要包装成带说明和 `<summary>` 标签的 user 消息；普通 assistant、toolResult 和 user 继续保留对应类型。system prompt 与工具定义在统一请求 context 中单独加入：[S: S-001, S-022]

```text
systemPrompt：当前系统提示
messages：摘要 user → 保留的 assistant / toolResult 等消息 → 后续新消息
tools：当前启用的工具定义
```

立即压缩完成时，尚未消费的队列输入还不在这份列表中，之后才会加入。到了 provider 适配器，system prompt 又可能成为 API messages 中的 system/developer 消息；模型服务还会把角色和工具定义编码为具体模型的输入。完整过程见[请求编码与两种模型示例](18-model-input-encoding.md)。

## 压缩期间提交的新输入怎样接上来

假设 Pi 已完成一轮排查，正在做阈值压缩：把消息 1～80 总结成摘要，保留消息 81～100。此时你在终端提交：“生产环境设置了 PORT=8080，接下来检查 Docker 配置。”这些消息编号只用来说明先后关系。

摘要调用使用开始时准备好的历史材料。终端编辑框继续接收输入，普通文本先存入 `compactionQueuedMessages`，并显示等待压缩完成的提示。新要求不会被临时加入已经进行中的摘要调用，也不会在摘要生成的同时启动相应的任务处理。[S: S-036]

```text
开始压缩：准备旧历史，调用模型生成摘要
用户补充：新要求暂存在输入队列
摘要完成：保存 compaction entry，重建为“摘要 + 保留消息”
继续处理：提交队列输入，模型看到“摘要 + 保留消息 + 新要求”
```

`compaction_end` 通知终端调用 `flushCompactionQueue()`。具体怎样续跑，取决于是否还有待恢复的运行：[S: S-036]

- 没有待恢复重试时，第一条排队的普通输入通过 `session.prompt()` 提交；其余输入按记录的 steering / follow-up 类型进入相应队列。上一轮已经完成的回答不会因此重答。
- 有待恢复重试时，输入按原类型通过 `session.steer()` 或 `session.followUp()` 入队，由恢复后的循环在相应边界消费。follow-up 仍需等待当前工作与 steering 处理完。

终端的压缩暂存队列和 Agent 本身的 steering / follow-up 队列是两处状态。其他入口或扩展已经放入 Agent 队列的消息，则由 `AgentSession` 的续跑检查衔接：自动压缩成功后，没有恢复重试要求时，`_runAutoCompaction()` 返回 `agent.hasQueuedMessages()` 的结果，由外层运行流程决定是否调用 `Agent.continue()`。这个压缩方法本身并不直接调用 continue。[S: S-021, X: X-005]

本例描述压缩成功后的普通输入路径。已注册的扩展命令在终端有单独入口，不能据此推断所有命令都必须等待压缩。终端发送排队消息失败时会恢复暂存队列并显示错误。[S: S-036]

源码：[压缩期间提交](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/modes/interactive/interactive-mode.ts#L2783)、[压缩结束通知](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/modes/interactive/interactive-mode.ts#L3059)、[队列转交](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/modes/interactive/interactive-mode.ts#L3990)。
"""

REPORTS['05-models-tools-extensions.md'] = r"""# 模型接口、工具与扩展

当前 Coding Agent 的模型入口由 `ModelRegistry` 和 `pi-ai/compat` 连接；工具则由 registry 保存定义，active set 决定本次模型可见的能力。Extensions 可以在输入、消息、工具和 provider 边界参与处理。[S: S-003, S-023, S-024]

## 当前模型请求怎样分派

`createAgentSession()` 为 `Agent` 安装 stream wrapper。每次请求先通过 `ModelRegistry.getApiKeyAndHeaders()` 解析鉴权，合并环境、headers、timeout 和 provider retry 配置，再调用从 `pi-ai/compat` 导入的 `streamSimple()`。[S: S-024]

compat 内部有两个分支：模型匹配内置 catalog，且对应 API 没有被覆盖时，转给 `compatModels.streamSimple()`；否则按 `model.api` 从 API registry 取出实现再调用。自定义 `models.json` 和 extension 的 provider 注册由这套产品配置路径接入。

`Models` 在这里是 compat 内置分支使用的 provider/model 集合。产品层的注册、鉴权与 compat 分派共同构成当前 CLI 的模型路径。历史 SiFlow 场景证明指定自定义端点曾成功接入，并未遍历全部分派分支。[C: C-019; S: S-012, S-024; R: R-001, R-005]

定位：[sdk.ts](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/sdk.ts#L301)、[compat.streamSimple](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/ai/src/compat.ts#L265)。

模型分派选定调用实现后，provider 适配器负责 API 字段，服务端负责模型对应的序列编码。system、messages 和 tools 怎样在这两层转换，以及 Qwen3.8-27B 与 DeepSeek V4 Flash 的格式差异，见[从 Pi 的请求到模型输入](18-model-input-encoding.md)。

## Registry、active set 和工具说明

内置工具定义有 `read`、`bash`、`edit`、`write`、`grep`、`find`、`ls` 七个名称。新 session 的默认 active set 是前四个；CLI/SDK 选项可以调整可用集合。Extension 和 SDK custom tools 按名称加入注册表，同名定义可能替换当前实现。[S: S-003; C: C-004]

| 工具 | 默认新 session | 基本作用 |
|---|---|---|
| read | active | 读取文本或图片，处理分页与输出限制 |
| bash | active | 在 cwd 启动 shell，支持 timeout 与 abort |
| edit | active | 按 old/new 文本修改文件 |
| write | active | 创建或覆盖文件 |
| grep | 需显式启用 | 搜索文件内容 |
| find | 需显式启用 | 按 pattern 查找路径 |
| ls | 需显式启用 | 列出目录内容 |

工具 schema 来自 `agent.state.tools`。system prompt 中的工具摘要还取决于相应 `promptSnippet`；说明文字与真实 tool schema 是两个输出位置。`setActiveToolsByName()` 更新 active set 并重建基础提示；产品层的 `prepareNextTurn` 把当前工具、system prompt、model 和 thinking level 接到下一请求。[S: S-004, S-023]

本次动态工具测试验证了注册后的 registry、active set、来源元数据及 prompt 更新。完整的请求中途配置差分仍需独立测试。[C: C-026; X: X-005]

## 工具输出有模型与应用两个消费方

工具返回的 `content` 提供文本或图片，`details` 保存供日志或界面使用的结构化数据。`createToolResultMessage()` 把两者保留在应用消息中，TUI 的 result renderer 也能拿到两者。已经检查的 OpenAI Completions 和 Anthropic 序列化路径从 `content` 构造模型结果，没有自动把 `details` 展开成正文。[C: C-027; S: S-025, S-026]

例如，搜索工具可以把摘要放在 content，把界面需要的结构化命中项放在 details。这个例子说明如何使用接口，不代表当前 built-in 的具体返回格式。是否把 details 进一步暴露给模型仍取决于 extension 和 provider 实现，不能把这个字段当成保密区。

## Hook 在哪些位置生效

| Hook | 所在位置 | 对行为的作用 |
|---|---|---|
| input | skill/template 展开之前 | 处理输入或变换内容 |
| before_agent_start | 普通 prompt 进入 Agent 之前 | 追加 custom messages 或覆盖该次 system prompt |
| context | 每次模型请求的消息转换之前 | 变换请求消息视图 |
| message_end | 产品层处理最终消息时 | 可替换最终消息，随后进入监听通知和持久化 |
| tool_call | 参数校验之后、execute 之前 | 可阻断该调用并返回理由 |
| tool_result | 实际 handler 结束之后 | 调整 content、details 和错误标记 |
| provider hooks | header、payload、response 边界 | 调整请求或观察响应 |
| session hooks | compact、switch、fork 等操作周围 | 参与会话生命周期 |

`AgentSession` 安装的工具 hook 在执行时读取当前 extension runner，reload 因而可以换用新 runner。Extensions 与主进程拥有相同运行权限；工具 hook 的 block 约束经过该入口的调用，extension 自己的文件或进程操作另有执行路径。[S: S-003, S-019; D: D-002]

Skills 提供可发现、可加载的任务指令。MCP 和 subagent 在这个版本的默认核心中没有对应的内置工作流，可由 extension 接入。分析具体环境时，要检查实际加载的扩展和 active tools。[D: D-004]


## 扩展怎样形成可迭代的工作流

[Armin 的使用记录](https://lucumr.pocoo.org/2026/1/31/pi/)把持久扩展状态和热重载视为持续修改工具的基础。[I: I-001]

当前代码中，`appendEntry()` 把扩展数据写成 custom entry，`buildSessionContext()` 不会自动把这种 entry 送给模型。调用 `AgentSession.reload()` 时，方法先通知 shutdown，再刷新 settings、provider registry 和 resources，重建 runner 与 tool registry；存在相应 bindings 时，再发出 reload 原因的 `session_start`。扩展需要自己从会话记录恢复所需状态，不能假定旧 closure 或 UI 对象自动保持有效。[C: C-028; S: S-008, S-027]

[Julian Prokay](https://jprokay.com/post/018-pi-coding-agent)的任务管理实践将 CLI/SQLite 状态与 Pi 界面扩展分工。它提供了一个使用案例：业务状态可以由应用维护，Pi extension 负责把操作接入会话。[B-11，见来源目录]

## CLI、Skills 和命名工具怎样分工

[Mario 的浏览器工具文章](https://mariozechner.at/posts/2025-11-02-what-if-you-dont-need-mcp/)展示了按需读取说明、再组合脚本的做法。[D: D-012]

对应本版本，read/bash 提供读取说明和执行程序的入口；skill 负责指令的发现与加载，命名工具还提供 schema 校验和结构化回填。额外能力可以存在于工作区程序中，而不必每项都变成初始 tool schema。应检查实际 active set、加载内容和执行后端，而不是用“四个默认工具”推断能力上限。[S: S-001, S-002, S-003]

这也不构成 CLI 普遍优于 MCP 的证据。作者较早的[终端工具实验](https://mariozechner.at/posts/2025-08-15-mcp-vs-cli/)使用 Claude Code，结果随任务与接口形式而变化；其数字不属于本报告的 Pi 实验。
"""

REPORTS['06-permissions-sandbox-workspace.md'] = r"""# 项目信任、执行权限与工作区

Pi 的默认工具和 extensions 以启动进程的 OS 权限运行。Project trust 控制项目启动资源的加载；逐工具确认或路径保护由可选 extension 实现。容器、VM 或其他 OS policy 才提供相应的执行隔离。[D: D-002, D-007; S: S-006, S-007, S-017]

## Project trust 怎样决策

`resolveProjectTrusted()` 依次处理显式 override、是否存在需要信任的项目资源、extension 的 trust 决策、已保存的 trust 记录，以及 default policy。`ask` 模式在没有 UI 且没有前序决策时返回 false；有 UI 时让用户选择并按选项保存记录。[S: S-006]

`DefaultResourceLoader` 先用不信任项目的状态加载 bootstrap extensions，再解析 trust 并加载最终资源集合。受控对象包括 `.pi` 项目配置和相应资源。AGENTS/CLAUDE context 文件有自己的加载路径，不能用“未信任项目”推断所有项目文本均未进入 prompt。[S: S-005; D: D-002]

## 一次工具调用经过什么边界

工具进入 registry 后先校验参数，再经过可选 `tool_call` hook。hook 返回 block 会生成错误结果并跳过 handler。默认配置没有全局逐工具审批弹窗；`protected-paths.ts` 展示的是可选 hook 如何拦截 write/edit。[S: S-003, S-017, S-018]

内置 bash 在指定 cwd 启动 shell并继承进程环境；timeout 参数可选。Unix 分支使用进程组处理，abort/timeout 走终止进程树的逻辑。这里描述内置 bash backend；subagent 示例自己的 `spawn/kill` 行为应单独检查。[S: S-007]

| 边界 | 控制对象 | 阅读时需要保留的范围 |
|---|---|---|
| Project trust | 项目配置、包和 extensions 等启动资源 | 不构成后续 read/bash/write 的权限决策 |
| tool_call hook | 经过工具调用入口的命名 handler | extension 的直接 fs/process/network 操作不必经过它 |
| 工具路由到 guest | 被配置为委托执行的 backend | 未委托的 custom tool 仍可能在 host 执行 |
| whole-process container/VM | Pi 及其子进程的部署边界 | 挂载目录和网络配置决定实际可访问范围 |

工作区是工具访问的真实文件系统。切换会话分支会改变模型上下文，但没有为文件内容创建对应的事务式回滚。[C: C-008]

本次通过 mock/faux 检查部分工具阻断和事件逻辑，未部署容器/VM，也未运行完整的 extension 副作用矩阵。源码与官方安全说明见 [security.md](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/docs/security.md#L3)。

## 怎样理解外部文章中的安全评价

Haochuan 将这种职责划分评价为[明确的安全边界](https://blog.haochuanz.net/posts/agent-harness-04-pi)。本报告采用可检查的机制区分：trust 约束资源加载，hook 约束经过它的调用，OS/container/VM 约束实际执行权限。文章的评价不替代部署测试，也不能推出其他权限系统都无效。[D: D-002, D-007; S: S-006, S-017]
"""

REPORTS['07-subagents-delegation.md'] = r"""# 子代理与多进程编排

![Pi 的可选 subagent extension 与实验性 orchestrator](../diagrams/generated/pi-subagent-topology.png)

图展示源码中的两条可选路径：subagent extension 启动独立 child 并默认共享 cwd；orchestrator 管理独立 RPC Pi 实例。OPT 表示可选扩展，EXP 表示实验性实现，RPC 是进程间命令与事件通道。本次未运行这两条路径；证据：D-004、D-006、D-010、S-015、S-016。图片经本次复核后继续使用，[提示词与审核记录](../diagrams/generated/metadata.json)。

Pi v0.80.7 的默认 Coding Agent 不提供内置 subagent 工具。仓库另有 subagent extension 示例和实验性 orchestrator：前者让模型通过一个工具委托任务，后者管理多个 RPC Pi 实例。[D: D-004, D-006, D-010]

## Subagent extension 怎样启动任务

父代理调用 extension 注册的 `subagent` 工具后，示例按 agent name 找到定义，把任务交给一个独立 Pi 子进程。参数包括 `--mode json -p --no-session`；定义中的 model/tools 可进入子进程参数，system prompt 通过临时文件追加。

`getPiInvocation()` 尝试复用当前脚本与 runtime，或使用打包后的可执行文件，最后回退到 PATH 中的 `pi`。子进程 cwd 由任务参数指定，未指定时使用 parent 的默认 cwd。`spawn` 没有设置独立 env，因此通常继承父进程环境。[S: S-015]

源码：[runSingleAgent](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/examples/extensions/subagent/index.ts#L268)。

## 隔离和共享分别发生在哪里

| 维度 | 示例中的行为 |
|---|---|
| 进程 | 每个任务启动独立 Pi 子进程 |
| 模型上下文 | 新建 child 消息，不自动复制 parent 全部 history；task 和 chain 的前序输出显式传入 |
| 会话文件 | `--no-session`，通过父工具结果回收输出 |
| 工作区 | 默认共享 cwd，也可由单项任务覆盖 |
| 权限与环境 | 通常同一 OS user，继承进程环境；工具名单不构成 OS sandbox |
| 返回通道 | 解析 JSON 事件，收集 assistant 消息、usage、工具调用和最终结果 |

示例支持 single、parallel 和 chain。parallel 的任务数与并发数由示例常量限制；chain 逐项把前序结果传给下一项。它们改变任务组织方式，没有自动为共享文件建立冲突管理。

取消时示例向直接 child 发送 SIGTERM，五秒后按 `proc.killed` 条件尝试 SIGKILL。该标记与进程是否真正退出不是同一个判断；这里没有运行挂起进程测试，因此不把这一逻辑写成保证清理整个进程树。[S: S-015]

## Orchestrator 管理的是实例

`OrchestratorSupervisor` 为每个 instance 创建 RPC Pi 进程，转发事件和 UI 请求，维护 instance/session 元数据并处理进程退出。启动恢复会把先前处于 online/starting 的记录标为 stopped；这不恢复子进程当时的在途模型请求。[S: S-016]

这两条路径本次均为静态复核，未启动 child 或 orchestrator。它们的入口、context、工作区和恢复语义与默认单 session 路径分开记录。
"""

REPORTS['08-sessions-persistence-recovery.md'] = r"""# 会话、持久化与恢复

`SessionManager` 把会话存为带 `id/parentId` 的 JSONL entry 树。新 entry 以当前 leaf 为 parent，再把 leaf 移到自己。模型使用的是当前分支投影出的消息；文件保留的历史可能包含其他分支、旧错误、摘要及配置记录。[S: S-008]

## 内存记录何时写成文件

![新会话什么时候真正创建文件，之后如何追加？](../diagrams/generated/pi-session-first-write-v3.png)

对新建且尚未写过文件的持久会话，user/配置 entry 先留在内存，首条 assistant entry 触发创建文件并写入已有记录，之后逐条追加。已有空文件、格式迁移与分支副本另有条件路径。证据：S-020、X-006。[提示词、生成参数与复核记录](../diagrams/generated/metadata.json)。

`newSession()` 先生成 header、session id 和文件路径，初始化内存索引。每次 append 都先更新 `fileEntries`、`byId` 和 leaf，再调用 `_persist()`。

对尚未写过文件的新会话，`_persist()` 检查历史中是否已有 assistant entry。只有 user 或初始配置记录时先留在内存；首条 assistant entry 出现后，以排他创建模式写入当前全部记录。之后新 entry 逐条追加。[C: C-023; S: S-020]

因此 `getSessionFile()` 返回路径、`message_end` 已发生和数据已落盘是不同观察点。fork 的路径若只有 user 消息，也会延迟到 assistant 出现后写文件。本次 tree-traversal 测试覆盖了这个条件。[X: X-006]

普通新增历史采用追加方式；格式迁移、初始化已有空文件及创建含已有 assistant 的分支副本有明确重写路径。“append-only tree”描述普通历史追加和分支语义，不应理解为文件永远不重写。源码也未在这些写入步骤中提供与 workspace 共同提交的事务。[S: S-020]

## Branch 与 fork

`branch(entryId)` 在当前 manager 中移动 leaf，下一条 append 成为该点的子节点，已有历史保持不变。`createBranchedSession()` 则提取 root 到指定 leaf 的路径，创建新的 session id 和文件，并重建保留项的 parent 链及标签。[S: S-008]

`branch()` 更新当前 manager 的内存 leaf；随后新增 entry 的 parentId 记录分支关系。重新打开文件时，索引从已有记录重建。[S: S-008]

这些操作都改变会话视图，workspace 文件仍保持现实状态。恢复旧上下文后，工具下一次读取到的可能是后来修改过的文件。

## 会话树怎样支持临时探索

Armin 用[分支处理临时任务后回到主线](https://lucumr.pocoo.org/2026/1/31/pi/)说明会话树的用途。它为“为什么需要 branch，而不只有线性历史”提供了具体工作流。[I: I-001]

在本版本中，可以从已有 entry 开始一条支线，处理工具或调查问题，再选择回到较早 leaf；`branchWithSummary()` 可以追加支线摘要。原支线记录仍保留，下一次请求使用重新选出的分支。如果支线修改了文件，回到旧 leaf 后文件仍是修改后的状态。会话树控制对话视图，文件版本仍需独立管理。[S: S-008]

## Resume 怎样构建上下文

读取 JSONL 后，`buildSessionContext()` 从 leaf 沿 parent 链向上找到分支，恢复 model/thinking 设置。若有 compaction，选取最新摘要、保留片段和之后的消息，再把 entries 映射为应用消息。普通扩展 custom entry 不进入模型上下文。[S: S-008, S-022]

历史 `R-003/R-004` 在两个独立进程中创建并恢复同一 session，第二个进程在未重发 token 的提示中返回 `PI_RESUME_2718`。本次 `X-006` 另外验证会话树和 compaction-aware context 的进程内构建。[R: R-003, R-004; X: X-006]

## 非法文件如何处理

解析器跳过不能解析的行，再检查 session header。打开非空且不构成有效 session 的文件时，manager 抛出错误并保留内容；打开空文件时，可以写入新的 header。这些是具体的加载规则，不能推出任意中段损坏都能正确恢复 parent chain。[S: S-008, S-020]

本次 `X-009` 的五项进程内用例通过。CLI 用例首次因临时副本缺少 tsx 加载配置而在模块解析阶段失败；补上开发入口对应的加载方式后，`X-010` 验证友好报错与原文件保持不变。[X: X-009, X-010]

源码：[SessionManager](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/session-manager.ts#L788)、[_persist](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/session-manager.ts#L946)。
"""

REPORTS['09-observability.md'] = r"""# 事件与可观测性

Pi 的事件同时服务界面、extension 和产品状态处理。JSON 模式将 session header 与这些事件写到 stdout，RPC 除命令响应外也转发事件。当前核心提供生命周期事件，默认没有完整的 OpenTelemetry trace/span 关联模型。[D: D-005, D-009; R: R-001, R-002]

## 事件表示哪个阶段

| 事件 | 可确认的阶段 | 需要另外检查的内容 |
|---|---|---|
| message_start / update | 消息开始或流式内容变化 | 尚不是最终消息，也不等于落盘 |
| message_end | 最终消息进入状态/监听处理路径 | 当前监听位置、是否持久化、文件是否首次创建 |
| tool_execution_start | 开始处理一次工具调用 | handler 可能被校验、block 或截断保护跳过 |
| tool_execution_end | 该调用的结果处理完成 | 结果可能是执行错误或准备阶段拒绝 |
| turn_end | 一轮 assistant 及工具批次结束 | 后续可能有下一轮模型请求 |
| agent_end | 一次低层循环结束 | 产品层可能重试、压缩或消费队列 |
| agent_settled | 产品层本次运行收尾完成 | 最终结果是否成功仍要看任务或错误 |

这张表依据 `Agent.processEvents()`、`AgentSession._handleAgentEvent()` 和工具批次实现。外部监听者与内部持久化有明确先后，事件名本身不足以推断磁盘或 OS 副作用。[S: S-018, S-019]

## 执行事件与持久历史

工具批次的结束事件可以按完成顺序到达，而持久消息按模型调用顺序形成。Session JSONL 记录可恢复的会话内容和配置，不保存每一次内部回调耗时。要分析延迟，需要额外关联请求、工具和时间信息。

历史 read 轨迹归一化后呈现 `run.started → turn.started → assistant(toolUse) → tool.started/completed → toolResult → turn.completed → 下一 turn → run.completed → run.settled`。其中 `tool.started` 是分析脚本对 Pi 事件的映射，含义仍受上述阶段边界约束。[R: R-002]

## 轨迹保留什么

原始 JSON 输出可含用户输入、模型文本/thinking、工具参数和结果。当前 normalized trace 去掉这些内容，保留事件序号、角色、类型、长度、usage 和工具关联信息。本次 Vitest JSON 则保留断言名称、状态、耗时及失败信息，可从[实验章节](11-runtime-experiments.md)定位。

OTel/Sentry adapter 在这个固定版本的相关文档中属于设计方向。本报告按 scenario 和事件序号关联记录，未验证 exporter 或 collector 端链路。[C: C-014]

## 运行完成和任务答对需要分别观测

[Scott 的 my-pi 实践](https://scottspence.com/posts/building-my-pi-claude-code-alternative-with-pi)区分运行故障与完成后的错误回答。[Kahtaf 的领域 Agent 记录](https://kahtaf.com/blog/lessons-from-building-a-domain-agent/)则按路由、工具、证据和回答层定位问题。[I: I-003]

当前 Pi 的 event stream 能帮助还原请求和工具经过了哪些阶段，任务产物是否符合要求仍需要单独的验收。`agent_settled` 也会在错误或取消收尾后出现。本报告的 controller 测试因此只支持所断言的机制，不当作真实任务成功率；外部项目加入的 telemetry、脱敏和评测组件也不记为默认 Pi 能力。[S: S-019]
"""

REPORTS['10-implementation-details.md'] = r"""# AgentSession 的状态与运行收尾

`AgentSession` 把输入准备、extension、模型配置和会话存储接到 `Agent` 上。`Agent` 驱动低层循环并维护消息；产品层在循环结束后判断是否还有重试、压缩或排队输入需要处理。[S: S-002, S-019]

## 状态分别由谁持有

| 所有者 | 关键状态 | 何时使用 |
|---|---|---|
| AgentSession | `_isAgentRunActive`、`_lastAssistantMessage`、重试与 overflow 恢复标记 | 判断产品运行是否仍在继续，以及最后响应应走哪条恢复路径 |
| Agent | live messages、model、tools、thinking level、输入队列、取消信号 | 构造模型请求、执行工具、推进低层循环 |
| SessionManager | entries、`byId`、`leafId`、session 文件与 flushed 状态 | 追加历史、选择分支、重建上下文和写入文件 |
| ResourceLoader / ModelRegistry | 当前资源、工具来源、模型配置与请求鉴权 | 准备输入和每次请求需要的配置 |

同一条消息可以同时有内存对象和持久 entry。`Agent` 在 `message_end` 时先更新消息状态，`AgentSession` 再处理 extension、监听通知和 session append；这条顺序使工具处理能使用已完成的 assistant 消息。[S: S-019]

## 配置怎样进入下一轮

`setActiveToolsByName()` 根据 registry 更新 active tools，并重建基础 system prompt。`AgentSession` 安装的 `prepareNextTurn` 在 turn 边界读取当前 system prompt、tools、model 和 thinking level，返回下一次请求使用的 context/config。

因此要查“工具变了以后模型什么时候看到”，需要同时追踪 registry 更新和下一轮快照刷新。动态工具测试验证了注册表、active set 和 prompt 的更新；完整的请求中途配置差分仍是单独的检查项。[S: S-023; X: X-005]

## 低层结束后为什么还会继续

`_runAgentPrompt()` 先把产品运行标记设为 active，再调用 `agent.prompt()`。之后循环调用 `_handlePostAgentRun()`；后者返回 true 时，再调用 `agent.continue()`。[S: S-002]

`_handlePostAgentRun()` 取出最后一条 assistant 响应，按源码顺序处理：

1. 检查普通可重试错误，并在重试次数允许时准备退避和 continuation。
2. 对已经尝试重试但仍失败的响应发出相应结束通知，重置重试计数。
3. 检查压缩条件；错误 overflow 的恢复与已完成响应的压缩具有不同的续跑规则。
4. 检查低层结束事件处理期间新进入的队列，有输入时继续运行。

详细实现位于 [agent-session.ts](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/agent-session.ts#L1023)。压缩条件见[上下文与压缩](04-context-memory-compaction.md)，消息排序见[核心循环](03-core-loop.md)。

## 自动重试由代码规则触发

`AgentSession` 的普通自动重试由错误分类和配置规则决定。低层运行结束后，`_handlePostAgentRun()` 读取最后的 assistant message，调用 `_isRetryableError()`；这里的 `stopReason`、`errorMessage` 可以是适配层封装的请求失败状态，不意味着模型已经判断应该重试。[S: S-002, S-010, S-031]

```text
低层运行结束
  → 读取最后一条 assistant message
  → 上下文溢出交给压缩分支
  → 检查 stopReason=error 且有 errorMessage
  → 排除配额/账单限制，匹配可重试错误文本
  → 检查 retry.enabled 和 maxRetries
  → 等待可取消的退避时间
  → Agent.continue() 重新请求模型
```

错误分类函数使用正则表达式匹配错误文本，不会再请求一个 LLM 判断是否值得重试。配额限制的排除规则先于临时错误匹配，因此错误中即使含有 `429`，也不一定重试。[S: S-031]

| 错误信息或状态 | 规则的处理 |
|---|---|
| overloaded、rate limit、部分 5xx 等临时服务错误 | 可进入普通自动重试，再受开关和次数约束 |
| connection lost、fetch failed、timeout 等传输错误 | 可进入同一重试路径 |
| insufficient_quota、billing、部分订阅额度限制 | 从普通自动重试中排除 |
| context overflow | 由 `_checkCompaction()` 处理，沿压缩恢复规则决定后续动作 |
| 普通回答没有完成任务或内容有误 | 不触发这个错误分类器的重试；它不评价答案质量 |

默认配置开启重试，`maxRetries=3`、`baseDelayMs=2000`。连续失败时，等待时间按 `baseDelayMs × 2^(attempt−1)` 计算，即 2、4、8 秒。收到非 error 的 assistant 消息时，产品层重置重试计数；这不是整条长任务一生只能重试三次的总预算。[S: S-010, S-019, S-032]

例如 Pi 请求 LLM 服务时返回 `503 Service Unavailable`，规则判定可重试，首次等待 2 秒。准备重试时，末尾失败响应从 live context 移除，但保留在 session 历史中，再由 `Agent.continue()` 重新发起请求。等待也可被取消。[S: S-010]

```text
同一次用户请求
├─ 第一次低层运行：LLM API 请求报可重试错误
│  → turn_end → agent_end
├─ AgentSession：检查规则，等待，再调用 continue
├─ 第二次低层运行：模型调用工具并给出回答
│  → agent_end
└─ 没有其他后续工作 → agent_settled
```

这是基于源码的重试示意，不是对历史 read 轨迹补造一次失败。用户没有重新提交请求，但同一次产品运行可以出现多次 `agent_end`，最后才 `agent_settled`。

## Bash 联网失败和模型 API 失败分别怎么处理

在未取消整体运行、也没有 extension 覆盖行为的默认 bash 工具路径中，命令自身的网络错误先成为工具结果。`AgentSession` 的自动重试分类器检查的则是最后一条 assistant 消息的错误状态。[S: S-010, S-031, S-034]

假设用户要求“下载这个文件，再分析内容”，模型提出：

```bash
curl --fail --max-time 5 https://example.com/data.json
```

若 curl 下载超时，以非零退出码结束，bash handler 会抛出包含输出和退出状态的异常。低层工具执行器捕获它，构造 `isError: true` 的 `toolResult`，把结果加入后续模型请求。接下来由模型决定换一种方式、报告失败，或提出一个新的等待后重试命令，例如：

```bash
sleep 10 && curl --fail --max-time 5 https://example.com/data.json
```

这里的等待和再次下载是模型提出的新工具调用，既不保证一定发生，也不使用产品层默认的 2/4/8 秒退避。上面的命令是教学示例，未在本轮实际运行。[S: S-018, S-034]

| 失败或重试发生在哪里 | Pi 看到的状态 | 谁决定后续动作 |
|---|---|---|
| curl、npm 等命令内部自行重试 | bash 调用仍在运行，最终结果尚未返回 | 命令自己的配置和实现 |
| bash 中的命令结束并返回网络错误 | 错误 toolResult 被交给模型 | LLM 决定下一次工具调用或回答 |
| Pi 请求 LLM 服务失败 | assistant 消息带 stopReason: "error" 和 errorMessage | AgentSession 按错误规则、次数与退避配置重试模型请求 |

所以，工具输出即使出现 `503` 或 `network error`，也不会仅凭这段文字触发产品层自动重试。分类器的输入必须先是相应的 assistant 错误消息。[S: S-031]

两层失败也可能连续发生：

```text
curl 下载失败
  → Pi 得到错误 toolResult
  → Pi 请求模型，让它决定下一步
  → 这次 LLM API 请求又失败
  → AgentSession 按规则重试 LLM API 请求
  → 模型恢复响应，决定是否再调用 bash
```

`Agent.continue()` 重试的是从现有上下文继续请求模型，不会直接重放上一批已执行的 shell 命令，也不回滚文件或从头执行整个用户任务。模型若随后再次要求执行同一命令，那是一次新的模型决策。

定位：[bash 非零退出处理](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/tools/bash.ts#L398)、[工具异常包装](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/agent/src/agent-loop.ts#L669)、[产品层运行后检查](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/agent-session.ts#L1038)。

## 自动重发与模型重新尝试工具的区别

| 情况 | 谁决定下一步 | 处在哪条路径 |
|---|---|---|
| 模型请求因网络或临时服务错误失败后重发 | Harness 的错误匹配、次数和退避规则 | AgentSession 产品层自动重试 |
| 测试命令失败，模型读到 toolResult 后改代码再运行 | LLM 根据上下文生成新的工具调用 | 正常模型—工具循环 |
| 上下文越界后生成摘要并继续 | 产品层选择压缩与续跑分支；模型承担摘要生成 | 压缩恢复路径 |

Provider SDK/适配器内部还可能有自己的请求重试配置。它与这里低层运行结束后的产品层重试是两层控制，不能简单把 `maxRetries=3` 当作全部 HTTP 尝试的上限。[S: S-024, S-032]

源码定位：[错误文本分类](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/ai/src/utils/retry.ts#L96)、[产品层重试准备](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/agent-session.ts#L2587)、[默认设置](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/settings-manager.ts#L813)。

## 最后怎样收尾

`_runAgentPrompt()` 的 finally 清除本次 system prompt override、处理 pending Bash messages，再调用 `_emitAgentSettled()`。后者更新产品运行标记，通知 extension 和订阅者，并处理 idle 等待者。[S: S-002, S-019]

由此可以区分低层 `agent_end` 和产品层 `agent_settled`：前者到来后，重试、压缩或队列仍可能延长这次产品运行。自动化调用方需要按所需边界等待，并另外检查最终响应和任务产物。[X: X-005, X-008]

## 从外部解读回到状态所有权

把扩展理解成“可以改工作流”，落实到代码后仍要回答：数据由谁持有、何时重建、哪些内容进入模型。当前路径中，Agent 管消息与队列，SessionManager 管历史记录，AgentSession 组织两者与 extensions 的生命周期。新增的工具输出分流与 reload 核查分别见 C-027、C-028；外部文章的用途解释和版本边界见[来源对照](17-external-perspectives.md)。
"""

REPORTS['11-runtime-experiments.md'] = r"""# 实验记录

本报告保留两批证据：2026 年 7 月的真实 SiFlow 场景和首次定向测试，以及 2026-10-20 的源码复核与本地 mock/faux 检查。本次没有调用外部模型。

## 历史真实模型场景

| 场景 | 实际观察 | 记录 |
|---|---|---|
| R-001 文本 | 一轮 assistant，无工具，最终 settled | [normalized trace](../traces/normalized/R-001-text-only.normalized.jsonl) |
| R-002 read | 两轮模型处理，一次 read，最终返回合成值 314159 | [normalized trace](../traces/normalized/R-002-read-tool.normalized.jsonl) |
| R-003 创建会话 | 记录合成 token 并写入 session | [normalized trace](../traces/normalized/R-003-session-create.normalized.jsonl) |
| R-004 恢复会话 | 独立新进程在未重发 token 时返回 PI_RESUME_2718 | [normalized trace](../traces/normalized/R-004-session-resume.normalized.jsonl) |

另有 R-005 的模型发现记录，以及当前路径的旧 X-001/X-003 的 39、31 项定向测试。原命令与环境摘要保存在 [runtime-tests.md](../runtime-tests.md)。这些数字属于历史执行，不合并成此次新测试的通过数。

## 本次定向检查

下表直接对应保存的 Vitest 结果。通过、失败和跳过分别列出；只用执行通过的具体断言支持行为结论。

| 检查 | 通过 | 失败 | 跳过 | 内容与产物 |
|---|---:|---:|---:|---|
| X-004 | 39 | 0 | 0 | [Agent 与低层 loop](../traces/checks/20261020/X-004.vitest.json) |
| X-005 | 12 | 0 | 5 | [产品事件、动态工具、重试、压缩后队列](../traces/checks/20261020/X-005.vitest.json) |
| X-006 | 46 | 1 | 0 | [session context/tree 与首次 CLI 尝试](../traces/checks/20261020/X-006.vitest.json) |
| X-008 | 15 | 0 | 0 | [faux compaction 与发送前压缩](../traces/checks/20261020-followup/X-008.vitest.json) |
| X-009 | 5 | 0 | 16 | [setSessionFile 名称筛选](../traces/checks/20261020-followup/X-009.vitest.json) |
| X-010 | 1 | 0 | 0 | [CLI + tsx 对照](../traces/checks/20261020-cli/X-010.vitest.json) |

核心循环组重新验证 loop、工具排序、hook 和队列。产品层组检查异步 `message_end` 的记录顺序、动态工具、重试和压缩后队列。持久化组检查 context projection 与分支树。补充组检查当前产品压缩条件、非法文件处理与 CLI 错误呈现。

## 一次失败怎样定位

X-006 中的 46 项进程内检查通过，CLI 用例在子进程解析模块时退出，尚未进入被测的 session 文件校验路径。该测试直接以 Node 启动 `cli.ts`，临时运行环境最初没有配上 Pi 开发入口使用的 tsx/tsconfig 加载方式。

X-009 先单独验证 `SessionManager.setSessionFile`：空文件初始化、非法非空文件拒绝与内容保留均通过。X-010 再给 CLI 用例补上 tsx 加载环境，验证友好错误和原文件不变，结果通过。原 X-006 记录保持失败状态，后续成功记录没有覆盖它。

## 跳过项与运行边界

X-005 的五项真实模型 compaction e2e 因没有凭据而跳过，不能算作压缩验证；相应 controller 行为使用 X-008 的 faux 测试补充。X-009 通过名称筛选只运行五项文件校验用例，其余十六项未选用。

当前范围选用 118 个 passed、1 个 failed、21 个 skipped 的测试条目，其中 CLI 的同一断言先失败后单独通过。这里统计的是当前路径的执行记录。范围外的历史测试仍保存在原始结果与 [runtime-tests.md](../runtime-tests.md)，不计入本表。摘要信息保存在各批次的 `summary.json`，执行脚本见[复现方法](13-coverage-reproducibility.md)。
"""

REPORTS['12-failure-modes-open-questions.md'] = r"""# 失败处理与待验证路径

Pi 的失败处理分布在工具、低层循环、产品编排和 session 存储四处。先定位失败发生在哪一层，再判断后续状态和事件。[S: S-001, S-008, S-010, S-018, S-021]

| 触发条件 | 当前处理 | 证据 |
|---|---|---|
| 未知工具、参数非法或 hook block | 返回错误 toolResult；相应 handler 不执行 | S-018，X-004 |
| assistant 以 length 截断且含工具调用 | 所有调用返回截断错误，模型可重新提出完整调用 | S-018，X-004 |
| bash 中命令联网失败并以非零退出结束 | 包装为错误 toolResult，由模型决定下一步 | S-018，S-034 |
| 普通可重试 provider 错误 | AgentSession 有界退避，错误保留在历史但从 live context 移除 | S-010，X-005 |
| 当前模型 context overflow | 按 stop reason 决定压缩后是否恢复；错误恢复有一次限制 | S-021，X-008 |
| 压缩过程中出现排队消息 | 压缩完成后可继续消费队列 | S-021，X-005 |
| 非空文件不是有效 session | 拒绝打开并保留文件内容 | S-020，X-009/X-010 |
| 取消运行 | 沿 AbortSignal 和各 backend 的取消逻辑处理，最终进入相应收尾 | S-001、S-007、S-015；具体 backend 的动态覆盖不同 |

普通 tool error 会回到模型，模型可以据此改变下一次工具调用；provider error 的普通自动重试由 `AgentSession` 的代码规则触发。错误分类与默认退避见[自动重试机制](10-implementation-details.md#自动重试由代码规则触发)，命令内部重试、工具失败和模型服务失败的区别见[三层重试示例](10-implementation-details.md#bash-联网失败和模型-api-失败分别怎么处理)。自动重试也不表示已经执行的外部动作可以安全重复，尤其是请求超时前副作用已经发生的情况。

## 当前还缺哪些行为证据

当前 `AgentSession` 的运行中配置刷新尚缺完整 request diff。可以在 tool hook 或事件监听者中更新 tools/model，分别记录当前请求和下一请求，检查变更在什么边界生效。

真实长上下文压缩的摘要质量没有测量。当前 tests 验证触发条件、状态更新和续跑，不衡量重要约束是否在真实摘要中丢失。

会话文件校验与分支重建已经执行；进程被 SIGKILL、半写入记录、损坏 parent 链和 workspace 漂移仍需要独立故障实验。解析器跳过坏行也可能留下不完整的逻辑历史。

Subagent 示例的取消和文件竞争、orchestrator 重启、容器或 VM 的文件与网络隔离仍是静态路径。应分别观察 child 退出、残留进程、文件变化和实际隔离边界。

这些是后续检查队列。先完成当前机制理解，再按需要选择具体实验或开展设计比较。
"""

REPORTS['13-coverage-reproducibility.md'] = r"""# 覆盖与复现

报告的结论由固定源码、历史 trace 和本次测试记录支持。当前 HIR 含 28 个 nodes、34 条 edges；正文采用 28 条 claims 和 65 条 evidence records，其余历史记录标记为范围外。计数用于核对产物，不表示代码覆盖率。

## 从哪里查证

| 产物 | 用途 |
|---|---|
| [manifest](../manifest.json) 与 [analysis brief](../analysis-brief.json) | 固定版本、历史/本次执行范围和待解释问题 |
| [claims](../evidence/claims.jsonl) 与 [observations](../evidence/observations.jsonl) | 结论、依据、条件和反例检查 |
| [coverage](../evidence/coverage.json) | 14 个模块的具体检查范围与剩余未知项 |
| [外部来源目录](../evidence/external-sources.json) | 16 篇页面的作者、版本、阅读状态与采用方式 |
| [模型输入来源](../evidence/model-input-sources.json) | 外部模板和编码器的查阅范围；未执行模型或抓取云端 prompt |
| [HIR](../hir.json) | 组件、关系和证据标记 |
| [scenario catalog](../scenarios/catalog.json) | 历史和新增检查的配置、结果与 artifact |
| [20261020](../traces/checks/20261020/summary.json)、[followup](../traces/checks/20261020-followup/summary.json)、[CLI](../traces/checks/20261020-cli/summary.json) | 本次逐组命令、时间、通过/失败记录 |

## 本次覆盖的机制

主线从 CLI/SDK session 构建到 AgentSession、Agent、低层循环、模型与工具边界，再到会话记录。新增阅读集中在 compat 分派、事件等待、工具 preflight、next-turn 刷新、压缩条件和首次文件写入。Subagent、orchestrator 与外部隔离作为静态旁支记录。

动态覆盖采用本地 mock/faux/controller 测试；原来的真实 JSON-mode 文本、read、resume 证据保留。TUI/RPC 的完整交互、真实长上下文、OS 崩溃、并发 child 文件竞争和容器/VM backend 不在本次运行覆盖内。

## 复现定向测试

需要固定 commit 的 Pi checkout、它的依赖和 Node 22.19.0。脚本检查 commit，将源码导出到临时目录，使用已安装依赖，关闭测试缓存并使用独立 agent 配置；不会安装包或调用外部模型。

```bash
python3 pi-harness-analysis/reproduce/run_mechanism_checks.py   --repo /path/to/pi   --node /path/to/node   --output /tmp/pi-mechanism-results   --group X-004 --group X-008 --group X-009 --group X-010
```

`--output` 必须为空，以免覆盖既有记录。`--group X-005` 可复现产品层组及其五个 e2e 跳过项；`--group X-006` 保留原未加载 tsx 的诊断配置，CLI 子项可能在模块解析时失败。X-010 是相应的加载器对照组。各组具体文件清单在脚本和 summary 中。

Node 官方归档 URL 与 SHA-256 保存在[运行时来源](../traces/checks/node-runtime-provenance.json)。依赖 lockfile hash 在每批 summary 中；这些记录不包含模型凭据。

## 重建分析产物与报告

```bash
python3 pi-harness-analysis/reproduce/compile_analysis.py
python3 pi-harness-analysis/reproduce/compile_report.py
python3 /path/to/harness-analysis-skill/scripts/render_diagrams.py pi-harness-analysis
python3 /path/to/harness-analysis-skill/scripts/validate_analysis.py pi-harness-analysis --strict
python3 /path/to/harness-analysis-skill/scripts/audit_outputs.py pi-harness-analysis --strict
```

`compile_analysis.py` 先构建历史记录，再应用本次源码复核及已保存测试结果；它不会重新运行实验。`compile_report.py` 写入此次维护的正文，并从当前 claims/evidence 生成索引。当前正文使用 6 张经复核的插图；图片、提示词、生成参数与审核状态见[插图记录](../diagrams/generated/README.md)。图片与机制说明使用同一组证据。
"""

REPORTS['16-glossary.md'] = r"""# 术语表

| 术语 | 在本版本中的含义 |
|---|---|
| Harness | 组织模型请求、工具执行、上下文、状态和运行控制的系统 |
| AgentSessionRuntime | 当前产品的 session 与 cwd 相关服务管理层，负责切换、清理和重建 |
| AgentSession | Coding Agent 的 prompt、extension、重试、压缩和收尾编排 |
| Agent | 低层 loop 的状态包装，拥有消息、队列、tools/model 和取消信号 |
| turn | 低层循环中的一轮 assistant 响应及工具处理；用户请求可包含多个 turn |
| agent_end | 一次低层运行的结束事件，产品层还可能继续处理 |
| agent_settled | 当前 Coding Agent 完成该次运行收尾；任务成功需要另行判定 |
| registry | 已注册的工具定义，可能包含默认未启用的工具 |
| active tools | 当前 Agent 中启用并用于模型请求的工具集合 |
| toolCall / toolUse | toolCall 是消息内容块，toolUse 是可能的 assistant stop reason |
| toolResult | 与工具调用关联的结果消息，可携带错误并进入下一请求 |
| steering | 由提交方式或 API 显式选择，在当前 turn 边界后注入；默认运行中 Enter 选择此队列 |
| follow-up | 由提交方式或 API 显式选择，在工具与 steering 耗尽时消费；默认运行中 Alt+Enter 选择此队列 |
| nextTurn | 产品层留给下一次普通 prompt 附带的消息 |
| context | 当前请求使用的 system、messages、tools；不等于整个 session 文件 |
| 持久历史 | 已保存的会话记录，可以包含多个分支、摘要、配置与扩展数据 |
| 当前分支 | 从当前 leaf 沿 parentId 选出的历史路径 |
| 请求视图 | 本轮实际使用的信息，经分支选择、压缩边界和消息转换后与 system/tools 组装 |
| AgentMessage | Pi 应用层消息；除普通模型消息外，还可包含 custom、bashExecution 和摘要类型 |
| CustomEntry / CustomMessageEntry | 前者保存默认不入模型的扩展状态；后者会重建为 custom 应用消息并参与消息转换 |
| bashExecution | 用户通过 ! 执行命令的内部记录；不同于模型调用 bash 后得到的 toolResult |
| convertToLlm | 普通 TypeScript 转换函数：将应用消息映射为 pi-ai Message[]，再由 provider 适配器构造实际 API 请求 |
| chat template / 对话编码器 | 将结构化消息和工具定义组织为模型对应的输入格式；此处讨论服务端职责，具体实现因模型而异 |
| tokenizer | 将文本和控制标记转换为 token IDs；与 Pi 的应用消息类型转换是不同阶段 |
| tool-call parser | 将模型生成的调用格式解析为 API 工具调用字段，之后由 Harness 执行工具 |
| ModelRegistry | 当前产品的模型配置与请求鉴权注册表 |
| compat | pi-ai 兼容入口，按条件连接内置 Models 或 API registry |
| Models | pi-ai 的 provider/model 集合接口，当前 compat 的内置模型分支会使用它 |
| leaf / parentId | 会话树的当前位置与父记录引用，决定当前分支 |
| compaction boundary | 带摘要和 firstKeptEntryId 的历史选择边界 |
| project trust | 项目启动资源加载的信任决策，职责不同于执行 sandbox |
| R / X evidence | R 表示真实模型运行；X 表示控制实验或定向测试 |

具体条件和调用顺序在对应章节展开，查证入口见[源码与结论索引](14-source-claim-index.md)。
"""

REPORTS['quality-comparison-2604.14228.md'] = r"""# 历史报告组织记录

首轮分析曾参照架构研究的组织方式，补充设计空间、术语表、结构化证据和多层图示。本次调整以 Pi 的实际运行路径和实现细节为主，相关背景不作为当前行为的证据。

当前阅读入口是[Pi Agent Harness 分析报告](index.md)。先从一次 read 请求理解对象和消息流，再检查工具排序、压缩、模型接口和 session 文件。设计取舍与跨产品比较留作后续专题。

旧版生成图片、提示词和审核元数据保存在 [diagrams/generated](../diagrams/generated/README.md)，用于追溯历史产物。当前模型接口的说明以 S-024、修正后的 HIR 和正文为准；首次写入、压缩分支和事件顺序以本次新增证据为准。
"""

REPORTS['claim-index.md'] = r"""# 结论索引

完整的结论、源码和实验链接见[源码与结论索引](14-source-claim-index.md)。机器可读版本见 [claims.jsonl](../evidence/claims.jsonl)。
"""

REPORTS['17-external-perspectives.md'] = r"""# 外部解读与当前源码的对照

本轮从作者文章、使用者记录、源码分析和产品评测中筛选了 16 篇页面。15 篇阅读了相关正文，1 篇只能读取元数据与搜索摘要。实现仍固定在 `v0.80.7 / 818d674` 的当前 AgentSession 路径；完整来源信息见 [external-sources.json](../evidence/external-sources.json)。

## 吸收的阅读角度

“极简”可以帮助确定检查顺序：看模型请求中实际有什么，再看是谁决定加入这些内容。作者的上下文控制动机已放入[上下文章节](04-context-memory-compaction.md)，与 system prompt、active tools、context hook 和会话分支的具体入口对应。这里没有把短 prompt 写成普遍的性能优势。

扩展的作用需要沿着持久状态、reload 和工具 registry 一起看。使用者写出一段扩展后，怎样继续修改并恢复状态，比“能注册一个函数”更能解释接口的用途。[工具与扩展章节](05-models-tools-extensions.md)补充了工具结果的两个消费方和资源重建顺序。

树状会话适合解释临时探索后回到主线的过程。配合 `branchWithSummary()`，可以选择带回哪些对话信息；文件副作用则沿真实工作区保留。这一工作流已融入[会话章节](08-sessions-persistence-recovery.md)。

队列和事件也有使用者层面的含义。steering 与 follow-up 给出不同的输入消费时机；事件完成与任务验收则是两种观测结果。这些解释分别放入[循环](03-core-loop.md)和[可观测性](09-observability.md)，并继续保留源码条件。

## 哪些说法需要修正或限定

| 外部表述 | 对照固定版本后的处理 |
|---|---|
| 部分文章概括为只有四个内置工具 | 当前定义有七个名称，默认 active set 为 read/bash/edit/write。原作者也提到可选只读工具。按 registry 与 active set 分开描述。 |
| 把最近约 20000 token 与 reserve 混称 | `reserveTokens=16384` 用于触发阈值；`keepRecentTokens=20000` 用于保留片段估算，见 S-028/S-029。 |
| 将 follow-up 说成等待整个 run settled 后才开始 | 当前低层 loop 在发出 agent_end 前先检查 follow-up，产品 settled 更晚，见 S-001/S-019。 |
| 将 SYSTEM.md 说成改系统提示的唯一入口 | 当前 `before_agent_start` 也能提供 system prompt，SDK 还有配置路径。按具体入口解释，见 S-002/S-004。 |
| 使用 agent/pre-step、agent/request 等 hook 名称 | 本报告核对的接口名是 context、before_agent_start、before_provider_request 等；未把社区层或其他版本名称套到当前类型。 |
| 较新分析使用 prepareRequest、context_edit 等机制 | 这些文章标注的是其他版本；只保留其阅读视角，具体功能不回填到本版本。 |
| 由个人成本案例、产品评分或标题推断“极简总是更好” | 未采纳这类普遍结论。原作者的 MCP/CLI 实验也有不同任务与评测对象，不能当作本报告的 Pi 测量。 |

四工具概括可见 [PiLot](https://www.pivscode.com/blog/pi-minimal-extensible-coding-agent/) 与 [Holbreich](https://alexander.holbreich.org/posts/2026/pi-coding-agent/)；预算用语见 [Haochuan](https://blog.haochuanz.net/posts/agent-harness-04-pi)；follow-up 表述见 [Shilin](https://edward40.com/p/pi-agent-internal/)；提示与 hook 名称见 [Walking Labs](https://walkinglabs.github.io/learn-harness-engineering/zh/harness-designs/pi/)；较新版本例子见 [Rememorio](https://rememorio.github.io/blog/agent-framework/en/pi-agent-harness/)。它们提供待核对的解释，表中的实现判断来自固定源码。

## 来源与采用范围

| 来源 | 日期或版本 | 本报告如何使用 |
|---|---|---|
| [B-01 · Mario Zechner：作者的 Pi 设计回顾](https://mariozechner.at/posts/2025-11-30-pi-coding-agent/) | 2025-11-30；早期实现，未固定本报告 commit | 控制上下文、检查交互；工具内容与显示数据分工。 |
| [B-02 · Armin Ronacher：Pi 与可定制工作流](https://lucumr.pocoo.org/2026/1/31/pi/) | 2026-01-31；早期使用体验，未固定 commit | 扩展状态、热重载和树状会话支持迭代工作流。 |
| [B-03 · Mario Zechner：浏览器脚本与按需说明](https://mariozechner.at/posts/2025-11-02-what-if-you-dont-need-mcp/) | 2025-11-02；浏览器工具案例；非 v0.80.7 实验 | 通过按需读取说明和脚本组合提供额外能力。 |
| [B-04 · Mario Zechner：MCP / CLI 终端工具实验](https://mariozechner.at/posts/2025-08-15-mcp-vs-cli/) | 2025-08-15；Claude Code 与终端工具比较；不是 Pi 评测 | 原实验没有给出 CLI 对 MCP 的普遍胜负结论。 |
| [B-05 · Haochuan：双队列、会话树与边界](https://blog.haochuanz.net/posts/agent-harness-04-pi) | 2026-08-25；文章声明 8fa7eebd2353；与 818d674 不同 | 双队列对应两种输入时机；压缩预算术语需修正。 |
| [B-06 · Shilin：内部机制导读](https://edward40.com/p/pi-agent-internal/) | 2026-07-21；发布日期接近，但源码链接未固定本报告 commit | 应用消息与 provider 格式分离；据此追查数据转换。 |
| [B-07 · Rememorio：v1.0.0 源码导读](https://rememorio.github.io/blog/agent-framework/en/pi-agent-harness/) | 日期未明示；明确固定 v1.0.0 / a13d35a742c6ef8462812a28fbe1d8c8b7431c32 | 可参考存储历史、分支、请求三种视图的阅读方式。 |
| [B-08 · Walking Labs：中文 Harness 设计拆解](https://walkinglabs.github.io/learn-harness-engineering/zh/harness-designs/pi/) | 日期未明示；未固定版本，混合主项目与社区扩展 | 扩展可编程性是有用视角；接口名须逐项核查。 |
| [B-09 · Kahtaf Alam：领域 Agent 构建记录](https://kahtaf.com/blog/lessons-from-building-a-domain-agent/) | 2026-06-22；OpenCandle 的应用层经验，非本报告实验 | 按职责和轨迹定位失败，并单独评价产物。 |
| [B-10 · Scott Spence：my-pi 构建与观测](https://scottspence.com/posts/building-my-pi-claude-code-alternative-with-pi) | 2026-04-26；持续更新的 my-pi 派生配置，未固定 Pi commit | telemetry 区分运行故障与已完成但答错的结果。 |
| [B-11 · Julian Prokay：pic 任务管理扩展](https://jprokay.com/post/018-pi-coding-agent) | 2026-02-15；自建 pic CLI / task extension | 任务状态由 CLI/SQLite 管理，extension 负责交互。 |
| [B-12 · Alexander Holbreich：定制工具的投入](https://alexander.holbreich.org/posts/2026/pi-coding-agent/) | 2026-06-03；未固定版本，含当时产品与价格比较 | 定制能力伴随维护工作流的投入。 |
| [B-13 · DeepakNess：日常配置与使用](https://deepakness.com/blog/pi-agent-setup) | 2026-05-29；页面标注更新 2026-08-14；个人配置含扩展 | 日常使用涉及模型选择、队列和定制界面。 |
| [B-14 · DevOpsTales：v0.84.2 产品评测](https://devopstales.github.io/ai/pi-coding-agent-review/) | 2026-09-07；声明对齐 v0.84.2；晚于目标版本 | 阅读其上手与治理讨论，机制仍核对本地版本。 |
| [B-15 · PiLot Studio：PiLot 产品方解读](https://www.pivscode.com/blog/pi-minimal-extensible-coding-agent/) | 2026-09-23；VS Code 产品方文章，主要转述作者论点 | 可作生态入口；默认工具数与 registry 数需区分。 |
| [B-16 · Matteo Chieppa：工具栈入门指南](https://www.matteochieppa.com/en/blog/pi-coding-agent-complete-guide) | 2026-04-05；搜索摘要声明 2026-04-27 / v0.70.2；正文读取受客户端渲染限制 | 检索用于发现工具/资源分层线索，未据此新增机制结论。 |

作者原文提供其当时的设计目的，使用者文章提供具体工作方式，代码解读提供追查线索。转述同一原文的多篇文章不构成多份独立验证。后续版本的文章只用于识别版本边界，本报告没有据此扩大到新版实现或新增性能结论。
"""

REPORTS['reading-guide.md'] = r"""# 专题阅读与查证索引

[Pi Agent Harness 分析报告](index.md)是可以连续阅读的主文。下面的资料用于追查具体机制，不要求按文件编号逐篇读完。

## 从一个操作追到代码

- [一次请求的运行过程](00-task-walkthrough.md)：历史 read 场景及其事件路径。
- [入口、对象与生命周期](02-interfaces-lifecycle.md)：对象关系，turn 与三个结束事件的例子。
- [核心循环与工具执行](03-core-loop.md)：参数准备、并发排序、队列与错误回填。
- [AgentSession 的状态与运行收尾](10-implementation-details.md)：配置刷新、代码规则触发的重试、退避与最终收尾。

## 理解消息、状态与扩展

- [上下文、消息转换与压缩](04-context-memory-compaction.md)：持久历史、当前分支、请求视图，custom/Bash/摘要的转换例子，以及压缩切点、长任务分段和压缩期间的输入队列。
- [从 Pi 的请求到模型输入](18-model-input-encoding.md)：API 字段、对话模板与 token，以及 Qwen3.8-27B / DeepSeek V4 Flash 的工具格式对照。
- [模型接口、工具与扩展](05-models-tools-extensions.md)：模型分派、工具 registry、content/details 与 reload。
- [会话、持久化与恢复](08-sessions-persistence-recovery.md)：首次写入、分支、fork 和重新打开文件。

## 查看执行边界和旁支

- [项目信任、执行权限与工作区](06-permissions-sandbox-workspace.md)：trust、hook 与部署隔离分别控制什么。
- [子代理与多进程编排](07-subagents-delegation.md)：扩展示例及实验性实例管理的旁支资料。
- [事件与可观测性](09-observability.md)：事件说明了什么，以及任务验收还需要什么。

## 查证范围和依据

- [范围与方法](01-scope-method.md)：固定版本、证据分类和分析范围。
- [实验记录](11-runtime-experiments.md)、[失败与待验证路径](12-failure-modes-open-questions.md)、[覆盖与复现](13-coverage-reproducibility.md)。
- [源码与结论索引](14-source-claim-index.md)、[术语表](16-glossary.md)、[外部解读与源码对照](17-external-perspectives.md)。

这些资料保留详细参数、源码编号和实验状态，供需要深入核对时使用。
"""

RUNTIME_TESTS = r"""# Runtime Test Record

Pinned target: `v0.80.7` / `818d67457cdd6b60bce6b121d16b23141c252dd8`.

## Setup

- Official Node `v22.19.0` portable archive was SHA-256 verified and extracted under `/tmp`.
- `npm ci --ignore-scripts` installed 351 packages; audit reported 0 vulnerabilities.
- Warning: optional `@earendil-works/gondolin@0.12.0` declares Node `>=23.6.0`; Gondolin was not run.
- Isolated HOME and synthetic workspace were used. No API key was stored.

## Model Discovery

Command shape:

```bash
HOME=/tmp/pi-analysis-runtime/home ./pi-test.sh   --list-models siflow --no-extensions --no-skills   --no-prompt-templates --no-context-files
```

Result:

```text
provider  model           context  max-out  thinking  images
siflow    qwen3.6-35ba3b  262.1K   16.4K    no        no
```

## Real Model Scenarios

Common arguments: `--provider siflow --model qwen3.6-35ba3b --mode json --no-extensions --no-skills --no-prompt-templates --no-context-files --no-approve`.

| Scenario | Additional controls | Exit | Event summary | Final |
|---|---|---:|---|---|
| R-001 | `--no-session --no-tools` | 0 | 1 turn, 0 tool, settled | `PI_TEXT_OK` |
| R-002 | `--no-session --tools read` | 0 | 2 turns, read start/end, settled | `314159` |
| R-003 | persistent `analysis-resume-001`, no tools | 0 | JSONL created | `ACK` |
| R-004 | reopen same session in new process | 0 | prior messages restored | `PI_RESUME_2718` |

## Controlled Tests

```text
agent-core loop + Agent:              2 files, 39 passed, 954ms
new AgentHarness/session/compaction:  3 files, 61 passed, 1.26s
Coding Agent compaction/retry/session:3 files, 31 passed, 2.76s
```

Exact test files are recorded in `evidence/observations.jsonl` (`X-001` through `X-003`).

## Trace Handling

Raw traces contain only synthetic prompts/files but may include model thinking. Normalized traces intentionally omit prompt text, assistant text/thinking, tool arguments and tool results. The report and HIR cite normalized traces.


## 2026-10-20 mechanism recheck

This is a new local mock/faux run on the same pinned commit. The real-provider
records above remain historical; no external model was called in this recheck.

Node 22.19.0 was downloaded from nodejs.org and its archive SHA-256 checked
against the official SHASUMS256. See traces/checks/node-runtime-provenance.json.
The runner exports pinned sources into a temporary directory, links existing
dependencies, disables Vitest caching, and passes a restricted environment with
no model credentials. It does not provide OS-level network isolation.

Detailed commands and per-test results:

- traces/checks/20261020/summary.json (X-004 through X-007)
- traces/checks/20261020-followup/summary.json (X-008 and X-009)
- traces/checks/20261020-cli/summary.json (X-010)

The saved results contain 179 passed, 1 failed and 21 skipped entries. The
initial CLI test in X-006 failed before the target behavior due to module
loading. X-010 supplied the development tsx/tsconfig loader and passed that
assertion; X-006 is preserved unchanged. X-005 skipped five real-model e2e
tests without credentials; X-009 selected five file-validation tests and left
sixteen tests outside its name filter.

Runner: reproduce/run_mechanism_checks.py. Use --group to select a group and a
new empty --output directory to preserve prior attempts.
"""

REPORTS['18-model-input-encoding.md'] = r"""# 从 Pi 的请求到模型真正收到的输入

Pi 已经选好历史、放入压缩摘要，也准备好了 system prompt 和工具定义。它们怎样一起交给模型？这一步跨过了 Harness 与模型服务的边界：Pi 组织 API 请求，服务端再按模型的对话格式编码，模型最终处理 token 序列。[C: C-030]

这里沿用“检查 Docker 配置”的例子。Pi 部分仍固定在 `v0.80.7 / 818d674`；模型侧对照的是 2026-10-21 查阅的 Qwen3.8-27B 官方模板和 DeepSeek V4 Flash 公开参考编码器。下文是源码串讲与简化示例，没有执行这两个模型，也没有抓取云端实际 prompt。外部 main 文件的版本边界与来源见[查阅记录](../evidence/model-input-sources.json)。

## 三份字段怎样变成一条模型输入

在 Pi 的统一接口层，请求 context 分别携带 `systemPrompt`、`messages` 和 `tools`。低层循环先处理消息转换，再把它们一起交给模型调用入口。之后还需要两次不同的转换：[S: S-001, S-037; D: D-013]

```mermaid
flowchart TD
  A["Pi：systemPrompt、messages、tools"] --> B["Pi provider 适配器：API 请求字段"]
  B --> C["模型服务：对话模板或专用编码器"]
  C --> D["带角色边界和工具说明的序列"]
  D --> E["Tokenizer：token IDs"]
  E --> F["模型计算与生成"]
  F --> G["服务端解析：回答、推理内容、工具调用"]
  G --> H["Pi：展示回答或执行工具"]
```

对纯文本聊天，模板负责把角色和内容排成模型训练时使用的格式，tokenizer 再把它转成 token IDs。模型使用这些输入及已经生成的内容，继续预测后续 token。图中的边界表示职责；具体部署可能将多个阶段封装在同一个服务中。[对话模板](https://huggingface.co/docs/transformers/main/en/chat_templating)、[文本生成](https://huggingface.co/docs/transformers/main/en/llm_tutorial)

## Pi 发出去的仍然是结构化请求

选择 OpenAI 兼容 Chat Completions 接口时，下面是一份简化的请求体。模型名称是占位符，摘要和工具说明是教学内容，省略鉴权、采样和思考参数。

```json
{
  "model": "MODEL_NAME",
  "messages": [
    {
      "role": "system",
      "content": "你是代码助手。先检查文件，再回答问题。"
    },
    {
      "role": "user",
      "content": "历史摘要：正在排查启动端口，已确认生产环境 PORT=8080。"
    },
    {
      "role": "user",
      "content": "请继续检查 Docker 配置。"
    }
  ],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "read",
        "description": "读取指定文件的内容",
        "parameters": {
          "type": "object",
          "properties": {"path": {"type": "string"}},
          "required": ["path"]
        }
      }
    }
  ]
}
```

Pi 的 `openai-completions` 适配器将独立的 `systemPrompt` 放进 system 或 developer 消息，具体角色取决于模型和兼容配置；这里采用 system。工具的名称、描述和参数 schema 则进入独立的 `tools` 字段，工具执行函数不在其中。这是已检查的一个适配实现，实际入口还要看 [compat 的分派条件](05-models-tools-extensions.md#当前模型请求怎样分派)。[S: S-037]

源码：[Context 组装](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/agent/src/agent-loop.ts#L287)、[system 消息转换](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/ai/src/api/openai-completions.ts#L878)、[工具定义转换](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/ai/src/api/openai-completions.ts#L1101)。

## 同一份内容进入 Qwen3.8-27B

查阅的官方模板在启用工具时，先写入可选思考强度指令、工具定义与调用格式要求，再接应用提供的 system 文本。下面保留主要边界，方括号表示省略内容；末尾采用开启思考的生成前缀。[S: S-038]

```text
<|im_start|>system
〔可选的 reasoning effort 指令〕
# Tools
〔工具使用说明〕
<tools>
〔read 工具的 JSON schema〕
</tools>
〔工具调用格式要求〕

你是代码助手。先检查文件，再回答问题。
<|im_end|>
<|im_start|>user
历史摘要：正在排查启动端口，已确认生产环境 PORT=8080。
<|im_end|>
<|im_start|>user
请继续检查 Docker 配置。
<|im_end|>
<|im_start|>assistant
<think>
```

API 中单独传输的 tools，在这里已经进入 system 段。模型若选择读文件，生成的调用片段可以采用以下格式，再由服务端解析成结构化 `tool_calls`：

```text
<tool_call>
<function=read>
<parameter=path>
Dockerfile
</parameter>
</function>
</tool_call>
```

工具执行后，API 里的 tool 消息由此模板包装为 user 段中的 `<tool_response>`。因此，API 返回的调用 JSON 与模型原始生成文本、API 消息角色与最终序列标记，分别属于不同表示。[Qwen3.8-27B 官方模板](https://huggingface.co/Qwen/Qwen3.8-27B/blob/main/chat_template.jinja)

## 同一份内容进入 DeepSeek V4 Flash

公开参考编码器采用另一套标记。普通 system 消息先写正文，再附工具说明；下例同样开启思考，未加入 max effort 的额外前缀。[S: S-039]

```text
<｜begin▁of▁sentence｜>
你是代码助手。先检查文件，再回答问题。

## Tools
〔DSML 调用格式说明〕
### Available Tool Schemas
〔read 的函数定义与参数 schema〕

<｜User｜>历史摘要：正在排查启动端口，已确认生产环境 PORT=8080。
<｜User｜>请继续检查 Docker 配置。
<｜Assistant｜><think>
```

该编码器内部把 tools 放在 system 消息上参与渲染；这是参考函数的输入结构，不能直接照搬为 HTTP 请求体。它生成和解析的工具调用使用 DSML，例如：

```text
<｜DSML｜tool_calls>
<｜DSML｜invoke name="read">
<｜DSML｜parameter name="path" string="true">Dockerfile</｜DSML｜parameter>
</｜DSML｜invoke>
</｜DSML｜tool_calls>
```

工具结果经过预处理，变成 user 内容中的 `<tool_result>` 块。公开实现提供了从消息到序列、再从生成文本到结构化结果的两向转换。[参考编码器](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash/blob/main/encoding/encoding_dsv4.py)、[格式说明](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash/blob/main/encoding/README.md)

两种示例最容易混淆的位置，可以放在一起对照：

| 位置 | Qwen3.8-27B 查阅模板 | DeepSeek V4 Flash 查阅编码器 |
|---|---|---|
| 角色边界 | im_start / im_end | User / Assistant 等专用标记 |
| 工具定义 | 本例中位于 system 段内、应用 system 文本之前 | 本例中附在 system 文本之后 |
| 工具调用 | tool_call、function、parameter | DSML tool_calls、invoke、parameter |
| 工具结果 | user 段中的 tool_response | user 内容中的 tool_result |

这些位置由具体模板决定。相同 API 字段可以被服务端编码成不同序列；同一模型也可能因模板版本、思考设置或服务端覆盖而改变输入格式。上述对照不覆盖整个 Qwen3.8 系列，也不等于确认了任一家云端的完整内部处理。

## 文件还是由 Pi 来读取

模型根据输入生成工具调用后，服务端解析调用并返回给 Pi。Pi 才查找 `read` 的执行函数、检查参数并读取工作区文件，然后把结果加入消息列表，发起下一次模型请求。下一次输入包含先前对话、刚才的调用和文件结果，模型据此继续分析。[S: S-001] [DeepSeek 工具调用示例](https://api-docs.deepseek.com/guides/tool_calls/)也展示了调用方执行工具、再把结果交回模型的流程。

`<think>` 等标记表达生成格式，实际推理来自模型计算。工具定义告诉模型可请求什么动作及其参数，执行动作的代码仍由 Harness 持有。

这也接回了前面的压缩：压缩主要改变 Pi 选给模型的 messages。旧历史被摘要代表之后，仍通过同一套 API 适配、对话编码和分词流程进入模型。模型模板通常只看到一条带摘要说明的普通消息；[摘要、近期消息和新输入如何排列](04-context-memory-compaction.md#压缩后的消息列表长什么样)，由更早的会话重建步骤决定。
"""


def build_claim_index():
    claims = [json.loads(line) for line in (ROOT/'evidence/claims.jsonl').read_text().splitlines() if line]
    evidence = {item['id']: item for item in (json.loads(line) for line in (ROOT/'evidence/observations.jsonl').read_text().splitlines() if line)}
    lines = ['# 源码与结论索引', '', '结论沿用历史编号，仅列当前 AgentSession 路径采用的记录。完整条件和反例检查保存在 [claims.jsonl](../evidence/claims.jsonl)。', '']
    for claim in claims:
        if claim.get('conditions', {}).get('report_scope') == 'historical_only':
            continue
        lines.extend([f"## {claim['id']}", '', claim['statement'], ''])
        for eid in claim['evidence_ids']:
            item = evidence[eid]
            src = item['source']
            path = src.get('path', '')
            if item['kind'] in ['D', 'S'] and path:
                url = SOURCE + path + (f"#L{src['start_line']}" if src.get('start_line') else '')
            else:
                url = '../' + path if path else '../evidence/observations.jsonl'
            lines.append(f"- [{eid}]({url})：{item['summary']}")
        lines.extend(['', f"范围：{claim['scope']}。状态：{claim['status']}；置信度：{claim['confidence']}。", ''])
    return '\n'.join(lines)


def main():
    REPORT.mkdir(exist_ok=True)
    REPORTS['14-source-claim-index.md'] = build_claim_index()
    for name, content in REPORTS.items():
        (REPORT / name).write_text(content.strip() + "\n")
    (ROOT / 'runtime-tests.md').write_text(RUNTIME_TESTS.strip() + "\n")

if __name__ == '__main__':
    main()
