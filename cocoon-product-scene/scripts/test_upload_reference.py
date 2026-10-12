"""Offline upload contract checks; never contacts the live service."""
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from upload_reference import ENDPOINT, image_type, multipart, upload


class Checks(unittest.TestCase):
    def test_mime_and_multipart(self):
        image = b'\x89PNG\r\n\x1a\nexample'
        self.assertEqual(image_type(image), ('image/png', 'png'))
        with self.assertRaises(ValueError):
            image_type(b'not an image')
        body = multipart(image, 'offline-test-key', 'boundary')
        self.assertIn(b'name="keyCode"\r\n\r\noffline-test-key', body)
        self.assertIn(b'name="file";', body)
        self.assertIn(image, body)
        self.assertTrue(body.endswith(b'--boundary--\r\n'))

    def test_upload_response_and_no_secret_in_result(self):
        calls = []

        class Opener:
            def open(self, request, timeout):
                calls.append(request)
                return io.BytesIO(json.dumps({'code': 200, 'data': {
                    'downloadUrl': 'https://example.com/reference.png'}}).encode())

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'reference.png'
            path.write_bytes(b'\x89PNG\r\n\x1a\nexample')
            with patch.dict(os.environ, {'COCOON_IMAGE_KEY': 'offline-test-key'}):
                result = upload(path, Opener())
            self.assertEqual(result['reference_url'], 'https://example.com/reference.png')
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0].full_url, ENDPOINT)
            self.assertNotIn('offline-test-key', json.dumps(result))

    def test_failure_no_retry_and_missing_key_no_request(self):
        calls = []

        class Opener:
            def open(self, request, timeout):
                calls.append(request)
                return io.BytesIO(b'{"code":500,"data":null}')

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'reference.png'
            path.write_bytes(b'\x89PNG\r\n\x1a\nexample')
            with patch.dict(os.environ, {'COCOON_IMAGE_KEY': ''}):
                with self.assertRaises(ValueError):
                    upload(path, Opener())
            self.assertEqual(len(calls), 0)
            with patch.dict(os.environ, {'COCOON_IMAGE_KEY': 'offline-test-key'}):
                with self.assertRaises(ValueError):
                    upload(path, Opener())
            self.assertEqual(len(calls), 1)


if __name__ == '__main__':
    unittest.main()
