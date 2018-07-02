import hashlib
from urllib.parse import splittype
import requests
import json
import os
from itertools import zip_longest
from concurrent.futures import ThreadPoolExecutor

parts_dir = os.path.expanduser('~/parts')
class Downloader:
    def __init__(self, url):
        self.url = url
        self.chunk_size = 1024 * 1024
        self._res = self._make_request()
        self._fix_chunk_params()
        self._chunks = self._make_chunks()
        self.filename = self._filename()

    def _fix_chunk_params(self):
        params = {
            'url': self.url,
            'key': self._generate_hash()
        }
        Chunk.fix_params(params)

    def _filename(self):
        return os.path.join(parts_dir, 'foo')

    @property
    def size(self):
        size = int(self._res.headers['Content-Length'])
        return size

    def _generate_hash(self):
        key_text = splittype(self.url)[1].strip('/').encode()
        key = hashlib.md5(key_text).hexdigest()
        return key

    def _make_request(self):
        res = requests.get(self.url, stream=True)
        return res

    def start(self):
        print('started')
        with ThreadPoolExecutor(max_workers=5) as exe:
            for chunk in self.unfinished_chunks[0:10]:
                exe.submit(chunk.fetch)
        
    def _bytes_ranges(self):
        starts = range(0,self.size,self.chunk_size)
        ends = range(self.chunk_size-1,self.size,self.chunk_size)
        ranges = zip_longest(starts,ends,fillvalue=self.size-1)
        return ranges

    def _make_chunks(self):
        chunks = [Chunk(start, end) for start, end in self._bytes_ranges()]
        return chunks

    def __len__(self):
        return len(self._chunks)

    def __iter__(self):
        return iter(self._chunks)

    @property
    def progress(self):
        unfinished = len(self.unfinished_chunks)
        total = len(self._chunks)
        report = {
            '%':  (1-unfinished/total)*100
        }
        return report

    @property
    def unfinished_chunks(self):
        chunks = [chunk for chunk in self._chunks if not chunk.finished]
        return chunks

    def assemble_chunks(self):
        with open(self.filename,'wb') as outf:
            for chunk in self._chunks:
                with open(chunk.filename,'rb') as inf:
                    outf.write(inf.read())

class Chunk:
    def __init__(self, start, end):
        self.start = start
        self.end = end
        self.filename = self._filename()
    
    @classmethod
    def fix_params(cls, params):
        for param,val in params.items():
            setattr(cls, param, val)

    @property
    def headers(self):
        headers = {
            'Range': 'bytes={}-{}'.format(self.start, self.end)
        }
        return headers

    def _filename(self):
        name = '{}_{}_{}'.format(self.__class__.key, self.start, self.end)
        return os.path.join(parts_dir, name)

    @property
    def size_expected(self):
        return self.end - self.start + 1

    @property
    def size(self):
        return os.path.getsize(self.filename)

    @property
    def is_of_expected_size(self):
        return self.size_expected == self.size

    @property
    def exists(self):
        return os.path.isfile(self.filename)

    @property
    def finished(self):
        return self.exists and self.is_of_expected_size

    def fetch(self):
        url = self.__class__.url
        with requests.get(url, headers=self.headers, stream=True) as res:
            with open(self.filename,'wb') as f:
                for chunk in res.iter_content(chunk_size=1024):
                    f.write(chunk)
