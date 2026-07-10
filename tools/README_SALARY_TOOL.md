# Salary Benchmark Tool（上游遗留 · 非国内主路径）

> **国内用户请先读这句**：本工具**不是**开箱即用的国内薪资产品。  
> 实现已迁至 `integrations/legacy/salary_lookup.py`；仓库根 `salary_lookup.py` 仅为兼容 shim。  
> 公司名匹配逻辑面向**丹麦/北欧**后缀与字符（A/S、ApS、øæå）。  
> 国内谈薪方法论（无数据爬取）见 `integrations/catalog/salary-negotiate/`。  
> 国内最小闭环（搜岗 → 简历/话术 → 匹配 → tracker）**不依赖**本工具。

## What is this?

The salary lookup tool lets you benchmark company salaries against a baseline from **your own** data (optional step in the upstream English `/apply` workflow).

**This tool is optional.** If you don't have `salary_data.json`, skip salary lookup entirely.

## How it works

The tool reads a `salary_data.json` file in the **repo root** containing company salary benchmarks. It uses fuzzy matching to find companies by name, handling Danish/Nordic characters, legal suffixes (A/S, ApS), and common spelling variations.

The data format supports any index-based or absolute salary data. For example:
- Index 100 = median salary, higher is better
- Absolute salary values in your currency
- Any custom metric you want to track

## Data format

The tool expects `salary_data.json` with this structure:

```json
{
  "metadata": {
    "source": "My Union Statistics 2025",
    "index_baseline": 100,
    "index_label": "Index",
    "baseline_description": "Index 100 = median salary for private sector"
  },
  "companies": [
    {
      "company": "Novo Nordisk A/S",
      "city": "Bagsværd",
      "categories": {
        "all_employees": { "count": 500, "index": 108.5 },
        "engineering": { "count": 120, "index": 112.3 }
      }
    },
    {
      "company": "Ørsted A/S",
      "city": "Fredericia",
      "categories": {
        "all_employees": { "count": 200, "index": 105.2 }
      }
    }
  ]
}
```

### Fields

- **metadata.source**: Where the data comes from (for reference)
- **metadata.index_baseline**: The baseline value (e.g., 100 for index-based data)
- **metadata.index_label**: Label for the index column in output
- **metadata.baseline_description**: Human-readable explanation of the baseline
- **companies[].company**: Company name (required)
- **companies[].city**: City/location (optional, used for filtering)
- **companies[].categories**: Named salary categories, each with `count` and/or `index`

## Setup options

### Option A: Create salary_data.json manually

Create the file by hand with data from any source: union statistics, Glassdoor, salary surveys, networking, or personal research.

### Option B: Convert from Excel

If you have salary data in an Excel file:

```bash
pip install openpyxl
python3 tools/convert_salary_excel.py path/to/salary-data.xlsx \
  --source "My Salary Data 2025" \
  --baseline 100 \
  --baseline-desc "Index 100 = median salary"
```

On Windows, use `py` if that is how Python is exposed on your PATH. If your system uses `python` instead of `python3`, substitute that in the examples.

The converter auto-detects the Excel layout:
- Looks for a "Company"/"Firma" column and an optional "City"/"By" column
- Treats remaining columns as salary data (auto-pairs count/index columns)

### Option C: Build from research

Start with an empty template and add companies as you research them:

```json
{
  "metadata": {
    "source": "Personal research",
    "index_baseline": 0,
    "index_label": "Monthly salary (DKK)",
    "baseline_description": "Approximate monthly salary before tax"
  },
  "companies": [
    {
      "company": "Example Corp",
      "city": "Copenhagen",
      "categories": {
        "entry_level": { "index": 42000 },
        "senior": { "index": 55000 }
      }
    }
  ]
}
```

## Usage

```bash
# preferred
python3 integrations/legacy/salary_lookup.py "Novo Nordisk"
# root shim (emits a deprecation warning)
python3 salary_lookup.py "Novo Nordisk"
python3 integrations/legacy/salary_lookup.py "Ørsted" --city "Fredericia"
python3 integrations/legacy/salary_lookup.py "COWI" --json
python3 integrations/legacy/salary_lookup.py --list-all
```

## Important notes

- The data file (`salary_data.json`) is **excluded from git** (see `.gitignore`). Your salary data may be proprietary or confidential.
- If the data file is missing, `salary_lookup.py` exits with a helpful error message and the `/apply` workflow skips the salary benchmark step.
- The fuzzy matcher handles Danish company name variations: legal suffixes, Nordic characters, anglicized spellings, and partial matches.
