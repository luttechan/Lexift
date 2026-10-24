#pragma once
#include <string>
#include <vector>
#include <utility>

namespace reading {
struct Result {
    std::wstring kana, romaji, note, error;
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
    static const wchar_t* stems[19]={L"ぎ",L"き",L"に",L"じ",L"て",L"り",L"み",L"び",L"ぴ",L"し",L"し",L"",L"じ",L"じ",L"ち",L"き",L"て",L"ぴ",L"ひ"};
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
        {L"고자이마스",L"ございます"},{L"도쿄",L"とうきょう"},{L"토쿄",L"とうきょう"},
        {L"오하요",L"おはよう"}};
    bool corrected=false,approximate=false;
    for(size_t i=0;i<text.size();i++) {
        wchar_t c=text[i];
        if(c==L' ' || c==L'\t' || c==L'\n' || c==L'\r') continue;
        bool matched=false;
        for(const auto& entry:lexicon) {
            if(text.compare(i,entry.first.size(),entry.first)==0 &&
               !(i+entry.first.size()<text.size() && text[i+entry.first.size()]==L'우')) {
                out.kana+=entry.second;i+=entry.first.size()-1;corrected=matched=true;break;
            }
        }
        if(matched) continue;
        if(c>=0xac00 && c<=0xd7a3) {
            unsigned n=c-0xac00;int l=n/588,v=(n%588)/28,t=n%28;
            out.kana+=mora(l,v);
            if(t==4 || t==16 || t==21) out.kana+=L"ん";
            else if(t==8) {out.kana+=L"る";approximate=true;}
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
    out.romaji=romanize(out.kana);
    if(out.romaji.empty()) {out.error=L"변환할 수 있는 발음이 없습니다.";return out;}
    if(corrected) out.note=L"자주 쓰는 발음 표기를 보정했습니다. ";
    out.note+=approximate?L"받침·모음은 가까운 일본어 소리로 옮겼습니다. 독음을 확인해 주세요.":L"장음은 ‘-’ 또는 모음을 한 번 더 적어 주세요.";
    return out;
}
}
