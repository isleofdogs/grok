import hashlib
from urllib.parse import splittype
import requests
import json
import os
from itertools import zip_longest

STATUS = {
    'saved': 'S',
    'exists': 'E',
}
parts_dir = os.path.expanduser('~/parts')
class Downloader:
    def __init__(self, url):
        self.url = url
        self.chunksize = 1024 * 1024
        self._res = self._raw_res()
        self.key = self._generate_hash()
        self._chunks = self._make_chunks()
        

    @property
    def size(self):
        size = int(self._res.headers['Content-Length'])
        return size

    def _generate_hash(self):
        key_text = splittype(self.url)[1].strip('/').encode()
        key = hashlib.md5(key_text).hexdigest()
        return key

    def _raw_res(self):
        res = requests.get(self.url, stream=True)
        return res

    def download(self):
        with ThreadPoolExecutor(max_workers=5) as exe:
            for item in self._bytes_ranges():
                exe.submit(item.fetch)
        
    def _bytes_ranges(self):
        starts = range(0,self.size,self.chunksize)
        ends = range(self.chunksize-1,self.size,self.chunksize)
        ranges = zip_longest(starts,ends,fillvalue=self.size-1)
        return ranges

    def _make_chunks(self):
        chunks = [Chunk(self.url, start, end, self.key) for start, end in self._bytes_ranges()]
        return chunks

    def __len__(self):
        return len(self._chunks)

    def __iter__(self):
        return iter(self._chunks)

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

class Chunk:
    def __init__(self, url, start, end, key):
        self.url = url
        self.start = start
        self.end = end
        self.key = key
        self.filename = self._filename()
    
    @property
    def headers(self):
        headers = {
            'Range': 'bytes={}-{}'.format(self.start, self.end)
        }
        return headers

    def _filename(self):
        name = '{}_{}_{}'.format(self.key, self.start, self.end)
        return os.path.join(parts_dir, name)

    @property
    def size_expected(self):
        return self.end - self.start + 1

    @property
    def size_present(self):
        return os.path.getsize(self.filename)

    @property
    def of_correct_size(self):
        return self.size_expected == self.size_present

    @property
    def exists(self):
        return os.path.isfile(self.filename)

    @property
    def finished(self):
        return self.exists and self.of_correct_size

    def fetch(self):
        with requests.get(self.url, headers=self.headers, stream=True) as res:
            with open(self.filename,'wb') as f:
                for chunk in res.iter_content(chunk_size=1024):
                    f.write(chunk)
        return STATUS['saved']
