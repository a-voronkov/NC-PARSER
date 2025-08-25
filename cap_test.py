import sys, json, os
from pathlib import Path
sys.path.insert(0, 'src')
from nc_parser.processing.parser import parse_document_to_text
files = ['data/samples/medical_document_scan.pdf', 'data/samples/formal_document.docx']
print('ENV_CAPTION:', os.getenv('NC_CAPTIONING_ENABLED'), os.getenv('NC_CAPTION_BACKEND'))
for f in files:
    p = Path(f)
    print('FILE:', f, 'exists=', p.exists())
    if not p.exists():
        continue
    doc = parse_document_to_text(p)
    caps = []
    for pg in (doc.pages or []):
        for el in (pg.get('elements', []) if isinstance(pg, dict) else []):
            if isinstance(el, dict) and el.get('type') == 'image_caption':
                caps.append(el.get('description'))
    print('captions:', caps)
    print('metrics:', getattr(doc, 'metrics', None))
    print('timings_ms_keys:', list((doc.timings_ms or {}).keys()))
