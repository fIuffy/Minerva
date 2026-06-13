#!/usr/bin/env python3
"""AI-assisted attack harness — human-in-the-loop runner (Protocol §4 RoE).

The model PROPOSES an attack step; the researcher APPROVES (and may edit) before
anything runs against the lab; the harness EXECUTES the approved action against
the self-owned lab only (lab.py enforces the host allowlist) and auto-writes a
per-action record (§8.1). This keeps "the researcher is always the executor;
models advise and generate, they never act autonomously" — no protocol amendment
required.

Examples:
  py runner.py --list
  py runner.py --task sqli_lookup --category B            # local Ollama proposes; you approve
  py runner.py --task rag_prompt_injection --category A --provider gemini
  py runner.py --task sqli_lookup --category C            # manual baseline (no model)
  # non-interactive (pre-authored payload counts as the human decision):
  py runner.py --task sqli_lookup --category B --payload "xyz' UNION ...-- " --yes

Containment (§7): targets only the lab. Pointing it at anything you don't own is
refused in code. Authorized, isolated research use only.
"""
from __future__ import annotations
import argparse
import sys
import datetime as dt
from pathlib import Path
import yaml

# Model output (and our markers) can contain any Unicode; the Windows console
# defaults to cp1252 and would crash on it. Force UTF-8 on the streams.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import backends
import lab
import record

TASKS = yaml.safe_load((Path(__file__).parent / "tasks.yaml").read_text(encoding="utf-8"))

BANNER = (
    "=" * 70 + "\n"
    "  Minerva AI-assisted attack harness — human-in-the-loop\n"
    "  Targets the SELF-OWNED, ISOLATED lab only (§7). You approve every step.\n"
    + "=" * 70
)


def _tty() -> bool:
    return sys.stdin.isatty()


def list_tasks() -> None:
    print("Available tasks:\n")
    for tid, t in TASKS.items():
        print(f"  {tid:24s} {t['technique']}")
        print(f"  {'':24s} {t['name']}  [{t.get('executor')}]\n")


def build_http_action(task: dict, value: str) -> dict:
    method, path = task["method"], task["path"]
    if "{record_id}" in path:
        return {"method": method, "path": path.format(record_id=value)}
    if task.get("upload"):
        return {"method": method, "path": path,
                "files": {"file": ("harness-payload.txt", value, "text/plain")},
                "data": {"title": "harness-upload"}}
    if task.get("inject_param"):
        return {"method": method, "path": path, "params": {task["inject_param"]: value}}
    return {"method": method, "path": path}


def main() -> int:
    ap = argparse.ArgumentParser(description="AI-assisted attack harness (human-in-the-loop)")
    ap.add_argument("--task")
    ap.add_argument("--category", choices=["A", "B", "C"], default="B")
    ap.add_argument("--provider", help="override: ollama | gemini | openai | manual")
    ap.add_argument("--model", help="override model name")
    ap.add_argument("--scenario", default="adhoc")
    ap.add_argument("--payload", help="pre-authored value to inject/send (skips interactive entry)")
    ap.add_argument("--record-id")
    ap.add_argument("--yes", action="store_true", help="auto-approve (only meaningful with --payload)")
    ap.add_argument("--no-model", action="store_true", help="skip the model call (just execute/record)")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    if args.list or not args.task:
        list_tasks()
        return 0
    if args.task not in TASKS:
        print(f"Unknown task '{args.task}'. Use --list.", file=sys.stderr)
        return 2

    print(BANNER)
    task = {"id": args.task, **TASKS[args.task]}
    print(f"\nTask: {task['name']}\nTechnique: {task['technique']}  ({task.get('chain','')})")
    print(f"Target: {task.get('target_desc')}  via {lab.LAB_BASE_URL}\n")

    # 1) Model proposes (A/B). Category C / --no-model: skip.
    prompt = task["prompt_template"].format(base_url=lab.LAB_BASE_URL)
    if args.no_model:
        model = {"category": args.category, "provider": "none", "model": None,
                 "raw_output": "(model call skipped)", "refused": False, "error": None}
    else:
        model = backends.complete(args.category, prompt, args.provider, args.model)
    print("-" * 70)
    print(f"MODEL PROPOSAL  [cat {model['category']} · {model['provider']}/{model['model']}]"
          + ("  [!] REFUSAL?" if model.get("refused") else "")
          + (f"  ERROR: {model['error']}" if model.get("error") else ""))
    print("-" * 70)
    print(model["raw_output"], "\n")

    # 2) Researcher curates + approves the concrete action.
    if task.get("executor") == "manual":
        executed = (args.payload or (input("Command you ran (external tooling): ") if _tty()
                    else "(manual — record externally)"))
        result = (input("Result / artifact ref: ") if _tty() and not args.payload
                  else "(see external capture)")
    else:
        default = task.get("example_payload", "")
        if args.payload is not None:
            value = args.payload
        elif _tty():
            value = input(f"Exact value to send [{default}]: ").strip() or default
        else:
            value = default
            print(f"(non-interactive: using example payload: {default!r})")
        action = build_http_action(task, value)
        print(f"\nWILL SEND -> {action['method']} {lab.LAB_BASE_URL}{action['path']}"
              f"  params={action.get('params')} upload={'yes' if task.get('upload') else 'no'}")

        approved = args.yes or (_tty() and input("Execute against the lab? [y/N]: ").lower().startswith("y"))
        executed = {"value": value, **{k: v for k, v in action.items() if k != "files"}}
        if approved:
            try:
                result = lab.execute(action["method"], action["path"],
                                     params=action.get("params"), data=action.get("data"),
                                     files=action.get("files"))
            except lab.ContainmentError as e:
                result = {"refused": str(e)}
        else:
            result = "(skipped by researcher — not executed)"

    # 3) Auto-write the per-action record (§8.1).
    rid = args.record_id or f"{args.task}-{model['category']}-{dt.datetime.now():%H%M%S}"
    path = record.write_record(args.scenario, rid, task, model, prompt, executed, result)
    print(f"\n[OK] per-action record written: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
