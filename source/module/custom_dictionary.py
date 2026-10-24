"""Small, explicit pronunciation overrides, stored separately from input history."""
import json
import unicodedata

KEY='dictionary/entries_json'
MAX_ENTRIES=1000


def normalize(keyword):
    return unicodedata.normalize('NFC',keyword.strip())


def validate(entries):
    if not isinstance(entries,list) or len(entries)>MAX_ENTRIES:
        raise ValueError('사전은 최대 1,000개까지 저장할 수 있습니다.')
    result=[];seen=set()
    for entry in entries:
        if not isinstance(entry,dict):
            raise ValueError('키워드와 대치할 텍스트를 입력하세요.')
        keyword=normalize(str(entry.get('keyword','')))
        text=str(entry.get('text','')).strip()
        lang=entry.get('language')
        if (not keyword or len(keyword)>64 or not any('가'<=c<='힣' for c in keyword)
                or any(not ('가'<=c<='힣' or c=='-') for c in keyword)):
            raise ValueError('키워드는 한글과 -로 64자 이내로 입력하세요.')
        if not text or len(text)>4096 or '\x00' in text or lang not in ('ja','zh'):
            raise ValueError('대치할 텍스트와 언어를 확인하세요.')
        identity=(lang,keyword)
        if identity in seen:
            raise ValueError('같은 언어에 동일한 키워드가 있습니다.')
        seen.add(identity);result.append(dict(keyword=keyword,text=text,language=lang))
    return result


class CustomDictionary:
    def __init__(self,store):
        self.store=store;self.entries=[];self.index={}
        try:
            entries=json.loads(store.value(KEY,'[]',str))
            self._install(validate(entries))
        except (ValueError,TypeError):
            # Never rewrite or destroy malformed user data during startup.
            self.load_error=True
        else:
            self.load_error=False

    def _install(self,entries):
        self.entries=entries
        self.index={(e['language'],e['keyword']):e['text'] for e in entries}

    def replace(self,entries):
        entries=validate(entries)
        old=self.store.value(KEY,'[]',str)
        self.store.setValue(KEY,json.dumps(entries,ensure_ascii=False,separators=(',',':')))
        self.store.sync()
        status=self.store.status()
        if getattr(status,'value',status)!=0:
            self.store.setValue(KEY,old)
            raise OSError('사전을 저장하지 못했습니다.')
        self._install(entries);self.load_error=False

    def lookup(self,language,keyword):
        return self.index.get((language,normalize(keyword)))

    def merge(self,language,source,data):
        text=self.lookup(language,source)
        if text is None:
            return data
        values=data.get('candidates',[]);readings=data.get('readings',[])
        remaining=[(value,readings[n] if n<len(readings) else data.get('kana',source))
                   for n,value in enumerate(values) if value!=text][:19]
        return dict(data,source=source,kana=data.get('kana') or source,
                    candidates=[text]+[v for v,_ in remaining],
                    readings=[source]+[r for _,r in remaining],custom=True)
