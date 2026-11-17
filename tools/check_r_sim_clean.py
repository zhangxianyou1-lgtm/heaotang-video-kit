"""Anti-CYA ("反叠甲") & Anti-Micro-Text ("反蚂蚁小字") UI validator for R-class simulated software.

Targets two well-known GPT-5.x / R6.0 UI generation habits:
1. Defensive CYA Disclaimers ("叠甲癖"): plastering "交互演示·示例数据", "演示账号", "原稿年费口径",
   "输入示例商品码", "键盘模拟扫码输入", "演示收款，不调用支付接口", "本地演示数据·无真实支付与扣费",
   "案例拆解", "注：", "说明：" inside business software UIs.
2. Explanatory Micro-Text ("蚂蚁小字癖"): adding <small> tags, 9px-12px grey helper captions under
   every title/input/button, or Tailwind text-xs / text-[10px] that become unreadable blurs on 9:16 mobile.

Every simulated HTML/CSS/JS/TSX/JSX/Vue file MUST pass this scanner with ZERO violations before
capturing screenshots or screen recordings.

Usage:
  python tools/check_r_sim_clean.py --self-check
  python tools/check_r_sim_clean.py path/to/sim_app/
"""
from pathlib import Path
import argparse
import json
import re
import sys

FORBIDDEN_UI_TERMS = (
    '交互演示',
    '演示账号',
    '演示数据',
    '本地演示',
    '演示商品',
    '演示收款',
    '演示环境',
    '演示模式',
    '演示系统',
    '演示版',
    '仅供演示',
    '仅供参考',
    '示例数据',
    '示例商品',
    '示例账号',
    '示例门店',
    '示例条码',
    '模拟扫码',
    '键盘模拟',
    '模拟输入',
    '模拟数据',
    '模拟环境',
    '测试账号',
    '测试数据',
    '测试环境',
    '不调用支付',
    '无真实支付',
    '非真实支付',
    '无真实扣费',
    '不产生真实',
    '不触发真实',
    '原稿年费',
    '原稿口径',
    '口径说明',
    '按原稿',
    '案例拆解',
    '虚构数据',
    '示意数据',
    '脱敏示例',
    '复刻界面',
    '仿真演示',
)

# Catch <small> tags, CSS font-size <= 12px (8px..12px), <= 0.75rem (0.5rem..0.75rem), and Tailwind text-xs / text-[8..12px]
MICRO_FONT_PATTERNS = [
    (re.compile(r'<\s*small\b', re.I), 'HTML <small> micro-text tag forbidden (remove helper footnotes)'),
    (
        re.compile(r'font-size\s*:\s*(?:[89]|1[0-2])(?:\.\d+)?\s*px\b', re.I),
        'CSS font-size <= 12px forbidden (unreadable micro-text on mobile vertical video; use >=15px logical / >=28px on 1080p)',
    ),
    (
        re.compile(r'fontSize\s*:\s*(?:[89]|1[0-2])\b'),
        'JS inline fontSize <= 12 forbidden (unreadable micro-text on mobile vertical video)',
    ),
    (
        re.compile(r'font-size\s*:\s*0\.(?:[4-6]\d*|7[0-5]?)\s*rem\b', re.I),
        'CSS font-size <= 0.75rem forbidden (unreadable micro-text on mobile vertical video)',
    ),
    (
        re.compile(r'\btext-(?:xs|\[(?:[89]|1[0-2])px\])\b'),
        'Tailwind text-xs / text-[<=12px] forbidden (remove helper micro-captions and enlarge primary UI text)',
    ),
]

SCAN_EXTS = {'.html', '.htm', '.css', '.js', '.jsx', '.ts', '.tsx', '.vue', '.svelte'}
COMMENT_RE = re.compile(r'<!--.*?-->|/\*.*?\*/', re.S)


def scan_text(text: str, source_name: str = '<memory>', check_micro_font: bool = True):
    cleaned = COMMENT_RE.sub('', text)
    hits = []
    for lineno, line in enumerate(cleaned.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith('//'):
            continue
        for term in FORBIDDEN_UI_TERMS:
            if term in line:
                hits.append({
                    'file': source_name,
                    'line': lineno,
                    'category': 'cya_disclaimer',
                    'rule': term,
                    'snippet': stripped[:120],
                })
        if check_micro_font:
            for regex, message in MICRO_FONT_PATTERNS:
                if regex.search(line):
                    hits.append({
                        'file': source_name,
                        'line': lineno,
                        'category': 'micro_text',
                        'rule': message,
                        'snippet': stripped[:120],
                    })
    return hits


def scan_path(target: Path):
    files = [target] if target.is_file() else [
        p for p in sorted(target.rglob('*'))
        if p.is_file() and p.suffix.lower() in SCAN_EXTS and 'node_modules' not in p.parts
    ]
    assert files, f'No UI source files found under {target}'
    all_hits = []
    for f in files:
        txt = f.read_text(encoding='utf-8', errors='replace')
        all_hits.extend(scan_text(txt, str(f), check_micro_font=True))
    return len(files), all_hits


def self_check():
    bad_sample = """
    <style>.hint { font-size: 11px; color: #999; } .sub { font-size: 0.7rem; }</style>
    <header>门店管理 <span>店长工作台 / 演示账号</span></header>
    <div class="badge text-xs">交互演示 · 示例数据</div>
    <p style="font-size: 12px">原稿年费口径：¥2,500 / 店 / 年</p>
    <input placeholder="输入示例商品码 SP1001" />
    <small>键盘模拟扫码输入 · 演示商品库匹配</small>
    <nav><a>扫码收银</a><a>案例拆解</a></nav>
    <footer>演示收款，不调用支付接口 | 本地演示数据 · 无真实支付与扣费</footer>
    """
    hits = scan_text(bad_sample, 'bad_pos.html')
    cya_rules = {h['rule'] for h in hits if h['category'] == 'cya_disclaimer'}
    micro_count = sum(1 for h in hits if h['category'] == 'micro_text')
    for expected in ('演示账号', '交互演示', '示例数据', '原稿年费', '示例商品', '键盘模拟', '案例拆解', '演示收款', '不调用支付', '本地演示', '无真实支付'):
        assert expected in cya_rules, f'Failed to catch CYA term: {expected}'
    assert micro_count >= 4, f'Expected >=4 micro-text violations, got {micro_count}'

    good_sample = """
    <style>
      body { font-size: 18px; color: #111827; }
      .price { font-size: 32px; font-weight: 700; }
      .btn-pay { font-size: 20px; }
    </style>
    <header>东街服饰收银台 <span>收银员：林店长（02）</span></header>
    <input placeholder="扫码或输入货号" />
    <div class="item"><span>帆布托特包</span><strong class="price">¥89.00</strong></div>
    <button class="btn-pay">收款确认</button>
    """
    assert scan_text(good_sample, 'clean_pos.html') == []
    print('PASS: check_r_sim_clean self-check (caught all CYA disclaimers + <=12px/<small>/text-xs micro-text)')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('target', nargs='?', type=Path, help='File or directory of R-class simulated UI source code.')
    parser.add_argument('--self-check', action='store_true', help='Run built-in anti-CYA & anti-micro-text regression test.')
    args = parser.parse_args()

    if args.self_check or args.target is None:
        self_check()
        if args.target is None:
            return

    count, hits = scan_path(args.target)
    if hits:
        print(json.dumps({
            'status': 'FAIL',
            'scanned_files': count,
            'fix_hint': 'Remove all defensive CYA disclaimers and helper micro-text (<small>, <=12px, <=0.75rem, text-xs). Keep max 3 clean visual layers with large high-contrast typography for 9:16 mobile viewing.',
            'violations': hits,
        }, ensure_ascii=False, indent=2))
        sys.exit(1)
    print(json.dumps({'status': 'PASS', 'scanned_files': count, 'violations': []}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
