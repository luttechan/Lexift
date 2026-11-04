"""Read-only indexed dictionary with bounded caches instead of Python object graphs."""
import hashlib,json,sqlite3
from collections import OrderedDict

class Prefixes:
    def __init__(self,store):self.connection=store.connection;self.cache=OrderedDict()
    def __contains__(self,tokens):
        key=' '.join(tokens)
        if key in self.cache:self.cache.move_to_end(key);return self.cache[key]
        found=self.connection.execute('SELECT 1 FROM prefixes WHERE reading=?',(key,)).fetchone() is not None
        self.cache[key]=found
        if len(self.cache)>2048:self.cache.popitem(last=False)
        return found

class CompactDictionary:
    def __init__(self,path,source):
        self.connection=sqlite3.connect(path.resolve().as_uri()+'?mode=ro&immutable=1',uri=True)
        self.connection.execute('PRAGMA cache_size=-512')
        self.connection.execute('PRAGMA mmap_size=0')
        self.meta={key:json.loads(value) for key,value in self.connection.execute('SELECT key,value FROM metadata')}
        with source.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
        if self.meta['source_sha256']!=digest:self.connection.close();raise ValueError('Dictionary index is stale')
        self.cache=OrderedDict();self.prefixes=Prefixes(self)

    def get(self,tokens,default=()):
        key=' '.join(tokens)
        if key not in self.cache:
            rows=tuple(self.connection.execute('SELECT text,weight FROM entries WHERE reading=? ORDER BY rank',(key,)))
            self.cache[key]=rows
            if len(self.cache)>256:self.cache.popitem(last=False)
        else:self.cache.move_to_end(key)
        return self.cache[key] or default

    def __getitem__(self,tokens):
        value=self.get(tokens)
        if not value:raise KeyError(tokens)
        return value

    def __contains__(self,tokens):return bool(self.get(tokens))

    def close(self):
        self.cache.clear();self.prefixes.cache.clear();self.connection.close()
