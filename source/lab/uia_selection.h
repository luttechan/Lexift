#pragma once
static bool selectedUiaRangeMatches(IUIAutomationTextRange* expected,IUIAutomationTextRangeArray* array,const std::wstring& token) {
    if(!expected || !array)return false;
    int count=0;if(FAILED(array->get_Length(&count)) || count!=1)return false;
    IUIAutomationTextRange* selected=nullptr;
    if(FAILED(array->GetElement(0,&selected)) || !selected)return false;
    int begin=1,end=1;BSTR text=nullptr;
    bool same=SUCCEEDED(expected->CompareEndpoints(TextPatternRangeEndpoint_Start,selected,TextPatternRangeEndpoint_Start,&begin)) &&
        SUCCEEDED(expected->CompareEndpoints(TextPatternRangeEndpoint_End,selected,TextPatternRangeEndpoint_End,&end)) && begin==0 && end==0;
    if(same) {
        same=SUCCEEDED(selected->GetText((int)token.size()+1,&text)) && text && std::wstring(text,SysStringLen(text))==token;
    }
    if(text)SysFreeString(text);selected->Release();return same;
}
