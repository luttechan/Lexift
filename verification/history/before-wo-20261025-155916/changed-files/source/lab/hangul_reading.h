#pragma once
#include <string>
#include <vector>
#include <utility>
#include <algorithm>

namespace reading {
struct Result {
    std::wstring kana, romaji, note, error;
    std::vector<std::wstring> alternatives;
    bool ok() const { return error.empty() && !kana.empty(); }
};
inline std::wstring compose(const std::wstring& s) {
    std::wstring out;
    for(size_t i=0;i<s.size();i++) {
        unsigned c=s[i];
        if(c>=0x1100 && c<=0x1112 && i+1<s.size() && s[i+1]>=0x1161 && s[i+1]<=0x1175) {
            unsigned syllable=0xac00+(c-0x1100)*588+(s[++i]-0x1161)*28;
            if(i+1<s.size() && s[i+1]>=0x11a8 && s[i+1]<=0x11c2) syllable+=s[++i]-0x11a7;
            out+=wchar_t(syllable);
        } else if(c>=0xac00 && c<=0xd7a3 && (c-0xac00)%28==0 && i+1<s.size() && s[i+1]>=0x11a8 && s[i+1]<=0x11c2) {
            out+=wchar_t(c+s[++i]-0x11a7);
        } else out+=wchar_t(c);
    }
    return out;
}
inline std::wstring mora(int l,int v) {
    // Columns a/i/u/e/o; tense consonants are common Korean spellings of the
    // same Japanese onset. They do not imply a preceding small tsu.
    static const wchar_t* base[19][5]={
        {L"が",L"ぎ",L"ぐ",L"げ",L"ご"},{L"か",L"き",L"く",L"け",L"こ"},
        {L"な",L"に",L"ぬ",L"ね",L"の"},{L"だ",L"でぃ",L"どぅ",L"で",L"ど"},
        {L"た",L"てぃ",L"とぅ",L"て",L"と"},{L"ら",L"り",L"る",L"れ",L"ろ"},
        {L"ま",L"み",L"む",L"め",L"も"},{L"ば",L"び",L"ぶ",L"べ",L"ぼ"},
        {L"ぱ",L"ぴ",L"ぷ",L"ぺ",L"ぽ"},{L"さ",L"し",L"す",L"せ",L"そ"},
        {L"さ",L"し",L"す",L"せ",L"そ"},{L"あ",L"い",L"う",L"え",L"お"},
        {L"ざ",L"じ",L"ず",L"ぜ",L"ぞ"},{L"ざ",L"じ",L"ず",L"ぜ",L"ぞ"},
        {L"ちゃ",L"ち",L"ちゅ",L"ちぇ",L"ちょ"},{L"か",L"き",L"く",L"け",L"こ"},
        {L"た",L"てぃ",L"とぅ",L"て",L"と"},{L"ぱ",L"ぴ",L"ぷ",L"ぺ",L"ぽ"},
        {L"は",L"ひ",L"ふ",L"へ",L"ほ"}};
    static const wchar_t* stems[19]={L"ぎ",L"き",L"に",L"で",L"て",L"り",L"み",L"び",L"ぴ",L"し",L"し",L"",L"じ",L"じ",L"ち",L"き",L"て",L"ぴ",L"ひ"};
    if(v==2 || v==6 || v==12 || v==17) { // ya / yeo / yo / yu
        const wchar_t* small=v==2?L"ゃ":v==17?L"ゅ":L"ょ";
        if(l==11) return v==2?L"や":v==17?L"ゆ":L"よ";
        return std::wstring(stems[l])+small;
    }
    if(v==3 || v==7) return l==11?L"いぇ":std::wstring(stems[l])+L"ぇ";
    if(v==9) return l==11?L"わ":std::wstring(base[l][2])+L"ぁ";
    if(v==10 || v==11 || v==15) return std::wstring(base[l][2])+L"ぇ";
    if(v==14) return std::wstring(base[l][2])+L"ぉ";
    if(v==16) return std::wstring(base[l][2])+L"ぃ";
    if(v==19) return std::wstring(base[l][2])+L"い";
    if(v==18 && l==14) return L"つ"; // 츠
    int column=v==20?1:(v==13 || v==18)?2:(v==1 || v==5)?3:(v==4 || v==8)?4:0;
    return base[l][column];
}
inline std::wstring romanize(const std::wstring& kana) {
    static const std::vector<std::pair<std::wstring,std::wstring>> rows={
        {L"あいうえお",L""},{L"かきくけこ",L"k"},{L"がぎぐげご",L"g"},
        {L"さしすせそ",L"s"},{L"ざじずぜぞ",L"z"},{L"たちつてと",L"t"},
        {L"だぢづでど",L"d"},{L"なにぬねの",L"n"},{L"はひふへほ",L"h"},
        {L"ばびぶべぼ",L"b"},{L"ぱぴぷぺぽ",L"p"},{L"まみむめも",L"m"},{L"らりるれろ",L"r"}};
    std::wstring out;
    for(wchar_t raw:kana) {
        wchar_t c=raw>=0x30a1 && raw<=0x30f6?raw-0x60:raw;
        bool found=false;
        for(const auto& row:rows) {
            auto index=row.first.find(c);
            if(index!=std::wstring::npos) {
                if(c==L'し') out+=L"shi";
                else if(c==L'ち') out+=L"chi";
                else if(c==L'つ') out+=L"tsu";
                else if(c==L'じ') out+=L"ji";
                else if(c==L'ふ') out+=L"fu";
                else out+=row.second+std::wstring(1,L"aiueo"[index]);
                found=true;break;
            }
        }
        if(found) continue;
        switch(c) {
            case L'や':out+=L"ya";break;case L'ゆ':out+=L"yu";break;case L'よ':out+=L"yo";break;
            case L'わ':out+=L"wa";break;case L'を':out+=L"wo";break;case L'ん':out+=L"n'";break;
            case L'っ':out+=L"xtsu";break;case L'ゃ':out+=L"xya";break;case L'ゅ':out+=L"xyu";break;case L'ょ':out+=L"xyo";break;
            case L'ぁ':out+=L"xa";break;case L'ぃ':out+=L"xi";break;case L'ぅ':out+=L"xu";break;case L'ぇ':out+=L"xe";break;case L'ぉ':out+=L"xo";break;
            case L'ゔ':out+=L"vu";break;case L'ー':out+=L"-";break;
            case L'。':out+=L".";break;case L'、':out+=L",";break;
            default:return L"";
        }
    }
    return out;
}
struct Spelling { std::wstring text; int cost; };
inline void prune(std::vector<Spelling>& paths) {
    std::stable_sort(paths.begin(),paths.end(),[](const Spelling& a,const Spelling& b){return a.cost<b.cost;});
    std::vector<Spelling> unique;
    for(auto& path:paths) {
        bool seen=false;for(auto& old:unique)if(old.text==path.text){seen=true;break;}
        if(!seen)unique.push_back(path);
        if(unique.size()==16)break;
    }
    paths=std::move(unique);
}
// Canonical stems cover their inflections without listing every conjugated word.
inline std::wstring canonicalSpelling(std::wstring text) {
    static const std::vector<std::pair<std::wstring,std::wstring>> stems={
        {L"ちじま",L"ちぢま"},{L"ちじみ",L"ちぢみ"},{L"ちじめ",L"ちぢめ"},
        {L"ちじれ",L"ちぢれ"},{L"ちじこま",L"ちぢこま"},
        {L"つず",L"つづ"},{L"ものずく",L"ものづく"},{L"てずく",L"てづく"},
        {L"おねいさん",L"おねえさん"},{L"おねいちゃん",L"おねえちゃん"}};
    for(auto& item:stems) {
        size_t at=0;
        while((at=text.find(item.first,at))!=std::wstring::npos) {
            text.replace(at,item.first.size(),item.second);at+=item.second.size();
        }
    }
    // 大きい/大きく/大きな share a stem, but 応急/王旗 do not.
    for(size_t at=0;(at=text.find(L"おうき",at))!=std::wstring::npos;at+=3) {
        if(at+3<text.size() && std::wstring(L"いくけさなめ").find(text[at+3])!=std::wstring::npos)
            text.replace(at,3,L"おおき");
    }
    // Only known word boundaries receive a preferred particle spelling.
    for(auto word:{L"わたし",L"あなた",L"かれ",L"かのじょ",L"これ",L"それ",L"あれ",L"きょう"}) {
        auto key=std::wstring(word)+L"わ";size_t at=0;
        while((at=text.find(key,at))!=std::wstring::npos) {
            if(at==0)text[at+key.size()-1]=L'は';
            at+=key.size();
        }
    }
    for(size_t at=1;at+1<text.size();at++) {
        if(text[at]!=L'お' && text[at]!=L'え')continue;
        bool predicate=false;
        for(auto stem:{L"べんきょう",L"よみ",L"よむ",L"かき",L"かく",L"たべ",L"のみ",L"のむ",
                       L"いき",L"いく",L"いっ",L"かえり",L"かえる"}) {
            auto tail=std::wstring(stem);
            if(text.compare(at+1,tail.size(),tail)==0){predicate=true;break;}
        }
        if(predicate)text[at]=text[at]==L'お'?L'を':L'へ';
    }
    return text;
}
inline Result convert(const std::wstring& input) {
    Result out;
    if(input.size()>256) {out.error=L"한 번에 256자까지 입력해 주세요.";return out;}
    auto text=compose(input);
    // Small, explicit pronunciation spelling corrections, not translations.
    // Everything outside these spellings uses syllable rules, not a word list.
    static const std::vector<std::pair<std::wstring,std::wstring>> lexicon={
        {L"곤니치와",L"こんにちは"},{L"콘니치와",L"こんにちは"},
        {L"곤니찌와",L"こんにちは"},{L"콘니찌와",L"こんにちは"},
        {L"아리가토",L"ありがとう"},{L"아리가또",L"ありがとう"},
        {L"고자이마스",L"ございます"},{L"도-쿄-",L"とうきょう"},{L"도쿄",L"とうきょう"},{L"토쿄",L"とうきょう"},
        {L"오하요",L"おはよう"},
        {L"모노즈쿠리",L"ものづくり"},{L"마치즈쿠리",L"まちづくり"},
        {L"히토즈쿠리",L"ひとづくり"},{L"츠즈쿠",L"つづく"},{L"츠즈미",L"つづみ"},
        {L"치지무",L"ちぢむ"},{L"치지레",L"ちぢれ"},{L"하나지",L"はなぢ"}};
    bool corrected=false,approximate=false;
    struct Alias {size_t at,length;std::wstring text;int family=0;int cost=3;};
    std::vector<Alias> aliases;
    std::vector<size_t> boundaries;
    for(size_t i=0;i<text.size();i++) {
        wchar_t c=text[i];
        if(c==L' ' || c==L'\t' || c==L'\n' || c==L'\r') {boundaries.push_back(out.kana.size());continue;}
        bool matched=false;
        for(const auto& entry:lexicon) {
            if(text.compare(i,entry.first.size(),entry.first)==0) {
                auto end=i+entry.first.size();
                // A conventional spelling may already supply the final long
                // vowel (ありがとう, おはよう, とうきょう). Consume one
                // explicitly repeated equivalent, rather than doubling it.
                if(end<text.size() && entry.second.size()>1) {
                    auto vowel=entry.second.back();
                    bool longEnding=vowel==L'う' || vowel==L'い';
                    if(longEnding && (text[end]==L'-' || text[end]==L'ー' ||
                       (vowel==L'う' && text[end]==L'우') || (vowel==L'い' && text[end]==L'이')))end++;
                }
                out.kana+=entry.second;i=end-1;corrected=matched=true;break;
            }
        }
        if(matched) continue;
        if(c>=0xac00 && c<=0xd7a3) {
            unsigned n=c-0xac00;int l=n/588,v=(n%588)/28,t=n%28;
            auto syllable=mora(l,v);size_t at=out.kana.size();
            // Common Korean transcriptions are alternatives, never global replacements.
            if(l==13 && v==18) {syllable=L"つ";aliases.push_back({at,1,L"ず",6});}
            if(l==10 && v==18)aliases.push_back({at,1,L"つ",6,2}); // 쓰: ス or ツ
            if(l==0 || l==3 || l==7) {
                auto other=mora(l==0?15:l==3?16:17,v);
                if(other!=syllable)aliases.push_back({at,syllable.size(),other});
            }
            int column=v==20?1:(v==13 || v==18)?2:(v==1 || v==5)?3:(v==4 || v==8)?4:v==0?0:-1;
            if(column>=0 && (l==7 || l==17)) {
                static const wchar_t* f[]={L"ふぁ",L"ふぃ",L"ふ",L"ふぇ",L"ふぉ"};
                static const wchar_t* vv[]={L"ゔぁ",L"ゔぃ",L"ゔ",L"ゔぇ",L"ゔぉ"};
                aliases.push_back({at,syllable.size(),l==17?f[column]:vv[column],l==17?1:2,2});
            }
            if((l==7 || l==17) && (v==2 || v==6 || v==12 || v==17)) {
                auto small=v==2?L"ゃ":v==17?L"ゅ":L"ょ";
                aliases.push_back({at,syllable.size(),std::wstring(l==17?L"ふ":L"ゔ")+small,l==17?1:2,2});
            }
            if((l==12 || l==13) && column>=0 && column!=1) {
                static const wchar_t* j[]={L"じゃ",L"じ",L"じゅ",L"じぇ",L"じょ"};
                aliases.push_back({at,syllable.size(),j[column],3,2});
            }
            bool wordInitial=at==0 || (!boundaries.empty() && boundaries.back()==at);
            if(wordInitial && (l==12 || l==13)) {
                // The Korean transcription table uses 지/자/주/조 for
                // word-initial チ/チャ/チュ/チョ as well as voiced sounds.
                if(column==1)aliases.push_back({at,syllable.size(),L"ち",5,2});
                else if(column==0 || column==2 || column==4) {
                    static const wchar_t* ch[]={L"ちゃ",L"ち",L"ちゅ",L"ちぇ",L"ちょ"};
                    aliases.push_back({at,syllable.size(),ch[column],5,2});
                } else if(v==2 || v==6 || v==12 || v==17) {
                    auto small=v==2?L"ゃ":v==17?L"ゅ":L"ょ";
                    aliases.push_back({at,syllable.size(),std::wstring(L"ち")+small,5,2});
                }
            }
            if((l==9 || l==10 || l==12 || l==13) && v==16)
                aliases.push_back({at,syllable.size(),(l==9 || l==10)?L"し":L"じ",3,2});
            if(l==3 && (v==2 || v==6 || v==12 || v==17)) {
                auto small=v==2?L"ゃ":v==17?L"ゅ":L"ょ";
                aliases.push_back({at,syllable.size(),std::wstring(L"じ")+small,3,2});
            }
            out.kana+=syllable;
            if(t==4 || t==16 || t==21) out.kana+=L"ん";
            else if(t==8) {
                // Korean ㄹ+ㄹ transcriptions (바이올린) can represent one
                // Japanese r onset. Keep the uncontracted reading as well.
                if(i+1<text.size() && text[i+1]>=0xac00 && text[i+1]<=0xd7a3 &&
                   (text[i+1]-0xac00)/588==5)
                    aliases.push_back({out.kana.size(),1,L"",4,2});
                out.kana+=L"る";approximate=true;
            }
            else if(t) {out.kana+=L"っ";approximate=true;}
            if(v==4 || v==18 || v==19 || v==11) approximate=true;
        } else if(c>=0x3041 && c<=0x3096) out.kana+=c;
        else if(c>=0x30a1 && c<=0x30f6) out.kana+=wchar_t(c-0x60);
        else if(c==L'-' || c==L'ー') out.kana+=L"ー";
        else if(c==L'.' || c==L'。') out.kana+=L"。";
        else if(c==L',' || c==L'、') out.kana+=L"、";
        else {
            out.error=(c>=0x1100 && c<=0x11ff)||(c>=0x3130 && c<=0x318f)?L"조합 중인 자음을 완성한 뒤 변환해 주세요.":L"한글 발음 또는 일본어 독음을 입력해 주세요. 영문은 아래 일본어 입력란에서 직접 입력할 수 있습니다.";
            out.kana.clear();return out;
        }
    }
    auto literal=out.kana;
    bool koreanDash=false;
    for(auto c:text)if(c>=0xac00 && c<=0xd7a3)koreanDash=true;
    // Korean '-' denotes a long vowel, not necessarily the katakana ー.
    // Common borrowed coffee spelling keeps its established literal reading.
    if(koreanDash) {
        std::wstring expanded;
        for(size_t pos=0;pos<literal.size();pos++) {
            auto c=literal[pos];
            bool coffee=(pos>=1 && literal.compare(pos-1,4,L"こーひー")==0) ||
                        (pos>=3 && literal.compare(pos-3,4,L"こーひー")==0);
            if(c==L'ー' && !expanded.empty() && !coffee) {
                auto keys=romanize(std::wstring(1,expanded.back()));
                wchar_t vowel=keys.empty()?0:keys.back();
                c=vowel==L'a'?L'あ':vowel==L'i'?L'い':vowel==L'u'?L'う':vowel==L'e'?L'い':vowel==L'o'?L'う':c;
            }
            expanded+=c;
        }
        out.kana=expanded;
    }
    out.romaji=romanize(out.kana);
    if(out.romaji.empty()) {out.error=L"변환할 수 있는 발음이 없습니다.";return out;}
    std::vector<Spelling> paths={{L"",0}};
    for(size_t pos=0;pos<out.kana.size();pos++) {
        wchar_t c=out.kana[pos];std::vector<Spelling> options={{std::wstring(1,c),0}};
        wchar_t other=c==L'じ'?L'ぢ':c==L'ぢ'?L'じ':c==L'ず'?L'づ':c==L'づ'?L'ず':0;
        if(other)options.push_back({std::wstring(1,other),1});
        if(koreanDash && pos<literal.size() && literal[pos]==L'ー' && c!=L'ー') {
            auto previous=pos?romanize(std::wstring(1,out.kana[pos-1])):L"";
            if(!previous.empty() && previous.back()==L'o')options.push_back({L"お",1});
            if(!previous.empty() && previous.back()==L'e')options.push_back({L"え",1});
            options.push_back({L"ー",2});
        }
        bool boundary=std::find(boundaries.begin(),boundaries.end(),pos)!=boundaries.end();
        if(koreanDash && boundary && (pos+1==out.kana.size() ||
           std::find(boundaries.begin(),boundaries.end(),pos+1)!=boundaries.end())) {
            if(c==L'わ')options.push_back({L"は",-1});
            if(c==L'え')options.push_back({L"へ",-1});
            if(c==L'お')options.push_back({L"を",-1});
        }
        // Joined Korean input contains no spaces. Keep possible particles as
        // lower-priority readings; the original word spelling stays available.
        if(koreanDash && (pos>0 || out.kana.size()==1) && !boundary) {
            if(c==L'わ')options.push_back({L"は",2});
            if(c==L'え')options.push_back({L"へ",2});
            if(c==L'お')options.push_back({L"を",2});
        }
        std::vector<Spelling> next;
        for(auto& path:paths)for(auto& option:options)next.push_back({path.text+option.text,path.cost+option.cost});
        prune(next);paths=std::move(next);
    }
    // Work backwards: a shortened coda or expanded loan sound must not move
    // offsets belonging to earlier syllables.
    for(auto it=aliases.rbegin();it!=aliases.rend();++it) {
        auto& alias=*it;
        auto count=paths.size();
        for(size_t n=0;n<count;n++) {
            if(paths[n].text.compare(alias.at,alias.length,out.kana,alias.at,alias.length)!=0)continue;
            auto alternate=paths[n].text;alternate.replace(alias.at,alias.length,alias.text);
            paths.push_back({alternate,paths[n].cost+alias.cost});
        }
        prune(paths);
    }
    if(literal!=out.kana)paths.push_back({literal,2});
    if(koreanDash) {
        auto canonical=canonicalSpelling(out.kana);
        if(canonical!=out.kana)paths.push_back({canonical,-2});
    }
    prune(paths);
    // Resource bounds must never remove the user's literal interpretation.
    std::vector<std::wstring> retained={out.kana,literal};
    auto retain=[&](const std::wstring& value) {
        if(std::none_of(paths.begin(),paths.end(),[&](const Spelling& p){return p.text==value;})) {
            if(paths.size()==16) {
                auto removable=std::find_if(paths.rbegin(),paths.rend(),[&](const Spelling& p){return std::find(retained.begin(),retained.end(),p.text)==retained.end();});
                if(removable!=paths.rend())paths.erase(std::next(removable).base());
            }
            paths.push_back({value,0});
        }
        retained.push_back(value);
    };
    retain(out.kana);
    if(literal!=out.kana)retain(literal);
    // Long input must still offer a consistent whole-input interpretation;
    // the 16-path beam otherwise loses "all k/t/p" or "all f" after a few
    // ambiguous syllables. These families consume a fixed number of slots.
    for(int family=0;family<=6;family++) {
        auto uniform=out.kana;
        for(auto it=aliases.rbegin();it!=aliases.rend();++it) {
            auto& alias=*it;
            if(alias.family==family && uniform.compare(alias.at,alias.length,out.kana,alias.at,alias.length)==0)
                uniform.replace(alias.at,alias.length,alias.text);
        }
        if(uniform!=out.kana)retain(uniform);
    }
    for(auto& path:paths)out.alternatives.push_back(path.text);
    // Keep the literal normalization stable for callers; query order may prefer
    // an orthographic stem or an explicitly separated particle.
    if(corrected) out.note=L"자주 쓰는 발음 표기를 보정했습니다. ";
    out.note+=approximate?L"받침·모음은 가까운 일본어 소리로 옮겼습니다. 독음을 확인해 주세요.":L"장음은 ‘-’ 또는 모음을 한 번 더 적어 주세요.";
    return out;
}
}
