#!/usr/bin/env python3
"""Compatibility shim → integrations/legacy/salary_lookup.py

本文件不是国内求职主路径能力。上游丹麦向薪资查询已迁至
integrations/legacy/salary_lookup.py。请自备 salary_data.json；
国内谈薪见 integrations/catalog/salary-negotiate/。

库导入（测试 / 脚本）仍可：
  from salary_lookup import format_entry
CLI：
  python3 salary_lookup.py "Company"   # 会打印 UserWarning 后转发
"""

from __future__ import annotations

import importlib.util
import sys
import warnings
from pathlib import Path

_LEGACY = Path(__file__).resolve().parent / "integrations" / "legacy" / "salary_lookup.py"


def _load_legacy():
    if not _LEGACY.is_file():
        raise ImportError(f"legacy salary_lookup missing: {_LEGACY}")
    spec = importlib.util.spec_from_file_location(
        "integrations_legacy_salary_lookup", _LEGACY
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {_LEGACY}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_legacy = _load_legacy()

# Re-export public API for tests / importers
load_data = _legacy.load_data
normalize = _legacy.normalize
anglicize = _legacy.anglicize
extract_core_words = _legacy.extract_core_words
match_score = _legacy.match_score
search_company = _legacy.search_company
format_entry = _legacy.format_entry
DATA_FILE = _legacy.DATA_FILE


def main(argv: list[str] | None = None) -> int:
    warnings.warn(
        "salary_lookup.py 为上游/丹麦向遗留入口；实现位于 "
        "integrations/legacy/salary_lookup.py。"
        "国内主闭环不包含薪资库；无 salary_data.json 时请跳过本步骤，"
        "谈薪方法论见 integrations/catalog/salary-negotiate/。",
        UserWarning,
        stacklevel=2,
    )
    old_argv = sys.argv
    try:
        if argv is not None:
            sys.argv = [str(_LEGACY), *argv]
        else:
            sys.argv = [str(_LEGACY), *sys.argv[1:]]
        _legacy.main()
    except SystemExit as exc:
        code = exc.code
        return int(code) if isinstance(code, int) else (0 if code is None else 1)
    finally:
        sys.argv = old_argv
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
