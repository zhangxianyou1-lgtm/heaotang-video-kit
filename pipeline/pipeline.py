"""Local talking-head preparation. Codex reviews edit.json before rendering.

No API keys, platform uploads or paid generation are performed by this script.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import zipfile
import wave

FPS = 30


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def run(args):
    proc = subprocess.run([str(x) for x in args], capture_output=True, text=True,
                          encoding='utf-8', errors='replace')
    if proc.returncode:
        raise RuntimeError(f'{args[0]} failed: {proc.stderr[-4000:]}')
    return proc


def probe(path):
    return json.loads(run(['ffprobe', '-v', 'error', '-show_streams', '-show_format',
                          '-of', 'json', path]).stdout)


def digest(path):
    with open(path, 'rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def load_job(path):
    path = Path(path).resolve()
    cfg = read(path)
    def resolve(value):
        p = Path(value)
        return p.resolve() if p.is_absolute() else (path.parent / p).resolve()
    cfg['sources'] = [str(resolve(x)) for x in cfg['sources']]
    if not cfg['sources'] or len(set(cfg['sources'])) != len(cfg['sources']):
        raise ValueError('sources must be a nonempty ordered list without duplicate paths')
    for p in cfg['sources']:
        if not Path(p).is_file():
            raise FileNotFoundError(p)
    cfg['background'] = str(resolve(cfg['background'])) if cfg.get('background') else str(Path(__file__).parent / 'assets/studio-medium.png')
    if not Path(cfg['background']).is_file():
        raise FileNotFoundError(cfg['background'])
    if cfg.get('blur', 'heavy') not in ('medium', 'heavy'):
        raise ValueError('blur must be medium or heavy')
    if cfg.get('green_screen') is not True:
        raise ValueError('This renderer requires verified green-screen footage; use a temporal matting workflow for other footage.')
    if not re.fullmatch(r'0x[0-9a-fA-F]{6}', cfg.get('key_color', '0x5fa557')):
        raise ValueError('Invalid key color')
    for key, default, low, high in [('key_similarity', .055, .001, 1), ('key_blend', .025, 0, 1),
                                  ('foreground_gain', .97, .5, 1.5), ('foreground_offset', 1, -30, 30),
                                  ('speech_margin', .21, .05, .5), ('silence_min', .8, .6, 10),
                                  ('silence_db', -35, -80, -10)]:
        value = float(cfg.get(key, default))
        if not math.isfinite(value) or not low <= value <= high:
            raise ValueError(f'Invalid {key}')
        cfg[key] = value
    work = resolve(cfg.get('work', 'jobs/current'))
    work.mkdir(parents=True, exist_ok=True)
    cfg['script'] = str(resolve(cfg['script'])) if cfg.get('script') else None
    if cfg['script'] and not Path(cfg['script']).is_file():
        raise FileNotFoundError(cfg['script'])
    return cfg, work


def complement(duration, cuts):
    """Frame-quantized retained intervals; merge overlapping removals."""
    end = math.floor((duration + .000002) * FPS)
    merged = []
    for a, b in sorted(cuts):
        a, b = max(0, round(a * FPS)), min(end, round(b * FPS))
        if b <= a:
            continue
        if merged and a <= merged[-1][1]:
            merged[-1][1] = max(b, merged[-1][1])
        else:
            merged.append([a, b])
    result, pos = [], 0
    for a, b in merged + [[end, end]]:
        if a > pos:
            result.append([pos / FPS, a / FPS])
        pos = b
    return result


def silence_intervals(log, duration):
    intervals, start = [], None
    for line in log.splitlines():
        m = re.search(r'silence_start: ([\d.]+)', line)
        if m:
            start = float(m[1])
        m = re.search(r'silence_end: ([\d.]+)', line)
        if m and start is not None:
            intervals.append([start, float(m[1])]); start = None
    if start is not None:
        intervals.append([start, duration])
    return intervals


def prepare(cfg, work):
    if (work / 'edit.json').exists():
        raise FileExistsError('edit.json already exists; preserve reviewed edits and use a new work directory to re-prepare')
    from faster_whisper import WhisperModel
    import numpy as np
    model = WhisperModel(cfg.get('model', 'large-v3-turbo'), device=cfg.get('device', 'cpu'),
                         compute_type=cfg.get('compute_type', 'int8'), cpu_threads=6)
    sources, review = [], []
    for index, filename in enumerate(cfg['sources'], 1):
        print(f'Analyze {index}/{len(cfg["sources"])}: {Path(filename).name}', flush=True)
        info = probe(filename)
        if not any(s['codec_type'] == 'audio' for s in info['streams']):
            raise ValueError(f'No audio: {filename}')
        v = next(s for s in info['streams'] if s['codec_type'] == 'video')
        if abs(v['width'] / v['height'] - 9 / 16) > .015:
            raise ValueError(f'Confirm reframing for non-9:16 footage: {filename}')
        duration = float(info['format']['duration'])
        sha = digest(filename)
        if any(s['sha256'] == sha for s in sources):
            raise ValueError('Duplicate footage by SHA256; select its intended occurrence explicitly')
        wav = work / f'source_{index:03}.wav'
        run(['ffmpeg', '-v', 'error', '-y', '-i', filename, '-vn', '-ac', '1', '-ar', '16000', wav])
        # FFmpeg has already decoded PCM; avoid a second decode through PyAV.
        with wave.open(str(wav), 'rb') as audio_file:
            audio = np.frombuffer(audio_file.readframes(audio_file.getnframes()), np.int16).astype(np.float32) / 32768.
        segments, _ = model.transcribe(audio, language='zh', beam_size=5,
                                      word_timestamps=True, vad_filter=True,
                                      condition_on_previous_text=False)
        transcript = [{'start': s.start, 'end': s.end, 'text': s.text,
                       'words': [{'start': w.start, 'end': w.end, 'word': w.word,
                                  'probability': w.probability} for w in s.words]} for s in segments]
        write(work / f'source_{index:03}.json', transcript)
        words = [w for s in transcript for w in s['words']]
        if not words:
            raise ValueError(f'No recognized speech; inspect {filename}')
        scan = run(['ffmpeg', '-hide_banner', '-nostats', '-i', filename,
                    '-vf', 'scale=270:480,freezedetect=n=-60dB:d=0.6,blackdetect=d=0.1',
                    '-af', f'silencedetect=noise={cfg["silence_db"]}dB:d={cfg["silence_min"]}',
                    '-f', 'null', '-'])
        (work / f'source_{index:03}.log').write_text(scan.stderr, encoding='utf-8')
        silence = silence_intervals(scan.stderr, duration)
        margin = cfg['speech_margin']
        cuts = [[0, max(0, words[0]['start'] - margin)],
                [min(duration, words[-1]['end'] + margin), duration]]
        for a, b in silence:
            if b - a > 2 * margin:
                cuts.append([a + margin, b - margin])
        sources.append({'file': filename, 'sha256': sha, 'duration': duration,
                        'probe': info, 'silences': silence,
                        'keep': complement(duration, cuts), 'notes': '自动候选；尚未审核口误、重复、动作及剪点'})
        review.append(f'## Source {index}: {Path(filename).name}\n' + '\n'.join(
            f'{s["start"]:.3f}–{s["end"]:.3f} {s["text"]}' for s in transcript))
        for second, t in enumerate([words[0]['start'], duration / 2, words[-1]['end']]):
            run(['ffmpeg', '-v', 'error', '-y', '-ss', str(min(t, duration - .1)), '-i', filename,
                 '-frames:v', '1', '-vf', 'scale=540:960', work / f'source_{index:03}_{second}.jpg'])
    write(work / 'edit.json', {'reviewed': False, 'background_reviewed': False,
                             'review_notes': '', 'sources': sources})
    (work / 'transcript.md').write_text('\n\n'.join(review), encoding='utf-8')
    print(f'Ready for Codex review: {work / "edit.json"}', flush=True)


def validate_edit(edit, cfg):
    if edit.get('reviewed') is not True or edit.get('background_reviewed') is not True or not edit.get('review_notes', '').strip():
        raise ValueError('Codex must inspect speech, joins and background and record review before render')
    if [s['file'] for s in edit['sources']] != cfg['sources']:
        raise ValueError('Source order changed; update/review the job and edit together')
    clips, cursor = [], 0
    for number, source in enumerate(edit['sources'], 1):
        if digest(source['file']) != source['sha256']:
            raise ValueError('Source changed after review')
        previous = 0
        for start, end in source['keep']:
            if not all(math.isfinite(x) for x in (start, end)) or not 0 <= start < end <= source['duration'] + .00001 or start < previous:
                raise ValueError('Invalid, overlapping or reversed keep ranges')
            a, b = round(start * FPS), round(end * FPS)
            if b <= a or b > math.floor((source['duration'] + .000002) * FPS):
                raise ValueError('Empty or out-of-range frame interval')
            clips.append({'source_index': number, 'file': source['file'], 'start': a / FPS,
                          'end': b / FPS, 'frames': b - a, 'output_start': cursor / FPS,
                          'output_end': (cursor + b - a) / FPS})
            cursor += b - a; previous = end
        if not source['keep'] and not source.get('notes', '').strip():
            raise ValueError('An omitted source needs a reason')
    if not clips:
        raise ValueError('No retained footage')
    return clips


def render_clip(cfg, clip, target):
    duration = clip['frames'] / FPS
    bgblur = 'gblur=sigma=14:steps=3,' if cfg.get('blur', 'heavy') == 'heavy' else ''
    gain, offset = cfg['foreground_gain'], cfg['foreground_offset']
    filt = (
        '[0:v]setpts=PTS-STARTPTS,fps=30,scale=720:1280:flags=lanczos,setsar=1,'
        f'format=yuva444p,chromakey={cfg.get("key_color", "0x5fa557")}:{cfg["key_similarity"]}:{cfg["key_blend"]},'
        'gblur=sigma=0.35:planes=8,format=rgba,despill=green:mix=0.5:expand=0.03,'
        f'lutrgb=r=val*{gain}+{offset}:g=val*{gain}+{offset}:b=val*{gain}+{offset}[fg];'
        '[1:v]scale=720:1280:flags=lanczos,setsar=1,format=yuv444p,' + bgblur +
        'loop=loop=-1:size=1:start=0,setpts=N/(30*TB)[bg];'
        '[bg][fg]overlay=shortest=1:format=auto,scale=1080:1920:flags=lanczos,format=yuv420p[v];'
        f'[0:a]asetpts=PTS-STARTPTS,aresample=48000,apad=whole_dur={duration:.9f},'
        f'atrim=duration={duration:.9f},afade=t=in:d=0.004,afade=t=out:st={max(0,duration-.004):.9f}:d=0.004[a]')
    run(['ffmpeg', '-v', 'error', '-y', '-threads', '2', '-ss', str(clip['start']), '-i', clip['file'],
         '-framerate', '30', '-i', cfg['background'], '-filter_complex_threads', '1', '-filter_complex', filt,
         '-map', '[v]', '-map', '[a]', '-t', f'{duration:.9f}', '-c:v', 'libx264', '-threads', '2',
         '-preset', 'veryfast', '-crf', '18', '-color_primaries', 'bt709', '-color_trc', 'bt709',
         '-colorspace', 'bt709', '-r', '30', '-fps_mode', 'cfr', '-c:a', 'pcm_s16le', '-ar', '48000', '-ac', '2', target])


def qc(path, expected_frames, work):
    info = probe(path)
    v = next(s for s in info['streams'] if s['codec_type'] == 'video')
    a = next(s for s in info['streams'] if s['codec_type'] == 'audio')
    scan = run(['ffmpeg', '-hide_banner', '-nostats', '-i', path,
                '-vf', 'scale=270:480,freezedetect=n=-60dB:d=0.6,blackdetect=d=0.1:pix_th=0.10:pic_th=0.98',
                '-af', 'silencedetect=noise=-35dB:d=2', '-f', 'null', '-'])
    (work / 'qc.log').write_text(scan.stderr, encoding='utf-8')
    events = [line for line in scan.stderr.splitlines() if re.search(r'freeze_start:|black_start:|silence_start:|error|corrupt|invalid', line, re.I)]
    technical = (int(v.get('nb_frames', 0)) == expected_frames and
                 (v['width'], v['height'], v['r_frame_rate']) == (1080, 1920, '30/1') and
                 abs(float(v['duration']) - float(a['duration'])) < 1/FPS and
                 abs(float(v.get('start_time', 0)) - float(a.get('start_time', 0))) < 1/FPS and not events)
    report = {'technical_pass': technical, 'expected_frames': expected_frames, 'probe': info,
              'events_to_review': events, 'visual_and_listening_review': 'pending'}
    write(work / 'qc.json', report)
    return technical


def render(cfg, work):
    edit = read(work / 'edit.json')
    clips = validate_edit(edit, cfg)
    parts = work / 'parts'; parts.mkdir(exist_ok=True)
    for i, clip in enumerate(clips):
        print(f'Render {i+1}/{len(clips)}', flush=True)
        render_clip(cfg, clip, parts / f'{i:04}.mkv')
    concat = parts / 'concat.txt'
    concat.write_text(''.join(f"file '{i:04}.mkv'\n" for i in range(len(clips))), encoding='utf-8')
    final = work / 'base.mp4'
    run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '1', '-i', concat,
         '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', final])
    write(work / 'timeline.json', {'fps': FPS, 'clips': clips, 'duration': clips[-1]['output_end'],
                                  'background_sha256': digest(cfg['background']), 'settings': cfg})
    run(['ffmpeg', '-v', 'error', '-y', '-i', final, '-vn', '-c:a', 'pcm_s16le', work / 'narration.wav'])
    words = []
    for c in clips:
        transcript = read(work / f'source_{c["source_index"]:03}.json')
        for seg in transcript:
            for word in seg['words']:
                mid = (word['start'] + word['end']) / 2
                if c['start'] <= mid < c['end']:
                    words.append({**word, 'start': c['output_start'] + max(0, word['start'] - c['start']),
                                  'end': min(c['output_end'], c['output_start'] + word['end'] - c['start'])})
    write(work / 'words.json', words)
    passed = qc(final, sum(c['frames'] for c in clips), work)
    for i, clip in enumerate(clips):
        for side, t in [('in', clip['output_start'] + .04), ('out', clip['output_end'] - .04)]:
            run(['ffmpeg', '-v', 'error', '-y', '-ss', str(max(0,t)), '-i', final, '-frames:v', '1',
                 '-vf', 'scale=540:960', parts / f'review_{i:04}_{side}.jpg'])
    note = ('# 后半段制作入口\n\n基准视频：base.mp4；完整基准音频：narration.wav。\n'
            '源到基准片映射：timeline.json；字级时间：words.json（ASR候选，须校对）。\n'
            '先完成 qc.json 的剪点试听和人物/桌面/发丝检查，再读取教程的完整流程与Claude交接技能。\n'
            '本音频已按新剪点拼接；后续动画、字幕、BGM必须以它为基准，不再引用原片时间。\n'
            'Claude任务文字由Codex按内容填写；不能把本提示当作已完成的动画任务包。\n')
    (work / 'NEXT.md').write_text(note, encoding='utf-8')
    with zipfile.ZipFile(work / 'handoff-input.zip', 'w', zipfile.ZIP_DEFLATED) as z:
        for name in ('narration.wav', 'words.json', 'NEXT.md'):
            z.write(work / name, name)
    print(f'Base ready. Technical pass={passed}; visual/listening review still required. Continue from {work / "NEXT.md"}')
    if not passed:
        raise RuntimeError('QC flagged issues; review qc.json before downstream production')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['prepare', 'preview', 'render'])
    parser.add_argument('job')
    parser.add_argument('--source', type=int, default=1)
    parser.add_argument('--start', type=float, default=2)
    args = parser.parse_args()
    cfg, work = load_job(args.job)
    if args.command == 'prepare':
        prepare(cfg, work)
    elif args.command == 'preview':
        if not 1 <= args.source <= len(cfg['sources']) or not math.isfinite(args.start) or args.start < 0:
            raise ValueError('Invalid preview source/start')
        path = cfg['sources'][args.source - 1]
        duration = float(probe(path)['format']['duration'])
        frames = min(90, math.floor((duration - args.start) * FPS))
        if frames < 1:
            raise ValueError('Preview starts beyond source end')
        render_clip(cfg, {'file': path, 'start': args.start, 'frames': frames}, work / 'background-preview.mkv')
    else:
        render(cfg, work)


if __name__ == '__main__':
    main()
