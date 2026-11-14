"""Run with python pipeline/test_pipeline.py; no model/network required."""
import copy
import tempfile
from pathlib import Path
from pipeline import complement, silence_intervals, validate_edit, digest


def must_reject(edit, cfg):
    try:
        validate_edit(edit, cfg)
    except ValueError:
        return
    raise AssertionError('Unsafe edit was accepted')


assert complement(10, [[0, 1], [3, 4], [3.5, 5], [9, 10]]) == [[1, 3], [5, 9]]
assert complement(1, [[0, 2]]) == []
assert complement(1, []) == [[0, 1]]
assert silence_intervals('silence_start: 0\nsilence_end: 1\nsilence_start: 8', 10) == [[0, 1], [8, 10]]
with tempfile.TemporaryDirectory() as temp:
    p = Path(temp) / 'source'; p.write_bytes(b'original')
    cfg = {'sources': [str(p)]}
    edit = {'reviewed': True, 'background_reviewed': True, 'review_notes': 'Checked test inputs',
            'sources': [{'file': str(p), 'sha256': digest(p), 'duration': 10,
                         'keep': [[1, 3], [5, 9]], 'notes': 'remove repeated test segment'}]}
    clips = validate_edit(edit, cfg)
    assert sum(c['frames'] for c in clips) == 180
    assert clips[1]['output_start'] == 2 and clips[1]['output_end'] == 6
    for intervals in ([[1, 3], [2, 4]], [[-1, 2]], [[1, 11]], [[1, 1]], [[float('nan'), 2]]):
        bad = copy.deepcopy(edit); bad['sources'][0]['keep'] = intervals; must_reject(bad, cfg)
    bad = copy.deepcopy(edit); bad['reviewed'] = False; must_reject(bad, cfg)
    p.write_bytes(b'replaced'); must_reject(edit, cfg)
print('PASS: cut merge, boundary quantization, timeline, review gate, invalid intervals, source replacement')
