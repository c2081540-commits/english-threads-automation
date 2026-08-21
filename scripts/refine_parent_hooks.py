#!/usr/bin/env python3
"""Audit and refine only unposted production Threads parent hooks."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from threads_automation.difficulty import (question_type, validate_hook_for_item,
                                           validate_hook_sequence)  # noqa: E402

NEW_HOOKS = {
    "ENG-000008": "動きのある表現、自然に選べる？",
    "ENG-000018": "主語を見れば解ける基礎。",
    "ENG-000019": "時制の感覚、残ってる？",
    "ENG-000020": "この動作、前置詞で差がつく。",
    "ENG-000022": "定番の一言、すぐ出る？",
    "ENG-000023": "よく使う形、どっちだった？",
    "ENG-000026": "否定文になると少し迷う。",
    "ENG-000027": "数え方まで意識できる？",
    "ENG-000028": "時間表現、なんとなくで選んでない？",
    "ENG-000030": "ここは基礎をサクッと。",
    "ENG-000031": "短い文ほど形で迷いやすい。",
    "ENG-000032": "似た形、場面で区別できる？",
    "ENG-000033": "文の流れまでつかめる？",
    "ENG-000034": "短い会話ほど視点が大事。",
    "ENG-000035": "正しそうな英文、見抜ける？",
    "ENG-000036": "基本の形を1問だけ。",
    "ENG-000039": "この動き、英語でどうつなぐ？",
    "ENG-000041": "職場の一場面、自然な形は？",
    "ENG-000042": "朝のルーティンで基礎確認。",
    "ENG-000043": "期間表現、迷わずいける？",
    "ENG-000044": "よく使う言い回し、覚えてる？",
    "ENG-000045": "実際の予定ならどう言う？",
    "ENG-000046": "空席を前に、自然な一言は？",
    "ENG-000047": "仕事中にも使う定番表現。",
}
INSTRUCTION_IDS = {
    "ENG-000008", "ENG-000020", "ENG-000027", "ENG-000032", "ENG-000039", "ENG-000044",
}
EXACT_DUPLICATE_IDS = {
    "ENG-000018", "ENG-000019", "ENG-000020", "ENG-000022", "ENG-000023",
    "ENG-000026", "ENG-000028", "ENG-000030", "ENG-000031", "ENG-000033",
    "ENG-000034", "ENG-000035", "ENG-000036", "ENG-000041", "ENG-000042",
    "ENG-000043", "ENG-000045", "ENG-000047",
}
ROLE_IDS = {"ENG-000008", "ENG-000046"}


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def reason(content_id: str) -> str:
    reasons = []
    if content_id in INSTRUCTION_IDS:
        reasons.append("instruction-style")
    if content_id in EXACT_DUPLICATE_IDS:
        reasons.append("exact duplicate within 20")
    if content_id in ROLE_IDS:
        reasons.append("hook role/content mismatch")
    return ", ".join(reasons) or "quality gate PASS"


def main() -> int:
    out = ROOT / "artifacts" / "weekly" / "2026-08-20"
    audit_path = out / "thread-hook-audit.json"
    prior_old_hooks = {}
    if audit_path.is_file():
        prior = read(audit_path)
        prior_old_hooks = {row["content_id"]: row["old_hook"] for row in prior.get("items", [])}
    rows = []
    sequence = []
    for number in range(6, 48):
        content_id = f"ENG-{number:06d}"
        queue_path = ROOT / "data" / "queue" / f"{content_id}.json"
        master_path = ROOT / "data" / "master" / "quiz" / f"{content_id}.json"
        queue, master = read(queue_path), read(master_path)
        if queue["status"] == "posted":
            continue
        current_hook = queue["parent_text"]
        old_hook = prior_old_hooks.get(content_id, current_hook)
        new_hook = NEW_HOOKS.get(content_id, current_hook)
        validate_hook_for_item(master, new_hook)
        queue["parent_text"] = new_hook
        master["threads_parent_text"] = new_hook
        write(queue_path, queue)
        write(master_path, master)
        audit_item = dict(master)
        audit_item["threads_parent_text"] = new_hook
        audit_item["publish_at"] = queue["publish_at"]
        sequence.append(audit_item)
        rows.append({
            "content_id": content_id,
            "difficulty": master["difficulty_level"],
            "question_type": question_type(master),
            "learning_point": master["learning_point"],
            "old_hook": old_hook,
            "new_hook": new_hook,
            "question_guide_ja": master.get("question_guide_ja"),
            "reason": reason(content_id),
            "decision": "REVISE" if content_id in NEW_HOOKS else "KEEP",
        })
    validate_hook_sequence(sequence)
    out.mkdir(parents=True, exist_ok=True)
    write(out / "thread-hook-audit.json", {"items": rows})
    lines = ["# 未投稿Threads親フック監査", "",
             "| content_id | difficulty | question type | learning point | 旧hook | 新hook | question_guide_ja | 変更理由 | 判定 |",
             "|---|---|---|---|---|---|---|---|---|"]
    for row in rows:
        lines.append("| {content_id} | {difficulty} | {question_type} | {learning_point} | "
                     "{old_hook} | {new_hook} | {question_guide_ja} | {reason} | {decision} |".format(
                         **{**row, "question_guide_ja": row["question_guide_ja"] or "-"}))
    (out / "thread-hook-audit.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"audited={len(rows)} keep={sum(row['decision'] == 'KEEP' for row in rows)} "
          f"revise={sum(row['decision'] == 'REVISE' for row in rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
