#!/usr/bin/env python3
import json
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from threads_automation.builder import (build_normal_queue,  # noqa: E402
                                        build_quiz_queue)
from threads_automation.paths import QUEUE_DIR  # noqa: E402
from threads_automation.schedule import (ALLOWED_STATUSES, eligibility,
                                          load_schedule_config)  # noqa: E402


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    if len(sys.argv) not in {2, 3}:
        raise SystemExit("Usage: finalize_week_schedule.py START_DATE [AS_OF_ISO8601]")
    start = date.fromisoformat(sys.argv[1])
    now = (datetime.fromisoformat(sys.argv[2]) if len(sys.argv) == 3
           else datetime.now(ZoneInfo("Asia/Tokyo")))
    if now.tzinfo is None:
        raise ValueError("AS_OF must include a timezone")
    config = load_schedule_config()
    instagram_schedule = read_json(
        REPO_ROOT.parent / "english-instagram-automation" / "data" / "production" /
        f"final-schedule-{start.isoformat()}.json"
    )
    if instagram_schedule["timezone"] != config["timezone"]:
        raise ValueError("Instagram and Threads schedule configs differ")

    queues = []
    dry_run = [f"DRY RUN Threads final schedule | {instagram_schedule['start_date']} to {instagram_schedule['end_date']}"]
    for scheduled in instagram_schedule["items"]:
        content_id = scheduled["content_id"]
        queue = (build_quiz_queue(content_id) if scheduled["content_type"] == "quiz"
                 else build_normal_queue(content_id))
        if queue["publish_at"] != scheduled["publish_at"]:
            raise ValueError(f"Instagram/Threads publish_at mismatch: {content_id}")
        queue["execution_eligibility"] = eligibility(queue["publish_at"], now)
        if queue["status"] not in ALLOWED_STATUSES:
            raise ValueError("invalid Threads queue status")
        if queue["content_type"] == "quiz":
            if queue["question_image"] is None:
                raise ValueError(f"quiz is not READY: {content_id}")
            if not (REPO_ROOT / queue["question_image"]).is_file():
                raise FileNotFoundError(f"question image missing: {content_id}")
            if queue["parent_status"] != "pending" or queue["answer_status"] != "pending":
                raise ValueError(f"quiz queue statuses must be pending: {content_id}")
            dry_run.append(
                f"{queue['publish_at']} | {content_id} | quiz | parent=yes | reply=yes | "
                f"{queue['question_image']} | {queue['status']} | {queue['execution_eligibility']}"
            )
        else:
            dry_run.append(
                f"{queue['publish_at']} | {content_id} | normal | parent=yes | reply=no | "
                f"asset=none | {queue['status']} | {queue['execution_eligibility']}"
            )
        write_json(QUEUE_DIR / f"{content_id}.json", queue)
        queues.append({key: queue[key] for key in
                       ("content_id", "platform", "content_type", "publish_at", "status", "execution_eligibility")})

    if len(queues) != 49 or len({item["content_id"] for item in queues}) != 49:
        raise ValueError("Threads final schedule must contain 49 unique items")
    final = {
        "start_date": instagram_schedule["start_date"],
        "end_date": instagram_schedule["end_date"],
        "timezone": config["timezone"],
        "generated_at": now.isoformat(),
        "past_slot_policy": config["past_slot_policy"],
        "items": queues,
    }
    write_json(REPO_ROOT / "data" / "queue" / f"final-schedule-{start.isoformat()}.json", final)
    output = REPO_ROOT / "artifacts" / f"threads-final-dry-run-{start.isoformat()}.txt"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(dry_run) + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
