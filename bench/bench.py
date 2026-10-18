import json
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
from tasks import TASKS  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ENV = dict(
    os.environ,
    KUBECONFIG=os.path.expanduser("~/.kube/config-home"),
    PATH=os.path.expanduser("~/.local/bin") + ":" + os.environ.get("PATH", ""),
)
MODELS = ["lfm2.5:8b", "granite4.1:8b"]
SAMPLES = int(os.environ.get("SAMPLES", "2"))
RUN_TIMEOUT = 480
ANSI = re.compile(r"\x1b\[[0-9;?]*[a-zA-Z]")


def kube(*args, stdin=None, timeout=60):
    return subprocess.run(
        ["kubectl", "-n", "llm", *args], input=stdin, capture_output=True,
        text=True, env=ENV, timeout=timeout,
    )


def ask(model, prompt):
    t0 = time.time()
    try:
        p = kube("exec", "-i", "deploy/ollama", "--", "ollama", "run", "--nowordwrap", "--hidethinking", model,
                 stdin=prompt, timeout=RUN_TIMEOUT)
        out = ANSI.sub("", p.stdout).replace("\r", "")
        return out, time.time() - t0, p.returncode
    except subprocess.TimeoutExpired:
        return "", time.time() - t0, -1


def extract_code(text, marker):
    """思考部分を除いた最後のコードブロックのうち、marker を含むものを返す。"""
    if "</think>" in text:
        text = text.rsplit("</think>", 1)[1]
    if "...done thinking." in text:
        text = text.rsplit("...done thinking.", 1)[1]
    blocks = re.findall(r"```[a-zA-Z0-9_+-]*\n(.*?)```", text, re.S)
    cands = [b for b in blocks if marker in b]
    code = cands[-1] if cands else None
    if code is None:
        return None
    # 新しい型ヒント構文 (Python 3.8 で未対応) による不当な失敗を避ける
    code = "\n".join(ln for ln in code.splitlines()
                     if ln.strip() != "from __future__ import annotations")
    return "from __future__ import annotations\n" + code + "\n"


def main():
    results = []
    out_json = os.path.join(HERE, "results.json")
    for model in MODELS:
        for other in MODELS:
            if other != model:
                kube("exec", "deploy/ollama", "--", "ollama", "stop", other)
        for task in TASKS:
            for s in range(SAMPLES):
                raw, sec, rc = ask(model, task["prompt"])
                code = extract_code(raw, task["marker"])
                if code is None:
                    passed, total, detail = 0, 1, "コードブロックが見つからない"
                else:
                    passed, total, detail = task["check"](code)
                rec = dict(model=model, task=task["name"], sample=s + 1, passed=passed,
                           total=total, detail=detail, seconds=round(sec, 1), chars=len(raw))
                results.append(rec)
                with open(os.path.join(HERE, f"raw_{model.replace(':', '_')}_{task['name'][0]}_{s+1}.txt"),
                          "w", encoding="utf-8") as f:
                    f.write(raw)
                with open(out_json, "w", encoding="utf-8") as f:
                    json.dump(results, f, ensure_ascii=False, indent=1)
                print(f"{model:15} {task['name']:12} #{s+1} {passed}/{total} {sec:6.1f}s {detail}", flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
