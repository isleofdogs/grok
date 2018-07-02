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

class Downloader:
    def __init__(self, url):
        self.url = url
        self.chunksize = 1024 * 1024
        self.length = 104857610
        self.key = self._generate_hash()
        

    def _generate_hash(self):
        key_text = splittype(self.url)[1].strip('/').encode()
        key = hashlib.md5(key_text).hexdigest()
        return key

    def raw_res(self):
        res = requests.get(self.url, stream=True)
        return res

    def download(self):
        with ThreadPoolExecutor(max_workers=5) as exe:
            for item in self._bytes_ranges():
                exe.submit(item.fetch)
        
    def _bytes_ranges(self):
        starts = range(0,self.length,self.chunksize)
        ends = range(self.chunksize-1,self.length,self.chunksize)
        ranges = [Chunk(self.url, s, e, self.key) for s,e in zip_longest(starts,ends,fillvalue=self.length-1)]
        return ranges

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
        return os.path.join('parts',name)

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

    def fetch(self):
        if self.exists and self.of_correct_size:
            return STATUS['exists']

        with requests.get(self.url, headers=self.headers, stream=True) as res:
            with open(self.filename,'wb') as f:
                for chunk in res.iter_content(chunk_size=1024):
                    f.write(chunk)
        return STATUS['saved']
