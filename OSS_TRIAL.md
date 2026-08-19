# 免费开源方案实测

日期：2026-08-20

## 实测环境

所有依赖都装在临时虚拟环境 `/tmp/handoff-oss-venv`，没有修改项目 Python 环境。测试输入是同一组 `demo-pass` 和 `demo-fail` 文件。

## Frictionless

版本：5.19.0。项目：[frictionlessdata/frictionless-py](https://github.com/frictionlessdata/frictionless-py)。

- 直接执行 `frictionless validate demo-pass.zip` 和 `demo-fail.zip` 时，两者都返回 `valid: true`；它把 ZIP 当成普通数据源，只选中了其中一个文件。它没有替 HandoffSeal 完成交付包文件清单和身份检查。
- 用 Frictionless 的 Package API 加入两个资源和字段 schema 后，正常包通过，异常包能以 `unique-error` 定位到 `record_id` 第 3 行。
- 适合做表结构、字段类型、必填、唯一性和数据包资源校验；不负责客户/周期/版本文件名、包内多余文件和交付证据页面。

## Great Expectations

版本：0.18.22。项目：[fivetran/great_expectations](https://github.com/fivetran/great_expectations)。

- 对正常 CSV，列顺序和 `record_id` 唯一性都通过。
- 对异常 CSV，列顺序仍通过，但 `expect_column_values_to_be_unique("record_id")` 返回 `success: false`，列出重复值 `R-001`。
- 适合把检查写成可复用 expectations；同样没有直接提供 ZIP 文件清单、交付包身份、未声明文件和本地 HTML 交付报告这一层。

## Open Data Editor

项目：[okfn/opendataeditor](https://github.com/okfn/opendataeditor)，文档：[上传数据](https://opendataeditor.okfn.org/user-guide/uploading-data)、[错误清单](https://opendataeditor.okfn.org/user-guide/full-list-of-table-errors-detected)。

- 它是免费的本地优先、无代码、跨平台工具，能打开 CSV、Excel 和文件夹，并基于 Frictionless 做表格检查。
- 文档列出的能力已经包括缺失/多余/重复列、缺失单元格、类型、主键、外键、唯一性、必填、枚举、最小/最大值和模式约束，还能导出带错误的数据文件。
- GitHub 最新 macOS DMG release 的下载量约 4,955，Windows 约 641；这只能说明免费工具确实有人下载，不等于交付团队会采用 HandoffSeal。

结论：如果 HandoffSeal 只做单表 schema/类型/唯一性检查，它没有理由存在。HandoffSeal 的 MVP 因此只保留批次级的身份、文件清单、跨文件 ID 集合和控制数检查，作为 Open Data Editor/Frictionless 的补充。

## CSVLint 与直接同类仓库

- [CSVLint](https://github.com/BdR76/CSVLint) 是免费的离线 Notepad++ CSV 校验插件，已有约 239 stars；其历史 release 资产出现过数万次下载，说明“本地、快速、免费校验”确实有使用者，但它聚焦单个 CSV。
- [client-data-delivery-validator](https://github.com/liuyuelintop/client-data-delivery-validator) 是 2026-08 新建的直接命名相近仓库，当前 0 stars/0 forks，README 也明确把它定位为小型练习而非生产系统。它不能证明没人需要这个问题，只能说明泛化的“交付校验器”尚未形成明显采用。

## 公开痛点

[dataengineering 讨论](https://www.reddit.com/r/dataengineering/comments/1pojhd1/how_to_deal_with_messy_excelcsv_imports_from/) 中，用户描述了供应商/客户 Excel/CSV 的表头变化、格式不一致、坏日期、重复行、缺失邮箱和主键等问题；另一篇[上传前验证讨论](https://www.reddit.com/r/dataengineering/comments/xs0ca3/data_validation_between_user_input_and_effective_upload_to_datalake/) 直接讨论了上传后才反馈列、类型、范围、空值和重复问题的流程。

这支持“交付前门禁”值得做免费试点，但不能替代试点本身。试点必须让陌生用户拿自己的真实批次重复运行，且确认发现曾经会造成返工、退回或解释成本。

## 使用迹象

GitHub 与 PyPI 公开指标只是使用代理，不等于付费客户数或真实活跃用户：

- Frictionless：约 838 stars、172 forks；近月 PyPI 下载约 722,579。
- Great Expectations：约 11,720 stars、1,798 forks；近月 PyPI 下载约 26,967,480。
- Pandera：约 4,436 stars、434 forks；近月 PyPI 下载约 9,362,127。[项目](https://github.com/unionai-oss/pandera)
- Soda Core：约 2,413 stars、284 forks；近月 PyPI 下载约 3,549,530。[项目](https://github.com/sodadata/soda-core)

下载量可能包含 CI、镜像和重复安装，因此只能证明生态有人使用，不能证明某个交付包产品有人付费。

## 决策

不继续维护一套重复的数据校验引擎。当前可落地的免费试点是 HandoffSeal 的跨文件层：本地读取 ZIP/文件夹，检查批次身份、必需文件、ID 集合和汇总控制数，生成 HTML/JSON 证据。免费、不注册、不上传；若没有 2 个陌生用户重复使用并确认真实返工价值，就停止。
