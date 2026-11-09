#!/usr/bin/env python3
"""يولّد موقع المكتبة (مجلد _site): ينسخ library/ وlabels.json، ويكتب index.json.
   البنية:  library/<المادة>/<الصف>/<الملف>      مثال: library/اللغة العربية/الصف الثامن/ف1.docx
   الصيغ المقبولة: docx html htm mht mhtml zip txt md   (ما عداها يُتجاهل مع تنبيه)"""
import argparse, datetime, hashlib, html, json, os, re, shutil, sys

EXT = {'.docx', '.html', '.htm', '.mht', '.mhtml', '.zip', '.txt', '.md'}
KEYS = {'title', 'grade', 'outcomes', 'level', 'strategies', 'resources', 'concepts', 'warmup', 'procedures', 'formative', 'summative', 'enrich', 'homework', 'weeklyNote', 'ignore'}
MAX = 90 * 1024 * 1024                      # حد GitHub لكل ملف 100م.ب
SIGN = 'مجموعة أسئلة برق'                  # توقيع ملفات الأسئلة التي تنتجها لوحة الأسئلة في برق
QMAX = 60000

def qinfo(path):
    """ملف نصي بتوقيع برق ← (عدد الأسئلة، ترويسة) أو None إن لم يكن مجموعة أسئلة."""
    try: txt = open(path, encoding='utf-8-sig').read()
    except Exception: return None
    if SIGN not in txt[:300]: return None
    lines = txt.splitlines(); i = 0; meta = {}
    while i < len(lines) and lines[i].lstrip().startswith('#'):
        m = re.match(r'\s*#\s*([^:：]+)[:：]\s*(.*)', lines[i])
        if m: meta[m.group(1).strip()] = m.group(2).strip()
        i += 1
    body = '\n'.join(lines[i:]).strip()
    if not body or len(body) > QMAX: return None
    ls = [l.strip() for l in body.splitlines() if l.strip()]
    inline = ls and all(('=' in l or re.match(r'\[[^\]]+\]', l)) and not re.match(r'(الجواب|الإجابة|الاجابة|answer)', l, re.I) for l in ls)
    n = len(ls) if inline else len([b for b in re.split(r'\n\s*\n+', body) if b.strip()])
    return n, meta

ap = argparse.ArgumentParser()
ap.add_argument('--lib', default='library'); ap.add_argument('--labels', default='labels.json'); ap.add_argument('--out', default='_site')
a = ap.parse_args()
warn = []

def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for ch in iter(lambda: f.read(1 << 20), b''): h.update(ch)
    return h.hexdigest()[:16]

if os.path.exists(a.out): shutil.rmtree(a.out)
os.makedirs(a.out)
files = []
for root, _, names in os.walk(a.lib):
    for n in sorted(names):
        full = os.path.join(root, n); rel = os.path.relpath(full, a.lib).replace(os.sep, '/')
        low = n.lower()
        if n.startswith('.') or low.startswith('readme'): continue
        if os.path.splitext(low)[1] not in EXT: warn.append('تجاوزتُ (صيغة غير مدعومة): ' + rel); continue
        size = os.path.getsize(full)
        if size > MAX: warn.append('تجاوزتُ (أكبر من 90 م.ب): ' + rel); continue
        parts = rel.split('/')
        subject = parts[0] if len(parts) >= 2 else ''
        grade = parts[1] if len(parts) >= 3 else ''
        kind, count = 'lesson', 0
        if low.endswith('.txt'):
            qi = qinfo(full)
            if qi:
                kind, count = 'questions', qi[0]
                subject = subject or qi[1].get('المادة', ''); grade = grade or qi[1].get('الصف', '')
            elif SIGN in open(full, encoding='utf-8-sig', errors='replace').read(300):
                warn.append('تجاوزتُ (مجموعة أسئلة فارغة أو أكبر من 60 ألف حرف): ' + rel); continue
        dst = os.path.join(a.out, 'library', rel); os.makedirs(os.path.dirname(dst), exist_ok=True); shutil.copy2(full, dst)
        files.append({'path': 'library/' + rel, 'name': os.path.splitext(n)[0], 'subject': subject, 'grade': grade,
                      'size': size, 'hash': sha(full), 'type': os.path.splitext(low)[1][1:], 'kind': kind, 'count': count})
files.sort(key=lambda f: (f['subject'], f['grade'], f['name']))

labels = {'version': 1, 'labels': []}
if os.path.exists(a.labels):
    try:
        j = json.load(open(a.labels, encoding='utf-8'))
        for x in j.get('labels', []):
            t, k = str(x.get('t', '')).strip(), x.get('k')
            if k in KEYS and 0 < len(t) <= 70 and re.search(r'[\u0621-\u064Aa-zA-Z]', t): labels['labels'].append({'t': t, 'k': k})
            else: warn.append('عنوان مرفوض في labels.json: ' + json.dumps(x, ensure_ascii=False))
    except Exception as e:
        sys.exit('labels.json غير صالح: %s' % e)
json.dump(labels, open(os.path.join(a.out, 'labels.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

now = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
json.dump({'version': 1, 'generated': now, 'files': files}, open(os.path.join(a.out, 'index.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
open(os.path.join(a.out, '.nojekyll'), 'w').close()
rows = ''.join('<li>%s — %s %s%s</li>' % (html.escape(f['name']), html.escape(f['subject']), html.escape(f['grade']), ' (أسئلة)' if f['kind'] == 'questions' else '') for f in files)
open(os.path.join(a.out, 'index.html'), 'w', encoding='utf-8').write(
    '<!doctype html><meta charset="utf-8"><title>مكتبة برق</title><body dir="rtl" style="font-family:Tahoma,Arial;max-width:720px;margin:30px auto;line-height:1.9">'
    '<h1>مكتبة تحضيرات برق</h1><p>هذه صفحة بيانات تقرؤها إضافة برق. ملفات: %d · عناوين مشتركة: %d</p><ul>%s</ul></body>' % (len(files), len(labels['labels']), rows))
print('ملفات:', len(files), '| عناوين مشتركة:', len(labels['labels']))
for w in warn: print('تنبيه:', w)
