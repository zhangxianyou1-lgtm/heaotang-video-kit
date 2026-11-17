"""Validate planned frame slots, not rendered media. Run with Python 3.11+."""
from pathlib import Path
import json
import argparse
import math
import re
import contextlib
import io
import tempfile

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {2:6314,3:6356,4:7065,5:7026,6:7194,7:7055,8:7679,9:7031}
# User-named old sections; quotes may be subdivided into several new slots.
REQUIRED = {1:[15,16,17,18],2:[8,9,10,11,12,16,19,20],3:[8,12,13,14,15,17],
            4:[10,13,15,16,17,26,27,28],5:[7,11,13,15,16,17,18,20],
            6:[4,5,6,8,22,25,26,27,28],7:[4,7,8,9,12,14,20,23,24,25],
            8:[7,8,9,11,20,21,23,25,26],9:[4,8,12,16,18,19,23]}

def validate(d):
    n=d['total_frames']; slots=d['slots']; assert isinstance(n,int) and n>450
    counts=dict.fromkeys('PGRA',0); cursor=0; run=0; maximum=0
    a_ids=set(); a_runs=0; last=None
    for s in slots:
        a,b,m=s['start_frame'],s['end_frame'],s['mode']
        assert type(a) is int and type(b) is int and a==cursor and b>a, ('coverage',s)
        assert m in counts and s['task_id'] and s['quote'] and s['action']
        assert s['task_id'] not in ('A_open','A_bridge') and not s['task_id'].startswith('A_tail'), ('retired cross-media filler',s)
        counts[m]+=b-a;cursor=b
        run=run+b-a if m=='P' else 0;maximum=max(maximum,run)
        if m=='A':
            a_ids.add(s['task_id']);a_runs+=last!='A'
        last=m
    assert cursor==n
    merged=[]
    for s in slots:
        if merged and s['mode']=='G' and merged[-1]['mode']=='G' and s['task_id']==merged[-1]['task_id']:
            merged[-1]['end_frame']=s['end_frame']
        else: merged.append(dict(s))
    for s in merged:
        if s['mode']=='G':
            length=s['end_frame']-s['start_frame']
            assert 120<=length<=165 or (length in (180,210) and s.get('duration_exception_reason')), ('G duration / full-action exception',s)
            assert s.get('generation_model')=='MiniMax-H3', ('H3 model missing',s)
            seconds=s.get('generation_seconds')
            assert type(seconds) is int and 4<=seconds<=15 and seconds>=math.ceil(length/30), ('H3 integer duration',s)
    assert slots[0]['start_frame']==0 and slots[0]['end_frame']==180 and slots[0]['mode']=='G', 'six-second continuous G opener required'
    assert counts['P']/n<=.35 and maximum<=360, ('P limit',counts,maximum)
    for s in slots:
        a,b=s['start_frame'],s['end_frame']
        if a<180:assert s['mode'] in 'GA', ('opening',s)
        if a<360 and b>180:assert s['mode']=='P', ('face window',s)
        if a<450 and b>360:assert s['mode']=='R', ('preview',s)
        if b>n-150:assert s['mode']=='P', ('closing',s)
    return {'total_frames':n,'P_percent':round(counts['P']/n*100,2),
            'G_percent':round(counts['G']/n*100,2),'R_percent':round(counts['R']/n*100,2),
            'A_percent':round(counts['A']/n*100,2),'longest_P_seconds':maximum/30,
            'A_task_ids':len(a_ids),'A_continuous_runs':a_runs,'slots':len(slots),
            'timing_basis':d['timing_basis']}

def validate_g_prompts(d, require_all=False):
    cjk_re = re.compile(r'[\u4e00-\u9fff]')
    stale = ('自主构思', '不限定固定道具', '拉丝黑钢', '磨旧黄铜', '绝无手指', '默认不新增人物')
    prompt_fields = ('first_frame_prompt', 'last_frame_prompt', 'video_prompt')
    checked = 0
    for s in d['slots']:
        if s['mode'] != 'G':
            continue
        for t in stale:
            assert t not in s.get('action', ''), ('stale term in action', s['task_id'], t)
        if require_all:
            assert isinstance(s.get('visual_thesis'), str) and s['visual_thesis'].strip(), ('missing visual_thesis', s['task_id'])
        for k in prompt_fields:
            if require_all or k in s:
                v = s.get(k)
                assert isinstance(v, str) and len(cjk_re.findall(v)) >= 200, ('G prompt < 200 CJK chars', s['task_id'], k, len(cjk_re.findall(v or '')))
                for t in stale:
                    assert t not in v, ('stale term in prompt', s['task_id'], k, t)
                checked += 1
    return checked


def validate_sfx(d, require_aligned=False):
    a_slots={(s['task_id'],s['start_frame']):s for s in d['slots'] if s['mode']=='A'}
    event_slots=set();pending=0
    for e in d.get('sfx_events',[]):
        key=(e['task_id'],e['slot_start']);s=a_slots[key];event_slots.add(key)
        for field in ('anchor','visual_event','sound'):
            assert isinstance(e.get(field),str) and e[field].strip(), ('missing semantic SFX field',field,e)
        if e.get('alignment_status')=='pending_word_alignment':
            pending+=1
            assert all(e.get(k) is None for k in ('local_frame','global_frame','sample_48k','sample_offset')), ('invented pending timecode',e)
            assert not require_aligned, 'SFX word alignment pending: plan is not ready to mix'
        else:
            assert e.get('alignment_status')=='aligned' and e.get('alignment_evidence'), ('missing word-alignment evidence',e)
            assert type(e.get('local_frame')) is int and type(e.get('global_frame')) is int
            assert 0<=e['local_frame']<s['end_frame']-s['start_frame']
            assert e['global_frame']==s['start_frame']+e['local_frame']
            assert e.get('sample_48k')==e['global_frame']*1600
    assert event_slots==set(a_slots), 'A slots missing semantic SFX events'
    return pending

def main(require_aligned=False, plan=None):
    windows=json.loads((ROOT/'tools/r60_required_windows.json').read_text(encoding='utf-8'))
    all_files=sorted((ROOT/'plans/九期整期画面分配').glob('0[1-9]*.json'))
    known={p.name:int(p.name[:2]) for p in all_files}
    files=[Path(plan)] if plan else all_files
    if plan is None: assert len(files)==9, f'Expected nine JSON plans, got {len(files)}'
    results=[]
    for p in files:
        d=json.loads(p.read_text(encoding='utf-8-sig')); i=known.get(p.name)
        if i in EXPECTED:assert d['total_frames']==EXPECTED[i] and d['timing_basis']=='existing'
        elif i==1:assert d['timing_basis']=='estimated'
        stats=validate(d);stats['title']=d['title']
        stats['G_prompts_checked']=validate_g_prompts(d, require_all=(i is not None))
        stats['pending_SFX_events']=validate_sfx(d,require_aligned)
        # old_section is an auditable source anchor, not a new timeline boundary.
        missing=[s for s in d['slots'] if s.get('old_section') in REQUIRED.get(i,[]) and s['mode']=='P'
                 and s['start_frame']>=450 and s['end_frame']<=d['total_frames']-150]
        assert not missing, ('required visualized section still P',p.name,missing)
        for s in d['slots']:
            if s['mode']!='P': continue
            for a,b,old_section in windows.get(str(i),[]):
                assert max(a,s['start_frame'],450)>=min(b,s['end_frame'],d['total_frames']-150), ('required window P',p.name,old_section,s)
        stats['A_reference_met']=stats['A_percent']>=20 and stats['A_task_ids']>=4
        results.append(stats)
    print(json.dumps(results,ensure_ascii=False,indent=2))
    return results

def self_check():
    d={'title':'self-check fixture','total_frames':1200,'timing_basis':'estimated','slots':[]}
    for a,b,m in [(0,180,'G'),(180,360,'P'),(360,450,'R'),(450,1050,'A'),(1050,1200,'P')]:
        d['slots'].append(dict(start_frame=a,end_frame=b,mode=m,task_id=str(a),quote='x',action='x'))
    d['slots'][0].update(generation_model='MiniMax-H3',generation_seconds=6,duration_exception_reason='continuous opener')
    validate(d)
    def rejected(call):
        try: call()
        except AssertionError: return
        raise AssertionError('Invalid plan accepted')
    for index,mode in [(2,'G'),(3,'P')]:
        bad=json.loads(json.dumps(d));bad['slots'][index]['mode']=mode
        rejected(lambda:validate(bad))
    for value in (5,6.0):
        bad=json.loads(json.dumps(d));bad['slots'][0]['generation_seconds']=value
        rejected(lambda:validate(bad))
    d['slots'][0].update(visual_thesis='test thesis',first_frame_prompt='测'*200,last_frame_prompt='测'*200,video_prompt='测'*200)
    assert validate_g_prompts(d,True)==3
    bad=json.loads(json.dumps(d));bad['slots'][0]['first_frame_prompt']='太短'
    rejected(lambda:validate_g_prompts(bad,True))
    d['sfx_events']=[dict(task_id='450',slot_start=450,anchor='三单',visual_event='订单落位',sound='pop',alignment_status='pending_word_alignment',local_frame=None,global_frame=None,sample_48k=None)]
    assert validate_sfx(d)==1
    rejected(lambda:validate_sfx(d,True))
    d['sfx_events'][0]['local_frame']=12
    rejected(lambda:validate_sfx(d))
    d['sfx_events'][0].update(alignment_status='aligned',alignment_evidence='fixture word boundary',global_frame=462,sample_48k=462*1600)
    assert validate_sfx(d,True)==0
    # An aligned single plan must not be blocked by the other eight pending plans.
    with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
        p=Path(tmp)/'single_plan.json';p.write_text(json.dumps(d),encoding='utf-8')
        assert len(main(True,p))==1
        known=next((ROOT/'plans/九期整期画面分配').glob('02*.json'))
        p=Path(tmp)/known.name;p.write_text(json.dumps(d),encoding='utf-8')
        rejected(lambda:main(True,p))  # Known episode totals remain locked.

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--require-aligned-sfx',action='store_true',help='Reject unaligned SFX before mixing; default only checks the plan.')
    parser.add_argument('--plan',type=Path,help='Check one JSON plan; omit to check all nine. Known episode filenames retain their original-frame and mandatory-window checks.')
    args=parser.parse_args()
    self_check();main(args.require_aligned_sfx,args.plan)
