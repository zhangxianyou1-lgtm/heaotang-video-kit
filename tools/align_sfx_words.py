"""Align pending_word_alignment SFX events against pipeline words.json candidates.

Usage:
  python tools/align_sfx_words.py --plan plans/九期整期画面分配/02_探针02_四个按钮五千块.json --words jobs/current/words.json
  python tools/align_sfx_words.py --self-check
"""
import argparse
import json
from pathlib import Path
import re

FPS = 30
SAMPLE_RATE = 48000
SAMPLES_PER_FRAME = SAMPLE_RATE // FPS  # 1600


def clean_text(text):
    return re.sub(r"[\s，。？！、：；“”\"'…·—\-（）()]", "", text or "")


def match_sfx_candidates(plan_data, words):
    """Return candidate frame/sample alignments for each sfx_event using ASR word timestamps."""
    norm_words = []
    for w in words:
        token = clean_text(w.get("word", ""))
        if token:
            norm_words.append({
                "token": token,
                "start": float(w["start"]),
                "end": float(w["end"]),
                "frame": round(float(w["start"]) * FPS),
            })

    results = []
    for ev in plan_data.get("sfx_events", []):
        sf, ef = int(ev["slot_start"]), int(ev["slot_end"])
        anchor_raw = ev.get("anchor_text", "")
        anchor = clean_text(anchor_raw)
        slot_words = [w for w in norm_words if sf <= w["frame"] < ef]
        joined = "".join(w["token"] for w in slot_words)
        hit_frame = None
        if anchor and anchor in joined:
            idx = joined.index(anchor)
            acc = 0
            for w in slot_words:
                if acc + len(w["token"]) > idx:
                    hit_frame = max(sf, min(ef - 1, w["frame"]))
                    break
                acc += len(w["token"])
        results.append({
            **ev,
            "candidate_global_frame": hit_frame,
            "candidate_local_frame": (hit_frame - sf) if hit_frame is not None else None,
            "candidate_sample_48k": (hit_frame * SAMPLES_PER_FRAME) if hit_frame is not None else None,
            "review_note": "ASR候选帧，须人工复听确认重音后将alignment_status改为aligned",
        })
    return results


def self_check():
    plan = {
        "sfx_events": [
            {"task_id": "A01", "slot_start": 300, "slot_end": 600, "anchor_text": "少卖九千",
             "visual_event": "数字锁定", "sound": "Pop", "alignment_status": "pending_word_alignment",
             "local_frame": None, "global_frame": None, "sample_48k": None}
        ]
    }
    words = [
        {"word": "一个月", "start": 11.0, "end": 11.4},
        {"word": "少卖", "start": 11.5, "end": 11.8},
        {"word": "九千", "start": 11.8, "end": 12.2},
    ]
    out = match_sfx_candidates(plan, words)
    assert out[0]["candidate_global_frame"] == 345
    assert out[0]["candidate_local_frame"] == 45
    assert out[0]["candidate_sample_48k"] == 345 * 1600
    print("PASS: align_sfx_words self-check")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan")
    ap.add_argument("--words")
    ap.add_argument("--output")
    ap.add_argument("--self-check", action="store_true")
    args = ap.parse_args()
    if args.self_check or not (args.plan and args.words):
        self_check()
        return
    plan_data = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    words = json.loads(Path(args.words).read_text(encoding="utf-8"))
    candidates = match_sfx_candidates(plan_data, words)
    if args.output:
        Path(args.output).write_text(json.dumps(candidates, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        print(json.dumps(candidates, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
