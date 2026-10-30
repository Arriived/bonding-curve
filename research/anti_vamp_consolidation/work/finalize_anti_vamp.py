from pathlib import Path
import json,hashlib,zipfile
root=Path(__file__).resolve().parents[1];bundle=root/'outputs/anti_vamp_study';report=root/'outputs/ANTI_VAMP_FINDINGS.md'
text=report.read_text(encoding='utf-8')
summary='''## Decision against the anti-vamp objective

**Conditional go for an original-first routing prototype as an anti-fragmentation mechanism, within these assumptions.** The goal is to concentrate the original meme's early market, not make a coin survive indefinitely. Creation remains open and unredirected purchases remain possible.

- At default 60% reach and 60% consent ceiling, original-first raises the original's minute-15 recent buying share from 25.3% to 51.1% and its organic-holder 5%-impact sell depth from 69.21 to 137.27. This is a measured recovery of concentration, not new money.
- With 100% reach and 100% consent ceiling, loyalty leaves realized consent around 95%. The original receives 96.4% of recent buying and depth is 254.57, versus 264.08 in the no-copy reference. High reach and willingness can therefore approximate the unfragmented market in this particular model.
- The two-minute cap election can also consolidate a market, but a trained copy-target policy makes the copy the selected recipient in all 100 confirmation seeds. With nine copies it earns 1,183.59 versus 318.25 for the same trade in independent markets, an additional 865.35. Buying the original early is a separate ordinary speculation case, not automatically a vampire exploit.
- With correct first registration, the tested copy purchases cannot replace the original-first recipient. That does not mean the copies cannot trade or their holders cannot profit; the mechanism reduces the routing advantage of competing copies rather than banning them.
- The central unresolved product choices are defining the canonical original mint, obtaining real order-flow reach, and buyers choosing the proposed recipient. A false-first registration sends recommendations to the wrong asset. The simulation does not validate an authenticity classifier or actual adoption.

**Research preference:** shared narrative discovery plus explicit original-mint purchases is more aligned with protecting the original than a capital contest that awards a copy the buying stream. If the objective is instead whichever coin becomes a focal point, report elected-lead concentration separately; a copy winning is not itself a failure on that different objective. These are off-chain synthetic findings, not a production validation.

'''
text=text.replace('## Primary result',summary+'## Primary result',1)
report.write_text(text,encoding='utf-8')
validation=json.loads((bundle/'final_validation.json').read_text())
validation['findings_sha256']=hashlib.sha256(report.read_bytes()).hexdigest()
(bundle/'final_validation.json').write_text(json.dumps(validation,indent=2))
with zipfile.ZipFile(root/'outputs/ANTI_VAMP_EVIDENCE.zip','w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in bundle.rglob('*'):
        if p.is_file():z.write(p,p.relative_to(bundle).as_posix())
    z.write(report,'ANTI_VAMP_FINDINGS.md')
with zipfile.ZipFile(root/'outputs/ANTI_VAMP_EVIDENCE.zip') as z:assert z.testzip() is None
print(json.dumps(validation,indent=2))
