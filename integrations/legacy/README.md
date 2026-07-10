# Legacy（上游遗留，非国内主路径）

本目录存放**上游 ai-job-search 遗留能力**，**不**属于国内最小闭环（搜岗 → `/apply-zh` → 匹配 → tracker）。

| 路径 | 说明 |
|------|------|
| `salary_lookup.py` | 薪资基准查询：依赖用户自备 `salary_data.json`；公司名归一化面向丹麦后缀（A/S、ApS）与 Nordic 字符。**无国内薪资数据源。** |

## 国内用户请

1. **不要**把根目录 `salary_lookup.py` 当成开箱可用的国内薪资产品。
2. 谈薪方法论（无爬取）→ [`../catalog/salary-negotiate/`](../catalog/salary-negotiate/)
3. 需要基准数据时：自备 JSON，再调用本目录脚本或根目录 shim。

仓库根 `salary_lookup.py` 仅为兼容转发，会发出 `UserWarning`。
