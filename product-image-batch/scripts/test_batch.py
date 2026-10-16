"""Offline tests; no image model or external accounts."""
import json
from pathlib import Path
import tempfile
import unittest

from batch import scan, initialize, pending, gallery, recovery_action


class BatchChecks(unittest.TestCase):
    def test_recovery_does_not_resubmit(self):
        self.assertEqual(recovery_action({'status': 'submission_unknown'}), 'verify_service_history_do_not_resubmit')
        self.assertEqual(recovery_action({'status': 'submitted', 'taskId': 't1'}), 'query_existing_task')
        self.assertEqual(recovery_action({'status': 'success', 'resultUrl': 'https://example.com/a.png'}), 'save_or_inspect_existing_result')
        self.assertEqual(recovery_action({'status': 'failed', 'attempts': 1}), 'review_record_do_not_auto_resubmit')

    def test_all_product_text_documents(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            product = root / '产品'
            product.mkdir()
            (product / '尺寸.txt').write_text('高度10厘米', encoding='utf-8-sig')
            (product / '卖点.TXT').write_text('保留商标', encoding='gb18030')
            (product / '包装.txt').write_text('数量一个', encoding='utf-16')
            (product / '损坏.txt').write_bytes(b'\xff')
            nested = product / '生成结果'
            nested.mkdir()
            (nested / '不要读取.txt').write_text('旧资料', encoding='utf-8')
            item = scan(root)['products'][0]
            self.assertEqual(len(item['description_files']), 4)
            documents = {Path(d['path']).name: d for d in item['documents']}
            self.assertEqual(documents['尺寸.txt']['text'], '高度10厘米')
            self.assertEqual(documents['卖点.TXT']['text'], '保留商标')
            self.assertEqual(documents['包装.txt']['text'], '数量一个')
            self.assertIsNotNone(documents['损坏.txt']['error'])

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
            plan = {'batch_id': 'test', 'style': {'description': '棚光'}, 'call_budget': 1,
                    'tasks': [{'id': 'cup', 'product': '保温杯', 'source': str(source),
                               'output': str(output), 'platform': 'alibaba', 'slot': 'main'}]}
            planfile = root / 'plan.json'
            planfile.write_text(json.dumps(plan), encoding='utf-8')
            manifest = root / 'manifest.json'
            plan['call_budget'] = 2
            planfile.write_text(json.dumps(plan), encoding='utf-8')
            with self.assertRaises(ValueError):
                initialize(planfile, manifest)
            plan['call_budget'] = 1
            planfile.write_text(json.dumps(plan), encoding='utf-8')
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
