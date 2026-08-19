# HandoffSeal 试点记录模板

这份表只记录采用证据，不记录真实业务文件内容。`candidate_id` 使用匿名编号，不写姓名、公司名、客户名或联系方式。

## 记录规则

- 首批可以陪跑，用来确认真实价值；陪跑不计入独立采用。
- 第二批必须由试用者自己完成，只允许查看说明和问答，不代操作、不代运行。
- 只有真实、重复发生的 CSV/XLSX 多文件交付批次才算有效批次。
- 记录发现是否真的避免了返工、退回或解释成本；demo 通过不算。

## 7 天试点台账

| candidate_id | 高度匹配 | 首次触达 | 回复/拒绝原因 | 首批真实批次 | 首批发现及后果 | 第二批独立完成 | 愿意下一批 | 备注 |
|---|---|---|---|---|---|---|---|---|
| C-001 | 是/否 | YYYY-MM-DD |  | 是/否 |  | 是/否 | 是/否 |  |
| C-002 | 是/否 | YYYY-MM-DD |  | 是/否 |  | 是/否 | 是/否 |  |
| C-003 | 是/否 | YYYY-MM-DD |  | 是/否 |  | 是/否 | 是/否 |  |

### 拒绝原因代码

- `NO_RECURRING_BATCH`：没有重复的多文件交付批次
- `NO_CROSS_FILE_PAIN`：没有跨文件核对或返工痛点
- `TOO_HARD_TO_RUN`：Python/命令行启动阻力过大
- `NO_TIME`：当前没有时间试用
- `PRIVACY`：不能在本机运行或不能提供必要的规则信息
- `NO_REPEAT`：首批有价值，但没有下一批可运行
- `OTHER`：其他原因，补一句简短说明

## 单个试用者记录

```text
candidate_id:
fit_reason: 周期性多文件 CSV/XLSX 交付 + 明确核对/返工成本
first_batch_mode: assisted | independent
first_batch_real: yes | no
finding:
avoided_cost: rework | return | explanation | none
second_batch_mode: independent | assisted | not_run
second_batch_real: yes | no
next_cycle_willing: yes | no | unknown
friction:
refusal_code:
```

## 7 天判定

- **通过**：至少 2 个陌生用户各自完成 2 个真实批次；第二批基本独立；至少 1 个发现被确认会造成真实返工、退回或解释成本；至少 1 人愿意继续下一批。
- **部分通过**：真实价值已经出现，但被一个明确启动阻力卡住；只修这个阻力，再跑一轮，不扩功能。
- **停止**：没有增量价值、没有真实批次、没有重复使用意愿，或用户只需要单表校验。

先定向触达 3–5 个高度匹配对象；达到 2 个真实试点后停止扩招。若不足，在 7 天窗口内继续定向触达，最多记录约 8–10 次有效交流；这些是研究预算，不是统计学结论。
