"""採点の自己検証: 正解コードで満点、バグ入りコードで減点になるかを確認する。"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from tasks import TASKS  # noqa: E402

PRE = "from __future__ import annotations\n"
T = {t["name"][0]: t for t in TASKS}

REF = {
    "1": ("def moving_average(values, window):\n    if window <= 0 or window > len(values):\n        raise ValueError\n"
          "    return [sum(values[i:i+window]) / window for i in range(len(values) - window + 1)]\n",
          "def moving_average(values, window):\n    result = []\n    for i in range(len(values) - window):\n"
          "        result.append(sum(values[i:i + window]) / window)\n    return result\n"),
    "2": ("import re\ndef parse_duration(s):\n    m = re.fullmatch(r'(?:(\\d+)d)?(?:(\\d+)h)?(?:(\\d+)m)?(?:(\\d+)s)?', s)\n"
          "    if not s or not m:\n        raise ValueError\n    d, h, mi, se = (int(x) if x else 0 for x in m.groups())\n"
          "    return d*86400 + h*3600 + mi*60 + se\n",
          "def parse_duration(s):\n    return int(s)\n"),
    "3": ("def f(l: list[int]) -> list[int]:\n    out = []\n    for n in l:\n        if n % 2 == 0:\n"
          "            out.append(n * 2 if n > 10 else n)\n        elif n > 10:\n            out.append(n * 3)\n    return out\n",
          "def f(l):\n    return [x for x in l if x > 10]\n"),
    "4": ("def test_a():\n    assert is_leap_year(2000)\n    assert not is_leap_year(1900)\n    assert not is_leap_year(1800)\n"
          "    assert is_leap_year(2024)\n    assert not is_leap_year(2023)\n".replace("is_leap_year", "solution.is_leap_year")
          .replace("def test_a", "import solution\ndef test_a", 1),
          "import solution\ndef test_a():\n    assert solution.is_leap_year(2024)\n"),
}

for k, (good, bad) in REF.items():
    t = T[k]
    print(k, t["name"], "正解 ->", t["check"](PRE + good))
    print(k, t["name"], "不十分 ->", t["check"](PRE + bad))
