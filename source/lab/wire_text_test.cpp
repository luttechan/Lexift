#include <stdio.h>
#include "wire_text.h"
int main(){
    int passed=0,failed=0;unsigned id=0;std::wstring text;auto check=[&](bool ok){ok?passed++:failed++;};
    check(parseReplacementCommand("REPLACE 7 d558",id,text) && id==7 && text==L"하");
    std::string longText;for(int i=0;i<2000;i++)longText+="4e00";
    check(parseReplacementCommand("REPLACE 8 "+longText,id,text) && text.size()==2000);
    std::string maxText;for(int i=0;i<4096;i++)maxText+="d83dde00";
    check(parseReplacementCommand("REPLACE 9 "+maxText,id,text) && text.size()==8192);
    check(!parseReplacementCommand("REPLACE 9 "+maxText+"4e00",id,text));
    check(!parseReplacementCommand("REPLACE -1 d558",id,text));
    check(!parseReplacementCommand("REPLACE 4294967296 d558",id,text));
    check(!parseReplacementCommand("REPLACE 9 d558 bad",id,text));
    check(!parseReplacementCommand("REPLACE 9 d55",id,text));
    check(!parseReplacementCommand("REPLACE 9 0000",id,text));
    check(!parseReplacementCommand("REPLACE 9 dc00",id,text));
    check(!parseReplacementCommand("REPLACE 9 d800",id,text));
    check(parseReplacementCommand("REPLACE 4294967295 d558\r",id,text) && id==UINT_MAX);
    check(!parseReplacementCommand("REPLACE_X 9 d558",id,text));
    check(!parseReplacementCommand("REPLACE 9 ",id,text));
    printf("{\"passed\":%d,\"failed\":%d}\n",passed,failed);return failed?1:0;
}
