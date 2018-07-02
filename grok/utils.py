import requests
import json
import os

class Downloader:
    def __init__(self, url):
        self.url = url
        
    def raw_res(self):
        res = requests.get(self.url, stream=True)
        return res

    def download(self):
        pass
        
