"""One-off: inspect the 2010-2024 Taiwan continuous GNSS dataset (Zenodo 23551543, CC-BY 4.0)."""
import urllib.request, zipfile, os, io
O = 'data/_job/'; os.makedirs(O, exist_ok=True); log = open(O + 'log.txt', 'w')
U = 'https://zenodo.org/api/records/23551543/files/continuous_GNSS_Taiwan.zip/content'
p = '/tmp/gnss.zip'
urllib.request.urlretrieve(U, p)
z = zipfile.ZipFile(p); names = z.namelist()
log.write(f'{len(names)} files\n')
ext = {}
for n in names: ext.setdefault(os.path.splitext(n)[1], []).append(n)
for e, v in ext.items(): log.write(f'{e or "(dir)"}: {len(v)} e.g. {v[:4]}\n')
for n in names:
    low = n.lower()
    if n.endswith('/'): continue
    if any(k in low for k in ('readme', 'metadata', 'offset', 'quality', 'equipment', 'station', 'log')) and z.getinfo(n).file_size < 3_000_000:
        log.write(f'\n===== {n} ({z.getinfo(n).file_size} bytes)\n'); log.write(z.read(n).decode('utf-8', 'replace')[:6000])
ts = [n for n in names if not n.endswith('/') and not any(k in n.lower() for k in ('readme', 'metadata', 'offset', 'quality', 'equipment'))]
for n in ts[:3]:
    log.write(f'\n===== SAMPLE {n} ({z.getinfo(n).file_size} bytes)\n'); t = z.read(n).decode('utf-8', 'replace').splitlines()
    log.write('\n'.join(t[:40]) + '\n...\n' + '\n'.join(t[-5:]) + '\n')
log.close()
