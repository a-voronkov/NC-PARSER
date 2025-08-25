import os, sys
from pathlib import Path
sys.path.insert(0, 'src')
from nc_parser.processing.parser import parse_document_to_text
p=Path('data/samples/formal_document.docx')
print('EXISTS', p.exists())
os.environ['NC_CAPTIONING_ENABLED']='true'
os.environ['NC_CAPTION_BACKEND']='stub'
doc=parse_document_to_text(p)
print('pages', len(doc.pages))
caps=[]
for pg in (doc.pages or []):
    for el in (pg.get('elements', []) if isinstance(pg, dict) else []):
        if isinstance(el, dict) and el.get('type')=='image_caption':
            caps.append(el.get('description'))
print('captions', caps)
print('metrics', getattr(doc, 'metrics', None))
print('timings_keys', list((doc.timings_ms or {}).keys()))
