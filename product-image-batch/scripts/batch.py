"""Offline inventory, manifest validation and HTML preview; never calls image models."""
import argparse
import hashlib
import html
import json
from pathlib import Path

EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.avif', '.bmp', '.tif', '.tiff'}
UPLOAD_EXTENSIONS = EXTENSIONS - {'.bmp', '.tif', '.tiff'}
EXCLUDED = {'生成结果', 'output', 'outputs', 'generated', 'runtime', '__pycache__'}


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read_document(path):
    data = path.read_bytes()
    encodings = ['utf-16'] if data.startswith((b'\xff\xfe', b'\xfe\xff')) else ['utf-8-sig', 'gb18030']
    for encoding in encodings:
        try:
            return {'path': str(path), 'encoding': encoding, 'text': data.decode(encoding), 'error': None}
        except UnicodeError:
            continue
    return {'path': str(path), 'encoding': None, 'text': None,
            'error': 'Cannot decode text; please save a UTF-8 copy.'}


def scan(root):
    root = Path(root).resolve(strict=True)
    if not root.is_dir():
        raise ValueError('Input must be a directory')
    products = []
    for folder in sorted(root.iterdir()):
        if folder.is_symlink() or folder.is_junction() or not folder.is_dir() or folder.name.startswith('.') or folder.name.lower() in EXCLUDED:
            continue
        images = [p for p in sorted(folder.iterdir()) if p.is_file() and not p.is_symlink() and p.suffix.lower() in EXTENSIONS]
        documents = []
        for path in sorted(folder.iterdir()):
            if path.is_file() and not path.is_symlink() and path.suffix.lower() == '.txt':
                try:
                    documents.append(read_document(path))
                except OSError:
                    documents.append({'path': str(path), 'text': None, 'encoding': None, 'error': 'Cannot read file; check access.'})
        preferred = [p for p in images if p.stem.lower() in {'原图', 'original'}]
        selected = images[0] if len(images) == 1 else preferred[0] if len(preferred) == 1 else None
        products.append({'product': folder.name, 'directory': str(folder),
                         'images': [str(p) for p in images], 'source': str(selected) if selected else None,
                         'status': 'ready' if selected else 'choose_source' if images else 'missing_image',
                         'upload_warnings': [str(p) for p in images if p.suffix.lower() not in UPLOAD_EXTENSIONS],
                         'description_files': [d['path'] for d in documents], 'documents': documents})
    return {'root': str(root), 'products': products, 'note': 'Image decoding and visual fidelity require inspection.'}


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def initialize(plan_path, manifest):
    plan_path = Path(plan_path).resolve(strict=True)
    plan = read(plan_path)
    tasks = plan.get('tasks', [])
    if not isinstance(tasks, list) or not tasks:
        raise ValueError('Nonempty tasks list required')
    plan.setdefault('call_budget', len(tasks))
    if type(plan['call_budget']) is not int or plan['call_budget'] < len(tasks):
        raise ValueError('Nonempty tasks and call_budget >= task count required')
    extra = plan.get('authorized_extra_calls', 0)
    if type(extra) is not int or extra < 0 or plan['call_budget'] != len(tasks) + extra:
        raise ValueError('call_budget must equal task count plus explicitly authorized_extra_calls')
    if extra and not str(plan.get('extra_calls_authorization', '')).strip():
        raise ValueError('Extra calls require a record of user authorization')
    if not plan.get('batch_id') or not isinstance(plan.get('style'), dict) or not plan['style'].get('description'):
        raise ValueError('batch_id and style required')
    ids, outputs, fingerprints = set(), set(), {}

    def resolve(value, exists=False):
        p = Path(value)
        return (p if p.is_absolute() else plan_path.parent / p).resolve(strict=exists)

    for t in tasks:
        for key in ('id', 'product', 'source', 'platform', 'slot', 'output'):
            if not isinstance(t.get(key), str) or not t[key].strip():
                raise ValueError(f'Task requires {key}')
        source, output = resolve(t['source'], True), resolve(t['output'])
        if not source.is_file() or source.suffix.lower() not in UPLOAD_EXTENSIONS:
            raise ValueError('Source format must support upload; use PNG/JPEG/WebP/GIF/AVIF')
        if t['id'] in ids or str(output).casefold() in outputs or output.exists():
            raise ValueError('Duplicate task/output or existing output; use a new version')
        # Never permit an output to overwrite any supplied reference/source.
        ids.add(t['id'])
        outputs.add(str(output).casefold())
        t.update(source=str(source), output=str(output), status='pending', attempts=0,
                 source_sha256=digest(source), prompt='', artifact=None, notes='')
        t['references'] = [str(resolve(v, True)) for v in t.get('references', [])]
        t['description_files'] = [str(resolve(v, True)) for v in t.get('description_files', [])]
        for v in [t['source'], *t['references'], *t['description_files']]:
            fingerprints[v] = digest(Path(v))
    plan['style']['references'] = [str(resolve(v, True)) for v in plan['style'].get('references', [])]
    for v in plan['style']['references']:
        fingerprints[v] = digest(Path(v))
    if outputs.intersection(v.casefold() for v in fingerprints):
        raise ValueError('Output conflicts with an input')
    for t in tasks:
        t.update(provider='cocoon', taskId=None, resultUrl=None, pointsCost=None,
                 reference_urls=[], quality_status='unchecked')
    plan.update(schema_version=2, calls_used=0, input_sha256=fingerprints)
    destination = Path(manifest).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('x', encoding='utf-8') as stream:
        json.dump(plan, stream, ensure_ascii=False, indent=2)
    return {'manifest': str(destination), 'tasks': len(tasks)}


def pending(manifest):
    plan = read(manifest)
    changed = [v for v, sha in plan['input_sha256'].items() if not Path(v).is_file() or digest(Path(v)) != sha]
    return {'changed_inputs': changed, 'calls_used': plan['calls_used'], 'call_budget': plan['call_budget'],
            'tasks': [dict(t, output_exists=Path(t['output']).is_file(), next_action=recovery_action(t, bool(changed))) for t in plan['tasks']
                      if t['status'] != 'skipped' and (t['status'] not in {'success', 'needs_review'} or not Path(t['output']).is_file())],
            'note': 'Never resubmit unknown requests; resume taskId polling or save resultUrl first. Changed inputs require a new plan.'}


def recovery_action(task, changed=False):
    if changed:
        return 'review_changed_inputs'
    if task.get('resultUrl'):
        return 'save_or_inspect_existing_result'
    if task.get('taskId'):
        return 'query_existing_task'
    if task['status'] in {'submitting', 'submission_unknown', 'generating'}:
        return 'verify_service_history_do_not_resubmit'
    if task['status'] == 'pending' and task.get('attempts', 0) == 0:
        return 'analyze_before_first_submission'
    return 'review_record_do_not_auto_resubmit'


def gallery(manifest):
    plan = read(manifest)
    esc = lambda value: html.escape(str(value), quote=True)
    cards = []
    for t in plan['tasks']:
        pictures = []
        for label, value in [('原图', t['source']), ('生成图', t['output'])]:
            path = Path(value)
            if path.is_file():
                uri = esc(path.resolve().as_uri())
                pictures.append(f'<figure><a href="{uri}"><img loading="lazy" src="{uri}" alt="{label}"></a><figcaption>{label}</figcaption></figure>')
        link = ''
        url = t.get('resultUrl') or ''
        if url.startswith(('https://', 'http://')):
            link = f'<p><a href="{esc(url)}" rel="noreferrer">服务原始结果</a> · taskId: {esc(t.get("taskId") or "")}</p>'
        cards.append(f'<article><h2>{esc(t["product"])} · {esc(t["platform"])} · {esc(t["slot"])}</h2><p>{esc(t["status"])} — {esc(t.get("notes", ""))}</p>{link}<div>{"".join(pictures)}</div></article>')
    target = Path(manifest).resolve().with_suffix('.html')
    document = '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>产品图批次预览</title><style>body{font:16px system-ui;margin:24px;background:#f3f4f6}article{background:white;padding:20px;margin-bottom:20px}article div{display:flex;flex-wrap:wrap}figure{margin:8px}img{width:260px;height:260px;object-fit:contain}h2{font-size:18px}</style><h1>产品图批次预览</h1>' + ''.join(cards) + '</html>'
    target.write_text(document, encoding='utf-8')
    return {'gallery': str(target)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('scan').add_argument('root')
    init = sub.add_parser('init')
    init.add_argument('plan')
    init.add_argument('--manifest', required=True)
    for command in ('pending', 'gallery'):
        sub.add_parser(command).add_argument('manifest')
    args = parser.parse_args()
    if args.command == 'scan':
        result = scan(args.root)
    elif args.command == 'init':
        result = initialize(args.plan, args.manifest)
    else:
        result = globals()[args.command](args.manifest)
    print(json.dumps(result, ensure_ascii=False, indent=2))
