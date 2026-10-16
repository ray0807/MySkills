"""Offline tests; no image model or external accounts."""
import json
from pathlib import Path
import tempfile
import unittest

from batch import scan, initialize, pending, gallery


class BatchChecks(unittest.TestCase):
    def test_inventory_and_recovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            product = root / '保温杯'
            product.mkdir()
            source = product / '原图.png'
            source.write_bytes(b'fixture-only-not-an-image')
            (root / '生成结果').mkdir()
            (root / '缺图').mkdir()
            many = root / '多图'
            many.mkdir()
            for name in ('a.jpg', 'b.jpg'):
                (many / name).write_bytes(b'fixture')
            self.assertEqual({p['product']: p['status'] for p in scan(root)['products']},
                             {'保温杯': 'ready', '多图': 'choose_source', '缺图': 'missing_image'})
            output = product / '生成结果' / 'main.png'
            plan = {'batch_id': 'test', 'style': {'description': '棚光'}, 'call_budget': 2,
                    'tasks': [{'id': 'cup', 'product': '保温杯', 'source': str(source),
                               'output': str(output), 'platform': 'alibaba', 'slot': 'main'}]}
            planfile = root / 'plan.json'
            planfile.write_text(json.dumps(plan), encoding='utf-8')
            manifest = root / 'manifest.json'
            initialize(planfile, manifest)
            self.assertEqual(len(pending(manifest)['tasks']), 1)
            self.assertTrue(Path(gallery(manifest)['gallery']).is_file())
            with self.assertRaises(FileExistsError):
                initialize(planfile, manifest)
            source.write_bytes(b'changed')
            self.assertIn(str(source), pending(manifest)['changed_inputs'])
            data = json.loads(manifest.read_text(encoding='utf-8'))
            data['tasks'][0]['status'] = 'skipped'
            manifest.write_text(json.dumps(data), encoding='utf-8')
            self.assertEqual(pending(manifest)['tasks'], [])
            output.parent.mkdir()
            output.write_bytes(b'output')
            with self.assertRaises(ValueError):
                initialize(planfile, root / 'another.json')


if __name__ == '__main__':
    unittest.main()
