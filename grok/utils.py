import hashlib
from urllib.parse import splittype
import requests
import json
import os
from itertools import zip_longest
from concurrent.futures import ThreadPoolExecutor
import pickle
import glob
from collections.abc import MutableMapping

parts_dir = os.path.expanduser('~/parts')
class Manager(MutableMapping):
    def __init__(self, parts_dir=parts_dir):
        self.parts_dir = parts_dir
        self.name_ext = '.grok'
        self.name_pat = os.path.join(self.parts_dir,'*{}'.format(self.name_ext))

    def __iter__(self):
        return (path_to_key(path) for path in self.filenames)

    @property
    def filenames(self):
        return glob.glob(self.name_pat)
        
    def __len__(self):
        return len(self.filenames)

    def __setitem__(self, key, download):
        path = self.key_to_path(key)
        with open(path, 'wb') as f:
            pickle.dump(download, f)

        chunks_dir = self._chunks_dir(key)
        os.makedirs(chunks_dir, exist_ok=True)

    def _chunks_dir(self, key):
        return os.path.join(self.parts_dir,key)

    def __getitem__(self, key):
        path = self.key_to_path(key)
        with open(path, 'rb') as f:
            download = pickle.load(f)
        return download

    def __delitem__(self, key):
        path = self.key_to_path(key)
        os.remove(path)
        chunks_dir = self._chunks_dir(key)
        os.rmdir(chunks_dir)

    def key_to_path(self, key):
        path = os.path.join(self.parts_dir,'{}{}'.format(key,self.name_ext))
        return path

    def path_to_key(self, path):
        key = os.path.basename(path).rstrip(self.name_ext)
        return key

class Download:
    def __init__(self, url, key):
        self.url = url
        self.key = key
        self.chunk_size = 1024 * 1024
        self._res = self._make_request()
        self._chunks = self._make_chunks()
        self.filename = self._filename()

    def _path(self, start, end):
        name = '{}-{}'.format(start, end)
        path = os.path.join(parts_dir, self.key, name)
        return path

    def __getitem__(self, index):
        return self._chunks[index]

    def _make_chunks(self):
        chunks = [
            Chunk(start, end, self._path(start, end))
            for start,end in self._ranges()
        ]
        return chunks

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
        res = requests.head(self.url)
        return res

    def start(self):
        print('started')
        with ThreadPoolExecutor(max_workers=5) as exe:
            for chunk in self:
                if chunk.finished:
                    continue
                exe.submit(chunk.fetch, url=self.url)
        
    def _ranges(self):
        starts = range(0,self.size,self.chunk_size)
        ends = range(self.chunk_size-1,self.size,self.chunk_size)
        ranges = zip_longest(starts,ends,fillvalue=self.size-1)
        return ranges

    def __len__(self):
        return len(self._chunks)

    @property
    def progress(self):
        size = sum(chunk.size for chunk in self)
        report = {
            '%':  size/self.size*100
        }
        return report

    def assemble_chunks(self):
        with open(self.filename,'wb') as outf:
            for chunk in self._chunks:
                with open(chunk.path,'rb') as inf:
                    outf.write(inf.read())

class Chunk:
    def __init__(self, start, end, path):
        self.start = start
        self.end = end
        self.path = path
    
    @property
    def headers(self):
        headers = {
            'Range': 'bytes={}-{}'.format(self.start, self.end)
        }
        return headers

    @property
    def size_expected(self):
        return self.end - self.start + 1

    @property
    def size(self):
        return os.path.getsize(self.path)

    @property
    def is_of_expected_size(self):
        return self.size_expected == self.size

    @property
    def exists(self):
        return os.path.isfile(self.path)

    @property
    def finished(self):
        return self.exists and self.is_of_expected_size

    def fetch(self, url):
        with open(self.path, 'wb') as f,\
        requests.get(url, headers=self.headers, stream=True) as res:
            for chunk in res.iter_content(chunk_size=1024):
                f.write(chunk)
