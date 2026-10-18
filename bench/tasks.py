"""モデル比較用の課題と自動採点。

各課題は prompt (モデルに渡す文面) と check(code) -> (passed:int, total:int, detail:str)
を持つ。生成コードは一時ディレクトリで別プロセスとして実行し、タイムアウトを設ける。
"""
import os
import random
import subprocess
import sys
import tempfile
import textwrap

TIMEOUT = 20


def run_py(files, entry, timeout=TIMEOUT):
    """files を一時ディレクトリに書き、entry (python ソース) を実行して (rc, stdout+stderr) を返す。"""
    with tempfile.TemporaryDirectory() as d:
        for name, src in files.items():
            with open(os.path.join(d, name), "w", encoding="utf-8") as f:
                f.write(src)
        with open(os.path.join(d, "_entry.py"), "w", encoding="utf-8") as f:
            f.write(entry)
        env = {"PATH": os.environ.get("PATH", ""), "PYTHONDONTWRITEBYTECODE": "1"}
        try:
            p = subprocess.run(
                [sys.executable, "-s", "_entry.py"],
                cwd=d, env=env, capture_output=True, text=True, timeout=timeout,
            )
            return p.returncode, (p.stdout + p.stderr)[-1500:]
        except subprocess.TimeoutExpired:
            return -1, "timeout"


# ---------------------------------------------------------------- 課題1: バグ修正
T1_PROMPT = '''次の Python 関数にはバグがあります。バグを修正した関数全体を、Python のコードブロック 1 つで示してください。説明は 1 行だけにしてください。

仕様: moving_average(values, window) は、長さ window の移動平均のリストを返す。
例: moving_average([1, 2, 3, 4, 5], 2) == [1.5, 2.5, 3.5, 4.5]
window が 0 以下、または len(values) より大きいときは ValueError を送出する。

```python
def moving_average(values, window):
    result = []
    for i in range(len(values) - window):
        result.append(sum(values[i:i + window]) / window)
    return result
```
'''

T1_HARNESS = '''
from solution import moving_average
ok = 0
cases = [
    ([1, 2, 3, 4, 5], 2, [1.5, 2.5, 3.5, 4.5]),
    ([1, 2, 3], 3, [2.0]),
    ([1, 2, 3], 1, [1.0, 2.0, 3.0]),
    ([10, 20, 30, 40], 4, [25.0]),
    ([1, 2, 3, 4], 3, [2.0, 3.0]),
]
errors = [([1, 2], 3), ([1, 2], 0), ([1, 2], -1), ([], 1)]
total = len(cases) + len(errors)
for v, w, exp in cases:
    try:
        r = moving_average(v, w)
        if len(r) == len(exp) and all(abs(a - b) < 1e-9 for a, b in zip(r, exp)):
            ok += 1
    except Exception:
        pass
for v, w in errors:
    try:
        moving_average(v, w)
    except ValueError:
        ok += 1
    except Exception:
        pass
print("RESULT", ok, total)
'''


# ---------------------------------------------------------------- 課題2: 仕様から実装
T2_PROMPT = '''次の仕様を満たす Python 関数 parse_duration(s: str) -> int を実装してください。コードブロック 1 つで、標準ライブラリのみを使い、説明は 1 行だけにしてください。

仕様:
- "1h30m15s" のような文字列を、合計秒数 (int) に変換する。
- 使える単位は d (日=86400秒)、h (時間=3600秒)、m (分=60秒)、s (秒=1秒)。
- 単位は d, h, m, s の順に並べる。省略は可。同じ単位を 2 回使うこと、順序が逆になることは不可。
- 数値は 0 以上の整数 (数字の並び) のみ。単位の前に必ず数値が必要。
- 上記を満たさない文字列 (空文字、単位なしの数値、未知の単位、空白を含む、負数、小数など) は ValueError を送出する。

例: parse_duration("1h30m") == 5400, parse_duration("45s") == 45, parse_duration("1d2h3m4s") == 93784
'''

T2_HARNESS = '''
from solution import parse_duration
ok = 0
good = {"1h30m": 5400, "45s": 45, "2d": 172800, "1d2h3m4s": 93784, "0s": 0,
        "10m5s": 605, "1d1s": 86401, "120m": 7200}
bad = ["", "90", "1x", "m", "1h1h", "30m1h", "1 h", "-5s", "1.5h", "h30", "1h30", "s", "1h 30m", "1H"]
total = len(good) + len(bad)
for s, exp in good.items():
    try:
        if parse_duration(s) == exp:
            ok += 1
    except Exception:
        pass
for s in bad:
    try:
        parse_duration(s)
    except ValueError:
        ok += 1
    except Exception:
        pass
print("RESULT", ok, total)
'''


# ---------------------------------------------------------------- 課題3: リファクタリング
T3_PROMPT = '''次の Python 関数を、読みやすくリファクタリングしてください。挙動は変えないこと。関数名 f はそのままにし、型ヒントを付けてください。リファクタリング後の関数全体を、Python のコードブロック 1 つで示し、説明は 1 行だけにしてください。

```python
def f(l):
    r = []
    for i in range(len(l)):
        if l[i] % 2 == 0:
            if l[i] > 10:
                r.append(l[i] * 2)
            else:
                r.append(l[i])
        else:
            if l[i] > 10:
                r.append(l[i] * 3)
            else:
                pass
    return r
```
'''

T3_HARNESS = '''
import random
from solution import f

def orig(l):
    r = []
    for i in range(len(l)):
        if l[i] % 2 == 0:
            if l[i] > 10:
                r.append(l[i] * 2)
            else:
                r.append(l[i])
        else:
            if l[i] > 10:
                r.append(l[i] * 3)
            else:
                pass
    return r

random.seed(1)
cases = [[], [0], [11], [12], [10], [-4, -3, 13, 14], [1, 2, 3]]
for _ in range(293):
    cases.append([random.randint(-30, 40) for _ in range(random.randint(0, 12))])
ok = 0
for c in cases:
    before = list(c)
    try:
        r = f(c)
        if r == orig(before) and c == before and isinstance(r, list):
            ok += 1
    except Exception:
        pass
print("RESULT", ok, len(cases))
'''


# ---------------------------------------------------------------- 課題4: テスト生成
T4_PROMPT = '''次の Python 関数のテストを書いてください。pytest は使わず、assert 文のみを使った `test_` で始まる関数をいくつか書いてください。関数は `from solution import is_leap_year` で読み込みます。テストコード全体を Python のコードブロック 1 つで示し、説明は 1 行だけにしてください。バグのある実装を見つけられるよう、境界値を十分に含めてください。

```python
def is_leap_year(year: int) -> bool:
    """グレゴリオ暦のうるう年かどうかを返す。"""
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
```
'''

T4_SOLUTIONS = {
    "correct": "def is_leap_year(year):\n    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)\n",
    "no_400_rule": "def is_leap_year(year):\n    return year % 4 == 0 and year % 100 != 0\n",
    "no_100_rule": "def is_leap_year(year):\n    return year % 4 == 0\n",
    "wrong_200": "def is_leap_year(year):\n    return year % 4 == 0 and (year % 100 != 0 or year % 200 == 0)\n",
}

T4_RUNNER = '''
import traceback, tests_gen
fails = 0
names = [n for n in dir(tests_gen) if n.startswith("test_") and callable(getattr(tests_gen, n))]
for n in names:
    try:
        getattr(tests_gen, n)()
    except BaseException:
        fails += 1
print("RESULT", len(names), fails)
'''


def check_t4(code):
    detail = []
    killed = 0
    correct_ok = False
    n_tests = 0
    for name, sol in T4_SOLUTIONS.items():
        rc, out = run_py({"solution.py": sol, "tests_gen.py": code}, T4_RUNNER)
        res = [ln for ln in out.splitlines() if ln.startswith("RESULT")]
        if rc != 0 or not res:
            if name == "correct":
                detail.append("正解実装で実行エラー: " + out.strip().splitlines()[-1][:100] if out.strip() else "正解実装で実行エラー")
            continue
        _, n, fails = res[-1].split()
        n, fails = int(n), int(fails)
        if name == "correct":
            n_tests = n
            correct_ok = (fails == 0 and n > 0)
            detail.append(f"正解:{'通過' if correct_ok else f'{fails}件失敗'}(テスト{n}件)")
        else:
            if fails > 0:
                killed += 1
    detail.append(f"変異検出:{killed}/3")
    # 正解で通り、かつ変異を検出できた数を得点にする (正解で落ちたら 0)
    score = killed if correct_ok else 0
    return score, 3, " / ".join(detail)


def make_checker(harness, filename="solution.py"):
    def check(code):
        rc, out = run_py({filename: code}, harness)
        res = [ln for ln in out.splitlines() if ln.startswith("RESULT")]
        if rc != 0 or not res:
            tail = out.strip().splitlines()[-1][:120] if out.strip() else f"rc={rc}"
            return 0, 1, "実行エラー: " + tail
        _, ok, total = res[-1].split()
        return int(ok), int(total), ""
    return check


TASKS = [
    {"name": "1 バグ修正", "prompt": T1_PROMPT, "check": make_checker(T1_HARNESS), "marker": "def moving_average"},
    {"name": "2 仕様から実装", "prompt": T2_PROMPT, "check": make_checker(T2_HARNESS), "marker": "def parse_duration"},
    {"name": "3 リファクタ", "prompt": T3_PROMPT, "check": make_checker(T3_HARNESS), "marker": "def f"},
    {"name": "4 テスト生成", "prompt": T4_PROMPT, "check": check_t4, "marker": "def test_"},
]
