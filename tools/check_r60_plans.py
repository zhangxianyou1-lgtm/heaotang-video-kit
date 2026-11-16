"""Validate planned frame slots, not rendered media. Run with Python 3.11+."""
from pathlib import Path
import json

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
    g_run=0; g_id=None; a_ids=set(); a_runs=0; last=None
    for s in slots:
        a,b,m=s['start_frame'],s['end_frame'],s['mode']
        assert type(a) is int and type(b) is int and a==cursor and b>a, ('coverage',s)
        assert m in counts and s['task_id'] and s['quote'] and s['action']
        counts[m]+=b-a;cursor=b
        run=run+b-a if m=='P' else 0;maximum=max(maximum,run)
        if m=='G':
            g_run=g_run+b-a if g_id==s['task_id'] else b-a
            assert g_run<=165, ('G child exceeds 5.5s',s)
            g_id=s['task_id']
        else:g_id=None;g_run=0
        if m=='A':
            a_ids.add(s['task_id']);a_runs+=last!='A'
        last=m
    assert cursor==n
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

def main():
    windows=json.loads((ROOT/'tools/r60_required_windows.json').read_text(encoding='utf-8'))
    files=sorted((ROOT/'plans/九期整期画面分配').glob('0[1-9]*.json'))
    assert len(files)==9, f'Expected nine JSON plans, got {len(files)}'
    results=[]
    for p in files:
        d=json.loads(p.read_text(encoding='utf-8-sig')); i=int(p.name[:2])
        if i in EXPECTED:assert d['total_frames']==EXPECTED[i] and d['timing_basis']=='existing'
        else:assert d['timing_basis']=='estimated'
        stats=validate(d);stats['title']=d['title']
        # old_section is an auditable source anchor, not a new timeline boundary.
        missing=[s for s in d['slots'] if s.get('old_section') in REQUIRED[i] and s['mode']=='P'
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
    d={'total_frames':600,'timing_basis':'estimated','slots':[]}
    for a,b,m in [(0,120,'G'),(120,180,'G'),(180,360,'P'),(360,450,'R'),(450,600,'P')]:
        d['slots'].append(dict(start_frame=a,end_frame=b,mode=m,task_id=str(a),quote='x',action='x'))
    # Deliberately invalid P ratio must fail; checks cannot simply accept coverage.
    try: validate(d)
    except AssertionError: pass
    else: raise AssertionError('P ratio rejection missing')

if __name__=='__main__':
    self_check();main()
