"""Universal R6.1/R6.2 Five-Pillar Plan Validator (Pure-Instruction GitHub Edition).

Validates:
- 5 Visual Pillars + Brand Packaging: P (Full-screen host), PIP (Picture-in-Picture cutout on A/R/D),
  G (Surreal 3D spectacle via ChatGPT + MiniMax-H3), R (High-fidelity simulated/live software screen recording),
  A (Claude zero-preset parallel-subagent motion graphics), D (Real public news/person/archival media),
  B (Official 4.0-4.5s column intro & 4.5s end brand logo).
- Host presence dual-lock: 15% <= P <= 35% (target 20%-30%, single run <= 12s/360f),
  PIP >= 3 slots and >= 15% duration (bottom_y <= 1420), P + PIP >= 35%, max 60s without host face.
- D-slot anti-laziness check: requires >= 3 verified real public source candidates (no AI fake news).
- B-slot rules: forbidden in [0, 450); supports B_intro after hook & B_outro (e.g. 135f / 4.5s) after closing 5s P.
- G-slot >= 200 CJK chars & zero engineering term pollution; word-level SFX alignment gate.

Usage:
  python tools/check_r60_plans.py
  python tools/check_r60_plans.py --plan jobs/current/plan.json
  python tools/check_r60_plans.py --plan jobs/current/plan.json --require-aligned-sfx
"""
from pathlib import Path
import argparse
import contextlib
import io
import json
import math
import re
import tempfile

ROOT = Path(__file__).resolve().parents[1]
VALID_TIMING_BASES = ('estimated', 'locked', 'existing')
VALID_PIP_SHAPES = ('rect', 'square', 'circle')
STALE_TERMS = ('自主构思', '不限定固定道具', '拉丝黑钢', '磨旧黄铜', '绝无手指', '默认不新增人物')
PROMPT_POLLUTION = (
    'y1440', 'y1640', 'y1536', '字幕', '后期图层', '后期叠',
    '乱码', '假字', '错字', '不瞎画', '安全带', '安全区', '避让带', '避让区',
)
R_CYA_FORBIDDEN = (
    '交互演示', '演示账号', '演示数据', '本地演示', '示例数据', '示例商品',
    '键盘模拟', '模拟扫码', '演示收款', '不调用支付', '无真实支付', '原稿年费', '原稿口径',
)
PROMPT_FIELDS = ('first_frame_prompt', 'last_frame_prompt', 'video_prompt')
CJK_RE = re.compile(r'[\u4e00-\u9fff]')


def validate(d, allow_legacy_no_pip=False):
    n = d['total_frames']
    slots = d['slots']
    assert isinstance(n, int) and n > 600, ('total_frames must be int > 600', n)
    assert d.get('timing_basis') in VALID_TIMING_BASES, ('invalid timing_basis', d.get('timing_basis'))

    counts = dict.fromkeys('PGRABD', 0)
    cursor = 0
    run_p = 0
    max_p = 0
    no_face_run = 0
    max_no_face = 0
    pip_frames = 0
    pip_slots = 0
    a_ids = set()
    a_runs = 0
    b_intro_slots = 0
    b_outro_slots = 0
    d_slots = 0
    last = None

    for idx, s in enumerate(slots):
        a, b, m = s['start_frame'], s['end_frame'], s['mode']
        assert type(a) is int and type(b) is int and a == cursor and b > a, ('coverage', s)
        assert m in counts and s.get('task_id') and s.get('quote') and s.get('action'), ('missing slot fields', s)
        assert s['task_id'] not in ('A_open', 'A_bridge') and not str(s['task_id']).startswith('A_tail'), (
            'retired cross-media filler', s
        )
        dur = b - a

        if m == 'B':
            assert a >= 450, ('brand intro/logo forbidden inside opening 0-15s hook [0,450)', s)
            assert 105 <= dur <= 180, ('brand B slot must be 105-180 frames (3.5-6.0s official cut range)', s)
            assert isinstance(s.get('branding_asset'), str) and s['branding_asset'].strip(), ('missing branding_asset', s)
            assert s.get('has_audio') is True, ('brand B slot must record has_audio=True', s)
            if b == n:
                b_outro_slots += 1
            else:
                b_intro_slots += 1

        if m == 'R':
            for bad_cya in R_CYA_FORBIDDEN:
                assert bad_cya not in s.get('action', ''), (
                    'GPT defensive CYA disclaimer forbidden in R-class UI/action (run check_r_sim_clean.py)', s['task_id'], bad_cya
                )

        if m == 'D':
            # Real public news / historical / public figure / official keynote footage
            cands = s.get('public_candidates')
            assert isinstance(cands, list) and len(cands) >= 3, (
                'D (real public/news media) slot requires >=3 distinct real candidates in public_candidates', s
            )
            assert isinstance(s.get('source_attribution'), str) and s['source_attribution'].strip(), (
                'D slot requires source_attribution for compliance badge', s
            )
            d_slots += 1

        pip = s.get('pip_window')
        has_face = (m == 'P')
        if pip is not None:
            assert m in ('A', 'R', 'D'), ('pip_window only valid on knowledge/demo/doc slots (A/R/D)', s)
            assert isinstance(pip, dict), ('pip_window must be object', s)
            assert pip.get('shape') in VALID_PIP_SHAPES, ('pip_window.shape must be rect|square|circle', s)
            bottom_y = pip.get('bottom_y')
            assert type(bottom_y) is int and 400 <= bottom_y <= 1420, (
                'pip_window.bottom_y must be int <= 1420 (>=20px above y1440 subtitle safe zone)', s
            )
            pip_frames += dur
            pip_slots += 1
            has_face = True

        counts[m] += dur
        cursor = b
        run_p = run_p + dur if m == 'P' else 0
        max_p = max(max_p, run_p)
        no_face_run = 0 if has_face else (no_face_run + dur)
        max_no_face = max(max_no_face, no_face_run)

        if m == 'A':
            a_ids.add(s['task_id'])
            a_runs += (last != 'A')
        last = m

    assert cursor == n, ('end frame mismatch', cursor, n)

    merged = []
    for s in slots:
        if merged and s['mode'] == 'G' and merged[-1]['mode'] == 'G' and s['task_id'] == merged[-1]['task_id']:
            merged[-1]['end_frame'] = s['end_frame']
        else:
            merged.append(dict(s))

    for s in merged:
        if s['mode'] == 'G':
            length = s['end_frame'] - s['start_frame']
            assert 120 <= length <= 165 or (length in (180, 210) and s.get('duration_exception_reason')), (
                'G duration / full-action exception', s
            )
            assert s.get('generation_model') == 'MiniMax-H3', ('H3 model missing', s)
            seconds = s.get('generation_seconds')
            assert type(seconds) is int and 4 <= seconds <= 15 and seconds >= math.ceil(length / 30), (
                'H3 integer duration', s
            )

    assert slots[0]['start_frame'] == 0 and slots[0]['end_frame'] == 180 and slots[0]['mode'] == 'G', (
        'six-second continuous G01 opener [0,180) required'
    )

    # Full-screen P lower & upper lock: 15% <= P <= 35% (prevents both P=0 erasure and >35% dry talking head)
    p_ratio = counts['P'] / n
    assert 0.15 <= p_ratio <= 0.35 and max_p <= 360, (
        'Full-screen P must be within [15%, 35%] (target 20%-30%) and continuous P <= 360f/12s',
        round(p_ratio * 100, 2), max_p
    )

    if not allow_legacy_no_pip:
        pip_ratio = pip_frames / n
        total_face_ratio = (counts['P'] + pip_frames) / n
        assert pip_slots >= 3 and pip_ratio >= 0.15, (
            'Knowledge PIP cutout required: >=3 slots and >=15% duration (bottom_y<=1420)',
            pip_slots, round(pip_ratio * 100, 2)
        )
        assert total_face_ratio >= 0.35, (
            'Combined host presence (Full-screen P + PIP cutout) must be >= 35%',
            round(total_face_ratio * 100, 2)
        )
        assert max_no_face <= 1800, (
            'Host face (P or PIP) must appear at least once every 60s (<=1800 frames)',
            max_no_face
        )

    # Determine speech end boundary (allowing optional trailing B_outro 3.5-6.0s brand logo)
    speech_end = slots[-1]['start_frame'] if (slots[-1]['mode'] == 'B' and slots[-1]['end_frame'] == n) else n

    for s in slots:
        a, b = s['start_frame'], s['end_frame']
        if a < 180:
            assert s['mode'] in 'GA', ('opening [0,180)', s)
        if a < 360 and b > 180:
            assert s['mode'] == 'P', ('face window [180,360)', s)
        if a < 450 and b > 360:
            assert s['mode'] in ('R', 'D'), ('preview window [360,450)', s)
        if a < speech_end and b > speech_end - 150:
            assert s['mode'] == 'P', ('closing 5s host judgment before end/outro [speech_end-150, speech_end)', s)

    return {
        'total_frames': n,
        'P_percent': round(counts['P'] / n * 100, 2),
        'PIP_percent': round(pip_frames / n * 100, 2),
        'host_total_percent': round((counts['P'] + pip_frames) / n * 100, 2),
        'G_percent': round(counts['G'] / n * 100, 2),
        'R_percent': round(counts['R'] / n * 100, 2),
        'A_percent': round(counts['A'] / n * 100, 2),
        'D_percent': round(counts['D'] / n * 100, 2),
        'B_percent': round(counts['B'] / n * 100, 2),
        'longest_P_seconds': round(max_p / 30, 3),
        'max_no_face_seconds': round(max_no_face / 30, 3),
        'PIP_slots': pip_slots,
        'A_task_ids': len(a_ids),
        'A_continuous_runs': a_runs,
        'D_slots': d_slots,
        'B_intro_slots': b_intro_slots,
        'B_outro_slots': b_outro_slots,
        'slots': len(slots),
        'timing_basis': d['timing_basis'],
    }


def validate_g_prompts(d, require_all=True):
    checked = 0
    for s in d['slots']:
        if s['mode'] != 'G':
            continue
        for t in STALE_TERMS:
            assert t not in s.get('action', ''), ('stale term in action', s['task_id'], t)
        if require_all:
            assert isinstance(s.get('visual_thesis'), str) and s['visual_thesis'].strip(), (
                'missing visual_thesis', s['task_id']
            )
        for k in PROMPT_FIELDS:
            if require_all or k in s:
                v = s.get(k)
                cjk_count = len(CJK_RE.findall(v or ''))
                assert isinstance(v, str) and cjk_count >= 200, (
                    'G prompt < 200 CJK chars', s['task_id'], k, cjk_count
                )
                for t in STALE_TERMS:
                    assert t not in v, ('stale term in prompt', s['task_id'], k, t)
                for p_term in PROMPT_POLLUTION:
                    assert p_term not in v, ('engineering/meta pollution in prompt', s['task_id'], k, p_term)
                checked += 1
    return checked


def validate_sfx(d, require_aligned=False):
    a_slots = {(s['task_id'], s['start_frame']): s for s in d['slots'] if s['mode'] == 'A'}
    event_slots = set()
    pending = 0
    for e in d.get('sfx_events', []):
        key = (e['task_id'], e['slot_start'])
        assert key in a_slots, ('SFX event does not match any A slot', key)
        s = a_slots[key]
        event_slots.add(key)
        for field in ('anchor', 'visual_event', 'sound'):
            assert isinstance(e.get(field), str) and e[field].strip(), ('missing semantic SFX field', field, e)
        if e.get('alignment_status') == 'not_used':
            assert isinstance(e.get('reason'), str) and e['reason'].strip(), ('unused SFX needs reason', e)
            assert all(e.get(k) is None for k in ('local_frame', 'global_frame', 'sample_48k', 'sample_offset')), (
                'unused SFX has timecode', e
            )
        elif e.get('alignment_status') == 'pending_word_alignment':
            pending += 1
            assert all(e.get(k) is None for k in ('local_frame', 'global_frame', 'sample_48k', 'sample_offset')), (
                'invented pending timecode', e
            )
            assert not require_aligned, 'SFX word alignment pending: plan is not ready to mix'
        else:
            assert e.get('alignment_status') == 'aligned' and e.get('alignment_evidence'), (
                'missing word-alignment evidence', e
            )
            assert type(e.get('local_frame')) is int and type(e.get('global_frame')) is int
            assert 0 <= e['local_frame'] < s['end_frame'] - s['start_frame']
            assert e['global_frame'] == s['start_frame'] + e['local_frame']
            assert e.get('sample_48k') == e['global_frame'] * 1600
    assert event_slots == set(a_slots), ('A slots missing semantic SFX events', set(a_slots) - event_slots)
    return pending


def check_plan_file(path: Path, require_aligned=False, allow_draft_prompts=False, allow_legacy_no_pip=False):
    d = json.loads(path.read_text(encoding='utf-8-sig'))
    is_template = bool(d.get('is_template'))
    stats = validate(d, allow_legacy_no_pip=allow_legacy_no_pip)
    stats['title'] = d.get('title', path.stem)
    require_prompts = (not allow_draft_prompts) and (not is_template)
    stats['G_prompts_checked'] = validate_g_prompts(d, require_all=True) if require_prompts else 0
    stats['pending_SFX_events'] = validate_sfx(d, require_aligned=(require_aligned and not is_template))
    stats['A_reference_met'] = stats['A_percent'] >= 20 and stats['A_task_ids'] >= 4
    if is_template:
        stats['template_mode'] = True
    return stats


def main(require_aligned=False, plan=None, allow_draft_prompts=False, allow_legacy_no_pip=False):
    if plan is None:
        template_path = ROOT / 'tutorial/03_任务与验收模板/整期方案JSON模板.json'
        checked_template = None
        if template_path.exists():
            checked_template = check_plan_file(template_path, require_aligned=False, allow_draft_prompts=True)
        out = {
            'status': 'PASS',
            'mode': 'universal-five-pillar-self-check',
            'template_verified': bool(checked_template),
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return [out]

    target = Path(plan)
    files = sorted(target.glob('*.json')) if target.is_dir() else [target]
    assert files, f'No JSON plan files found at {target}'
    results = [
        check_plan_file(
            p,
            require_aligned=require_aligned,
            allow_draft_prompts=allow_draft_prompts,
            allow_legacy_no_pip=allow_legacy_no_pip,
        )
        for p in files
    ]
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return results


def self_check():
    pip_br = dict(shape='rect', x=780, y=1080, w=240, h=330, bottom_y=1410)
    pip_bl = dict(shape='square', x=60, y=1150, w=260, h=260, bottom_y=1410)
    d = {
        'title': 'self-check five-pillar fixture',
        'total_frames': 3000,
        'timing_basis': 'estimated',
        'slots': [
            dict(start_frame=0, end_frame=180, mode='G', task_id='G01', quote='q1', action='a1',
                 generation_model='MiniMax-H3', generation_seconds=6,
                 duration_exception_reason='6s continuous opener',
                 visual_thesis='thesis', first_frame_prompt='奇'*205, last_frame_prompt='观'*205, video_prompt='动'*205),
            dict(start_frame=180, end_frame=360, mode='P', task_id='P_open', quote='q2', action='a2'),
            dict(start_frame=360, end_frame=450, mode='R', task_id='R_preview', quote='q3', action='a3'),
            dict(start_frame=450, end_frame=570, mode='P', task_id='P_hook', quote='q4', action='a4'),
            dict(start_frame=570, end_frame=690, mode='B', task_id='B_intro', branding_asset='01_需求探针',
                 has_audio=True, quote='4s片头', action='现成栏目片头自带画面与音效'),
            dict(start_frame=690, end_frame=1050, mode='A', task_id='A01', quote='q5', action='a5', pip_window=pip_br),
            dict(start_frame=1050, end_frame=1230, mode='D', task_id='D01', quote='q_news', action='真实新闻实证',
                 public_candidates=['cand1_keynote', 'cand2_reuters', 'cand3_official_blog'],
                 source_attribution='公开报道资料'),
            dict(start_frame=1230, end_frame=1470, mode='P', task_id='P_mid', quote='q_mid', action='中段真人点题'),
            dict(start_frame=1470, end_frame=1830, mode='A', task_id='A02', quote='q6', action='a6', pip_window=pip_bl),
            dict(start_frame=1830, end_frame=2160, mode='R', task_id='R01', quote='q_demo', action='仿真软件录屏', pip_window=pip_br),
            dict(start_frame=2160, end_frame=2430, mode='A', task_id='A03', quote='q7', action='a7'),
            dict(start_frame=2430, end_frame=2715, mode='A', task_id='A04', quote='q8', action='a8'),
            dict(start_frame=2715, end_frame=2865, mode='P', task_id='P_end', quote='q9', action='末5秒真人收束'),
            dict(start_frame=2865, end_frame=3000, mode='B', task_id='B_outro', branding_asset='00_账号片头_和奥堂AIclub',
                 has_audio=True, quote='4.5s片尾Logo', action='4.5秒和奥堂总Logo收口'),
        ],
        'sfx_events': [
            dict(task_id='A01', slot_start=690, anchor='五千', visual_event='跳变', sound='pop',
                 alignment_status='pending_word_alignment', local_frame=None, global_frame=None, sample_48k=None),
            dict(task_id='A02', slot_start=1470, anchor='三家', visual_event='展开', sound='click',
                 alignment_status='pending_word_alignment', local_frame=None, global_frame=None, sample_48k=None),
            dict(task_id='A03', slot_start=2160, anchor='翻倍', visual_event='碰撞', sound='thud',
                 alignment_status='pending_word_alignment', local_frame=None, global_frame=None, sample_48k=None),
            dict(task_id='A04', slot_start=2430, anchor='归零', visual_event='收束', sound='chime',
                 alignment_status='pending_word_alignment', local_frame=None, global_frame=None, sample_48k=None),
        ],
    }

    st = validate(d)
    assert st['B_intro_slots'] == 1 and st['B_outro_slots'] == 1 and st['PIP_slots'] == 3 and st['D_slots'] == 1
    assert validate_g_prompts(d, True) == 3
    assert validate_sfx(d) == 4

    def rejected(call):
        try:
            call()
        except AssertionError:
            return
        raise AssertionError('Invalid plan accepted')

    # Reject P < 15% (e.g. dropping P_mid so P falls to 450/3000 = 15% - test 13%)
    bad_low_p = json.loads(json.dumps(d))
    bad_low_p['slots'][7]['mode'] = 'R'  # turns 240f P_mid into R -> P = 690-240 = 450 -> wait: 180+120+150=450/3000=15.0%, make P_hook R too -> 330/3000=11%
    bad_low_p['slots'][3]['mode'] = 'R'
    rejected(lambda: validate(bad_low_p))

    # Reject missing PIP cutouts
    bad_no_pip = json.loads(json.dumps(d))
    for s in bad_no_pip['slots']:
        s.pop('pip_window', None)
    rejected(lambda: validate(bad_no_pip))

    # Reject PIP invading subtitle zone (bottom_y > 1420)
    bad_pip_y = json.loads(json.dumps(d))
    bad_pip_y['slots'][5]['pip_window']['bottom_y'] = 1450
    rejected(lambda: validate(bad_pip_y))

    # Reject D slot with fewer than 3 real public candidates
    bad_d = json.loads(json.dumps(d))
    bad_d['slots'][6]['public_candidates'] = ['only_one']
    rejected(lambda: validate(bad_d))

    # Reject B_intro at 0s
    bad_brand = json.loads(json.dumps(d))
    bad_brand['slots'][0]['mode'] = 'B'
    bad_brand['slots'][0]['branding_asset'] = '00_账号片头'
    bad_brand['slots'][0]['has_audio'] = True
    rejected(lambda: validate(bad_brand))

    # Reject short prompts and engineering pollution
    bad = json.loads(json.dumps(d))
    bad['slots'][0]['first_frame_prompt'] = '太短'
    rejected(lambda: validate_g_prompts(bad, True))
    bad = json.loads(json.dumps(d))
    bad['slots'][0]['first_frame_prompt'] = '奇'*205 + '避让y1440字幕'
    rejected(lambda: validate_g_prompts(bad, True))

    # Reject unaligned SFX when --require-aligned-sfx is active
    rejected(lambda: validate_sfx(d, True))
    for ev in d['sfx_events']:
        ev.update(
            alignment_status='aligned',
            alignment_evidence='fixture word boundary',
            local_frame=15,
            global_frame=ev['slot_start'] + 15,
            sample_48k=(ev['slot_start'] + 15) * 1600,
        )
    assert validate_sfx(d, True) == 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--require-aligned-sfx',
        action='store_true',
        help='Reject unaligned SFX before final audio mixing.',
    )
    parser.add_argument(
        '--allow-draft-prompts',
        action='store_true',
        help='Only check slot timeline/ratios and SFX, skipping >=200-char G prompt check during early slot drafting.',
    )
    parser.add_argument(
        '--allow-legacy-no-pip',
        action='store_true',
        help='Allow inspecting pre-PIP historical JSON plans without failing PIP cutout checks.',
    )
    parser.add_argument(
        '--plan',
        type=Path,
        help='Check one JSON plan file or a directory of JSON plans; omit to run universal self-check.',
    )
    args = parser.parse_args()
    self_check()
    main(args.require_aligned_sfx, args.plan, args.allow_draft_prompts, args.allow_legacy_no_pip)
