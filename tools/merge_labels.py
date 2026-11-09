#!/usr/bin/env python3
"""يدمج ملفات «نموذج مطابقة العناوين» التي يرسلها المعلمون في labels.json بعد فحصها.
   الاستعمال:  python tools/merge_labels.py ملف1.txt ملف2.txt        (أضف --dry-run للمعاينة دون كتابة)
   لا يُضاف عنوان إلا إذا: <=70 حرفاً، فيه حروف، خانته معروفة، ولا يتعارض مع عنوان موجود بخانة مختلفة (يُبلَّغ عنه لتقرر أنت)."""
import argparse, json, os, re, sys, unicodedata

KEYS = {'title', 'grade', 'outcomes', 'level', 'strategies', 'resources', 'concepts', 'warmup', 'procedures', 'formative', 'summative', 'enrich', 'homework', 'weeklyNote', 'ignore'}
ap = argparse.ArgumentParser(); ap.add_argument('files', nargs='+'); ap.add_argument('--labels', default='labels.json'); ap.add_argument('--dry-run', action='store_true')
a = ap.parse_args()

def norm(t):                                   # توحيد للمقارنة فقط (التشكيل، الهمزات، الياء/الألف المقصورة، الفراغات، الحالة)
    t = re.sub('[\u064B-\u065F\u0640]', '', unicodedata.normalize('NFKC', t))
    t = re.sub('[أإآ]', 'ا', t).replace('ى', 'ي').replace('ة', 'ه')
    return re.sub(r'[^\u0621-\u064Aa-z0-9]+', ' ', t.lower()).strip()

data = {'version': 1, 'labels': []}
if os.path.exists(a.labels): data = json.load(open(a.labels, encoding='utf-8'))
have = {norm(x['t']): x for x in data['labels']}
added, same, conflict, bad = [], 0, [], []
for fn in a.files:
    txt = open(fn, encoding='utf-8-sig', errors='replace').read()
    if 'نموذج مطابقة عناوين التحضير' not in txt[:400]: bad.append((fn, 'ليس ملف نموذج مطابقة')); continue
    for line in txt.splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line: continue
        left, right = line.split('=', 1)
        m = re.search(r'\[(\w+)\]', left)
        if not m or m.group(1) not in KEYS: continue
        k = m.group(1)
        for t in re.split(r'[،,؛;|]+', right):
            t = t.strip()
            if not t: continue
            if len(t) > 70 or not re.search(r'[\u0621-\u064Aa-zA-Z]', t): bad.append((fn, 'مرفوض: ' + t[:40])); continue
            n = norm(t)
            if not n: continue
            if n in have:
                if have[n]['k'] == k: same += 1
                else: conflict.append((t, have[n]['k'], k, os.path.basename(fn)))
            else:
                x = {'t': t, 'k': k}; data['labels'].append(x); have[n] = x; added.append((t, k))
print('أُضيف:', len(added), '| مكرر (موجود بنفس الخانة):', same, '| تعارض:', len(conflict), '| مرفوض/تجاوز:', len(bad))
for t, k in added: print('  +', t, '←', k)
for t, k0, k1, f in conflict: print('  ! تعارض «%s»: الموجود %s، والجديد %s (من %s) — لم يُغيَّر' % (t, k0, k1, f))
for f, why in bad: print('  x', os.path.basename(f), why)
if added and not a.dry_run:
    json.dump(data, open(a.labels, 'w', encoding='utf-8'), ensure_ascii=False, indent=1); print('كُتب', a.labels)
elif a.dry_run: print('(معاينة فقط، لم يُكتب شيء)')
