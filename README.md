# HandoffSeal MVP

HandoffSeal 是一个本地运行的“交付包跨文件对账门”：把客户即将收到的 ZIP/文件夹和 JSON 规则交给它，检查客户、周期、版本、必需文件，以及明细表和期望表之间的 ID 集合、汇总控制数是否一致，再生成可复核的 HTML/JSON 证据。

它不是新的通用数据质量平台。单表校验已经有免费的 [Open Data Editor](https://github.com/okfn/opendataeditor)、Frictionless 和 CSVLint；HandoffSeal 只补一个更窄的动作：把多份文件当成一个“交付批次”验收。它不判断业务数据是否合理，也不接数据库或自动修改原文件。

## 当前范围

- 目录或 ZIP 输入；
- JSON 规则文件；
- 必需文件和文件名身份标记检查；
- CSV 列检查、空主键、重复主键；
- XLSX 工作表、列和重复主键检查；
- `key_set_equal`：检查两张表的 ID 集合是否互相一致；
- `row_count_matches`：检查明细实际行数是否等于汇总表中的控制数；
- 发现公式时标记 `REVIEW`，不重算公式；
- 输出 `evidence.json` 和 `report.html`；
- ZIP 路径安全检查，不上传任何内容。

明确不做：数据库/API、PDF OCR、公式语义、业务合理性判断、自动修复、定时任务、账号系统、通用数据质量平台和复杂业务规则编排。

## 运行

```bash
python3 handoff_seal.py \
  --manifest manifest.demo.json \
  --package demo-pass.zip \
  --output evidence-pass
```

## 一键启动（Day 0）

macOS 试用者可以先双击 `run.command`，或在终端运行：

```bash
chmod +x run.command
./run.command
```

上面的默认命令只跑本地 demo。真实批次使用同一个启动层：

```bash
./run.command client-manifest.json client-delivery.zip evidence-client-001
```

它只调用本机已有的 `python3`，不内嵌运行时、不上传文件、不改原文件。

规则文件的最小形式：

```json
{
  "package": {
    "customer": "ACME",
    "period": "2026-08",
    "version": "v1",
    "filename_tokens": ["ACME", "2026-08", "v1"]
  },
  "files": [
    {
      "path": "ACME_2026-08_v1_summary.csv",
      "kind": "csv",
      "required_columns": ["metric", "value"],
      "unique_key": "metric"
    },
    {
      "path": "ACME_2026-08_v1_detail.csv",
      "kind": "csv",
      "required_columns": ["record_id", "amount"],
      "unique_key": "record_id"
    },
    {
      "path": "ACME_2026-08_v1_expected.csv",
      "kind": "csv",
      "required_columns": ["record_id", "label"],
      "unique_key": "record_id"
    }
  ],
  "cross_checks": [
    {
      "type": "key_set_equal",
      "left": {"path": "ACME_2026-08_v1_detail.csv", "key": "record_id"},
      "right": {"path": "ACME_2026-08_v1_expected.csv", "key": "record_id"}
    },
    {
      "type": "row_count_matches",
      "data_path": "ACME_2026-08_v1_detail.csv",
      "expected": {
        "path": "ACME_2026-08_v1_summary.csv",
        "match_column": "metric",
        "match_value": "detail_rows",
        "value_column": "value"
      }
    }
  ]
}
```

## 本地演示

```bash
python3 build_demo.py
python3 handoff_seal.py --manifest manifest.demo.json --package demo-pass.zip --output evidence-pass
python3 handoff_seal.py --manifest manifest.demo.json --package demo-fail.zip --output evidence-fail
```

`demo-pass` 应为 PASS；`demo-fail` 会同时报告重复主键、跨文件 ID 不一致、汇总控制数不一致，并把未列入规则的旧文件标为 REVIEW。报告可以直接用浏览器打开。

## 免费试点

免费试点不收费、不注册、不上传文件。目标是经常把多份 CSV/XLSX 打包交付给客户或下游系统的小型报表、运营和外包交付团队。用户只需为自己的真实批次写一次 manifest，然后在下一批交付前运行：

```bash
python3 handoff_seal.py \
  --manifest client-manifest.json \
  --package client-delivery.zip \
  --output evidence-2026-08
```

试点按 7 天分阶段：先定向触达 3–5 个高度匹配对象；首批可以陪跑以确认价值；第二批只允许查看说明和问答，必须由用户基本独立运行。达到 2 个真实试点后停止扩招；若不足，再在 7 天窗口内继续定向触达，记录约 8–10 次有效交流，不把这些数字当统计结论。

试点是否成立只看真实采用：至少 2 个陌生用户各自运行过 2 个真实批次，第二批基本独立，其中至少 1 次发现被用户确认本来会造成返工、退回或解释成本，并且至少 1 人愿意继续下一批。下载、点赞、demo 通过和首批陪跑都不算独立采用。详细记录见 [PILOT.md](PILOT.md) 和 [PILOT_LOG_TEMPLATE.md](PILOT_LOG_TEMPLATE.md)。

若用户只需要 Open Data Editor 的单表校验、没有跨文件错误、没有重复批次，或首次运行后不再使用，就停止，不继续堆功能。

当前目录的 `demo-*.zip` 只是本地回归样例，不代表已有外部用户或付费客户。
