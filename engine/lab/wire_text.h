#pragma once
#include <string>
#include <climits>
static std::wstring fromHex(const std::string& text) {
    std::wstring result;
    if(text.size()%4 || text.size()>32768)return result;
    for(size_t i=0;i<text.size();i+=4) {
        unsigned value=0;
        for(size_t j=0;j<4;j++) {
            char c=text[i+j];int digit=c>='0'&&c<='9'?c-'0':c>='a'&&c<='f'?c-'a'+10:-1;
            if(digit<0)return L"";value=value*16+digit;
        }
        result.push_back((wchar_t)value);
    }
    return result;
}
static bool parseReplacementCommand(const std::string& command,unsigned& serial,std::wstring& text) {
    serial=0;text.clear();if(command.compare(0,8,"REPLACE "))return false;
    size_t at=8,start=at;
    while(at<command.size() && command[at]>='0' && command[at]<='9') {
        unsigned digit=command[at++]-'0';if(serial>(UINT_MAX-digit)/10)return false;
        serial=serial*10+digit;
    }
    if(at==start || at>=command.size() || command[at++]!=' ')return false;
    std::string hex=command.substr(at);if(!hex.empty() && hex.back()=='\r')hex.pop_back();
    text=fromHex(hex);if(text.empty())return false;
    for(size_t i=0;i<text.size();i++) {
        unsigned c=text[i];if(!c)return false;
        if(c>=0xd800 && c<=0xdbff) {
            if(++i>=text.size() || text[i]<0xdc00 || text[i]>0xdfff)return false;
        } else if(c>=0xdc00 && c<=0xdfff)return false;
    }
    return true;
}
