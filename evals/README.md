# JobPilot 评测数据

E1 评测简历事实拆分，E2 评测 JD 解析。把原文交给待测功能，再将输出与人工标注对照。首批 10 份合成简历中，`resume-001` 至 `resume-005` 用于开发，`resume-006` 至 `resume-010` 留作测试候选。评测口径见 [04 评测方案](../notes/求职助手Agent/04-评测方案.md)。

| 目录 | 内容 |
| --- | --- |
| `datasets/resumes/` | 可直接输入的合成简历文本 |
| `datasets/jds/` | 用于演示标注格式的合成 JD 文本 |
| `datasets/jd-sources.json` | 真实岗位清单，含来源、职级、方向、详略和本地文本校验值 |
| `datasets/annotations/` | 以 `sample_id` 对应输入的人工标注 |
| `private/jds/` | 从公开招聘页复制的真实 JD 原文，仅存本地 |
| `runners/` | 评测运行脚本 |
| `results/` | 本地运行记录，可能包含原文和模型输出，Git 忽略 |
| `reports/` | 评测汇总及可分享的失败案例 |

## E1 简历事实标注

参考 [resume-003.json](datasets/annotations/resume-003.json)。每个 `facts` 条目只描述一个可以核对的事实，用 `source_quote` 保存来自对应简历的原文片段。`kind` 取 `action`（行动）、`technology`（技术）、`result`（结果）或 `role`（角色）。

`responsibility` 取 `lead`（主导）、`own`（负责）、`participate`（参与）或 `na`（不适用）。项目原文没有写明职责程度时，标为 `participate` 并将 `needs_confirmation` 设为 `true`。`has_number` 表示事实包含数量、分数、时长或百分比等数值。

| 简历 | 方向 | 水平 | 关注点 |
| --- | --- | --- | --- |
| [resume-001](datasets/resumes/resume-001.txt) | AI 应用 | 优秀 | 主导范围、离线评测样本数、百分位耗时 |
| [resume-002](datasets/resumes/resume-002.txt) | 后端 | 优秀 | 模块负责范围、并发与延迟的测试条件 |
| [resume-003](datasets/resumes/resume-003.txt) | 前端 | 一般 | 职责不明、技术与行动、用例数量 |
| [resume-004](datasets/resumes/resume-004.txt) | 算法 | 薄弱 | 课程场景、验证集结果 |
| [resume-005](datasets/resumes/resume-005.txt) | AI 应用 | 一般 | 参与程度、人工任务复核、未量化结果 |
| [resume-006](datasets/resumes/resume-006.txt) | AI 应用 | 一般 | 结构化校验、人工边界、同学负责的部分 |
| [resume-007](datasets/resumes/resume-007.txt) | 前端 | 优秀 | 主导交付、可访问性、体积和加载速度的区别 |
| [resume-008](datasets/resumes/resume-008.txt) | 后端 | 薄弱 | 课程作业、局部参与、测试范围 |
| [resume-009](datasets/resumes/resume-009.txt) | 算法 | 一般 | 调参集与验证集、检索与问答指标 |
| [resume-010](datasets/resumes/resume-010.txt) | AI 应用 | 薄弱 | 原文缺失字段、小样本、练习场景 |

## E2 JD 标注

参考 [合成 JD](datasets/jds/jd-example-001.txt)和 [jd-example-001.json](datasets/annotations/jd-example-001.json)。`hard_requirements` 和 `preferred_requirements` 分别填写硬性要求和加分项，按能够单独判断的条目拆分。`keywords` 使用标准技术名，例如将「检索增强生成」记为 `RAG`。`basic_fields` 中原文缺失的值填 `null`，有范围或下限的值保留语义，例如「至少 4 天」。

标注真实 JD 时，从 `private/jds/{sample_id}.txt` 读取原文。对应 JSON 放入 `datasets/annotations/`，`sample_id` 与原文文件名一致，`source_url` 填公开招聘页链接。要求条目用自己的话概括。合成示例用于说明格式，真实 JD 数量单独统计。

## 真实 JD 样本

2026-11-18 从企业官网、企业官方职位板和公开招聘网站收集 118 份 JD，涉及 36 家企业。其中中文 82 份，英文 36 份。样本按岗位链接和正文去重，对同一家公司的近重复描述只留一份。按 [来源清单](datasets/jd-sources.json)的 `sample_id` 可以找到本地原文。提取时去掉了网页界面文字，并整理了空白与分行。

| 职级 | 数量 | 标记依据 |
| --- | ---: | --- |
| 实习 | 76 | 招聘项目或标题明确为实习 |
| 校招或初级 | 13 | 应届招聘项目或初级、New Grad 等标题 |
| 有经验社招 | 16 | 职位要求明确写出相关工作年限 |
| 资深 | 13 | 标题明确为资深或 Senior |

| 方向 | 数量 |
| --- | ---: |
| 后端 | 29 |
| 算法与机器学习 | 26 |
| AI 应用与 Agent | 24 |
| 前端与客户端 | 20 |
| 基础设施 | 8 |
| 数据工程与分析 | 6 |
| 产品与设计 | 3 |
| 硬件 | 1 |
| 质量与测试 | 1 |

详略按正文字数及显式加分项、到岗或时长信号分为详尽 52 份、常规 53 份、简略 13 份，用于抽样对比。清单的 `missing_field_candidates` 记录未匹配到明确线索的薪资、实习到岗和时长字段，人工标注时再复核。样本保留采集时的描述，包含已下线岗位，招聘状态以来源页为准。

百度占 48 份，主要集中在实习组。正式评测准备时，按职级、方向、详略分层，避免同一企业的近似模板分散到开发集和测试集。真实 JD 正文存放在 Git 忽略的 `private/jds/`。提交到仓库的是来源清单、合成样本与标注示例。
