# HandoffSeal 决策记录

日期：2026-08-20

## 结论

否决“再做一个通用 CSV/XLSX 校验器”。保留 HandoffSeal，但把它收窄成一个本地交付包跨文件对账门：检查 ZIP/文件夹中的客户、周期、版本、必需文件、跨表 ID 集合和汇总控制数，并输出可复核的 HTML/JSON 证据。

它不是通用数据质量平台，也不是业务正确性审计器。免费试点可以直接开始；在陌生用户重复运行前，不把它称为可赚钱产品。

## 模型复核与事实否决

本轮 GPT 侧复核否决了旧范围：既然 Open Data Editor、Frictionless 和 CSVLint 已经能免费完成大部分单表检查，就不应再包装一个同类工具。它接受的窄切口是“一个批次里的多份文件能否互相对上”：客户/周期/版本、必需文件、明细与期望表的 ID 集合、明细行数与汇总控制数。

在初始评估阶段，DeepSeek 本机免费代理无法调用，运行日志显示账号池无可用账号，因此当时没有把未完成的 DeepSeek 意见冒充成当前结论。随后通过 Chrome 中已登录的 ChatGPT 与 DeepSeek Chat 分别进行独立提案、交叉反驳和最终共识复核；仍需外部免费试点验证。

当前最小范围是：

- 规则明确列出必需文件；
- 文件名检查客户、周期、版本标记；
- CSV/XLSX 检查列漂移、空主键和重复主键；
- `key_set_equal` 检查两张表的 ID 集合；
- `row_count_matches` 检查明细行数和汇总控制数；
- 生成 HTML/JSON 证据，定位到文件、工作表和行；
- 不上传、不接数据库/API、不自动修改原文件。

## GitHub 查重结果

在写代码前，用以下精确关键词检查过 GitHub：

`delivery package validator`、`client deliverable validator`、`file package manifest checker`、`cross file consistency checker`、`data delivery validation`、`report package checker`、`file completeness checker manifest`。

本轮没有找到与“交付批次跨文件对账 + 本地证据包”完全相同的仓库；这是“尚未发现直接同款”，不是市场需求证明。相邻项目已经足够强：

- [Open Data Editor](https://github.com/okfn/opendataeditor) 已覆盖本地 CSV/XLSX 的列、类型、必填、唯一键、主外键和错误导出；
- [Frictionless](https://github.com/frictionlessdata/frictionless-py)、[Great Expectations](https://github.com/great-expectations/great_expectations) 和 [CSVLint](https://github.com/BdR76/CSVLint) 已覆盖大量单表质量检查；
- 一个直接命名为 client-data-delivery-validator 的新仓库仍明确自称小型练习项目，当前没有 stars/forks，说明“泛化包装”本身没有显著采用迹象。

另一方面，公开用户讨论明确描述了供应商/客户 Excel/CSV 的列变化、坏日期、重复行、缺失主键，以及上传后才发现错误导致反复重传的问题：[messy Excel/CSV imports](https://www.reddit.com/r/dataengineering/comments/1pojhd1/how_to_deal_with_messy_excelcsv_imports_from/)、[data validation before upload](https://www.reddit.com/r/dataengineering/comments/xs0ca3/data_validation_between_user_input_and_effective_upload_to_datalake/)。这证明痛点存在，但不证明用户会采用 HandoffSeal。

之前的 FormGuard 已冻结，因为 GitHub 上已有 [FormZiller](https://github.com/malashd1/formziller) 等相近实现，商业市场也已有浏览器合成监控产品。

## 免费试点判定

不收费、不注册、不上传；只让陌生用户用自己的真实批次。试点成立的门槛是至少 2 个陌生用户各自运行 2 个真实批次，并确认至少 1 个发现确实避免了返工、退回或解释成本。下载、点赞、demo 通过都不算。

如果用户只需要 Open Data Editor、没有跨文件问题、无法获得重复批次，或首次使用后不再运行，就停止，不继续堆功能。只有通过这个门槛，才值得做模板库、拖拽 UI 或团队协作。

## 2026-08-20 GPT × DeepSeek Chrome Chat 共识

两边均返回 `STATUS: AGREE`。共识不是“继续开发”，而是立即执行一次 7 天真实免费试点：

- Day 0 只做极薄启动层：`run.command`、默认目录和短说明；不做拖拽 UI、正式安装器、内嵌 Python、新校验规则、PDF/Excel 导出或复杂业务语义。
- 先定向触达 3–5 个高度匹配对象；若已得到 2 个真实试点就停止扩招，否则在 7 天窗口内继续定向触达，约记录 8–10 次有效交流。这些是研究预算，不是统计结论。
- 首批可以陪跑，用来确认增量价值；第二批只允许文档和问答，必须由用户基本独立运行，陪跑不计入独立采用。
- 通过条件是至少 2 个陌生用户各自完成 2 个真实批次、第二批基本独立、至少 1 个发现确实避免返工/退回/解释成本，并且至少 1 人愿意继续下一批。
- 如果没有增量价值、没有真实批次或没有重复使用意愿，冻结项目，不再堆功能；如果只卡在一个明确的启动阻力，只修该阻力后重跑。

这次模型共识只解决“下一步怎么验证”，不构成外部用户采用、付费意愿或市场规模证据；当前还没有擅自发送任何招募信息。
