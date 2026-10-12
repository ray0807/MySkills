"""Upload a local reference image to Cocoon; no generation or automatic retries."""
import argparse
import json
import os
from pathlib import Path
import uuid
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

ENDPOINT = 'https://mcp.boomclaws.com/v1/point/public/upload/temp-file'
MAX_BYTES = 20 * 1024 * 1024


class MissingKey(ValueError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('Upload redirect rejected; credentials were not forwarded')


def image_type(data):
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'image/png', 'png'
    if data.startswith(b'\xff\xd8\xff'):
        return 'image/jpeg', 'jpg'
    if data.startswith((b'GIF87a', b'GIF89a')):
        return 'image/gif', 'gif'
    if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        return 'image/webp', 'webp'
    if data[4:8] == b'ftyp' and data[8:12] in {b'avif', b'avis'}:
        return 'image/avif', 'avif'
    raise ValueError('Use PNG, JPEG, GIF, WebP or AVIF reference images')


def multipart(data, key, boundary):
    if not key or '\r' in key or '\n' in key:
        raise ValueError('COCOON_IMAGE_KEY is missing or invalid')
    mime, extension = image_type(data)
    head = (f'--{boundary}\r\nContent-Disposition: form-data; name="keyCode"\r\n\r\n'
            f'{key}\r\n--{boundary}\r\nContent-Disposition: form-data; name="file"; '
            f'filename="reference-{uuid.uuid4().hex}.{extension}"\r\nContent-Type: {mime}\r\n\r\n')
    return head.encode('utf-8') + data + f'\r\n--{boundary}--\r\n'.encode()


def upload(file, opener=None):
    key = os.environ.get('COCOON_IMAGE_KEY', '').strip()
    if not key:
        raise MissingKey('请填写 Cocoon AI 图片服务 Key，配置到本机 COCOON_IMAGE_KEY 环境变量后再运行。')
    path = Path(file).resolve(strict=True)
    if not path.is_file() or not 0 < path.stat().st_size <= MAX_BYTES:
        raise ValueError('Reference must be a nonempty image, at most 20 MiB')
    data = path.read_bytes()
    if len(data) > MAX_BYTES:
        raise ValueError('Reference exceeds 20 MiB')
    boundary = 'CocoonReference' + uuid.uuid4().hex
    request = Request(ENDPOINT, data=multipart(data, key, boundary), method='POST',
                      headers={'Content-Type': f'multipart/form-data; boundary={boundary}',
                               'Accept': 'application/json'})
    with (opener or build_opener(NoRedirect())).open(request, timeout=45) as response:
        result = json.load(response)
    if result.get('code') != 200 or not isinstance(result.get('data'), dict):
        raise ValueError('Upload rejected; check account and service upload settings')
    url = result['data'].get('downloadUrl')
    parsed = urlparse(url) if isinstance(url, str) else None
    if not parsed or parsed.scheme not in {'https', 'http'} or not parsed.hostname:
        raise ValueError('Upload did not return a valid reference URL')
    return {'source_file': str(path), 'reference_url': url, 'status': 'uploaded'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--file', required=True)
    parser.add_argument('--output', help='Optional local reference record JSON; excludes credentials')
    args = parser.parse_args()
    try:
        result = upload(args.file)
        content = json.dumps(result, ensure_ascii=False, indent=2)
        if args.output:
            destination = Path(args.output)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(content + '\n', encoding='utf-8')
        print(content)
    except MissingKey as error:
        parser.exit(1, f'configuration_required: {error}\n')
    except (ValueError, OSError, HTTPError, URLError) as error:
        # Avoid printing server body/request payload, which can contain keyCode.
        parser.exit(1, f'Upload failed ({type(error).__name__}); check local configuration. No automatic retry.\n')
