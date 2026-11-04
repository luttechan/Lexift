#pragma once
static bool uiaSuffixMatches(IUIAutomationTextRange* match,IUIAutomationTextRange* caret,const std::wstring& token) {
    int end=1;BSTR text=nullptr;
    bool valid=SUCCEEDED(match->CompareEndpoints(TextPatternRangeEndpoint_End,caret,TextPatternRangeEndpoint_End,&end)) && end==0 &&
        SUCCEEDED(match->GetText((int)token.size()+1,&text)) && text && std::wstring(text,SysStringLen(text))==token;
    if(text)SysFreeString(text);return valid;
}
static bool findUiaSuffix(IUIAutomationTextRange* context,IUIAutomationTextRange* caret,const std::wstring& token,IUIAutomationTextRange** result) {
    *result=nullptr;if(!context || !caret || token.empty())return false;
    BSTR needle=SysAllocStringLen(token.data(),(UINT)token.size());if(!needle)return false;
    IUIAutomationTextRange* match=nullptr;
    HRESULT hr=context->FindText(needle,TRUE,FALSE,&match);SysFreeString(needle);
    if(SUCCEEDED(hr) && match && uiaSuffixMatches(match,caret,token)){*result=match;return true;}
    if(match)match->Release();match=nullptr;
    // Preserve support for providers without FindText, but verify exact text
    // so UTF-16 units cannot select extra grapheme clusters or adjacent words.
    hr=caret->Clone(&match);int moved=0;
    if(SUCCEEDED(hr) && match &&
       SUCCEEDED(match->MoveEndpointByUnit(TextPatternRangeEndpoint_Start,TextUnit_Character,-(int)token.size(),&moved)) &&
       uiaSuffixMatches(match,caret,token)){*result=match;return true;}
    if(match)match->Release();return false;
}
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
