import requests
import json
import os
from itertools import zip_longest

class Downloader:
    def __init__(self, url):
        self.url = url
        self.chunksize = 1024 * 1024
        self.length = 104857610
        
    def raw_res(self):
        res = requests.get(self.url, stream=True)
        return res

    def download(self):
        pass
        
    def _bytes_ranges(self):
        starts = range(0,self.length,self.chunksize)
        ends = range(self.chunksize-1,self.length,self.chunksize)
        ranges = [{'Range': '{}-{}'.format(s,e)} for s,e in zip_longest(starts,ends,fillvalue=self.length-1)]
        return ranges
