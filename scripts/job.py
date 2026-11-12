"""One-off: extract metadata + weekly-median time series from the Taiwan continuous GNSS dataset
(Zenodo record 23551543, CC-BY 4.0, Institute of Earth Sciences, Academia Sinica)."""
import urllib.request, zipfile, os, json, statistics
O = 'data/_job/'; os.makedirs(O, exist_ok=True)
U = 'https://zenodo.org/api/records/23551543/files/continuous_GNSS_Taiwan.zip/content'
p = '/tmp/gnss.zip'; urllib.request.urlretrieve(U, p)
z = zipfile.ZipFile(p); names = z.namelist()
for n in names:
    if n.endswith(('.csv', '.txt')): open(O + os.path.basename(n), 'wb').write(z.read(n))
enu = sorted(n for n in names if n.endswith('.enu'))
open(O + 'enu_files.txt', 'w').write('\n'.join(f'{n}\t{z.getinfo(n).file_size}' for n in enu))
out = {}
for n in enu:
    key = n.split('time_series/')[1]
    wk = {}
    for line in z.read(n).decode('utf-8', 'replace').splitlines():
        a = line.split()
        if len(a) < 5: continue
        try: t, e, nn, u = float(a[0]), float(a[2]), float(a[3]), float(a[4])
        except ValueError: continue
        w = int((t - 2010) * 52.1775)
        wk.setdefault(w, []).append((t, e, nn, u))
    rows = []
    for w in sorted(wk):
        v = wk[w]
        rows.append([round(statistics.median(x[0] for x in v), 4)] + [round(statistics.median(x[i] for x in v), 1) for i in (1, 2, 3)] + [len(v)])
    out[key] = rows
json.dump(out, open(O + 'weekly.json', 'w'), separators=(',', ':'))
print(len(out), os.path.getsize(O + 'weekly.json'))
