#include <windows.h>
#include <uiautomation.h>
#include <string>
#include <stdio.h>
#include "uia_selection.h"
#define STUB(name,args) HRESULT STDMETHODCALLTYPE name args override{return E_NOTIMPL;}
struct Range:IUIAutomationTextRange {
    ULONG refs=1;int begin=4,end=8;std::wstring value=L"와타시 ";Range* found=nullptr;Range* cloned=nullptr;
    STUB(QueryInterface,(REFIID,void**))
    ULONG STDMETHODCALLTYPE AddRef()override{return ++refs;}
    ULONG STDMETHODCALLTYPE Release()override{return --refs;}
    HRESULT STDMETHODCALLTYPE Clone(IUIAutomationTextRange** out)override{*out=cloned;if(!cloned)return E_NOTIMPL;cloned->AddRef();return S_OK;}
    STUB(Compare,(IUIAutomationTextRange*,BOOL*))
    HRESULT STDMETHODCALLTYPE CompareEndpoints(TextPatternRangeEndpoint a,IUIAutomationTextRange* other,TextPatternRangeEndpoint b,int* out)override {
        auto r=static_cast<Range*>(other);*out=(a==TextPatternRangeEndpoint_Start?begin:end)-(b==TextPatternRangeEndpoint_Start?r->begin:r->end);return S_OK;
    }
    STUB(ExpandToEnclosingUnit,(TextUnit)) STUB(FindAttribute,(TEXTATTRIBUTEID,VARIANT,BOOL,IUIAutomationTextRange**))
    HRESULT STDMETHODCALLTYPE FindText(BSTR needle,BOOL backward,BOOL ignoreCase,IUIAutomationTextRange** out)override {
        *out=nullptr;if(!found || !backward || ignoreCase || found->value!=std::wstring(needle,SysStringLen(needle)))return S_OK;
        *out=found;found->AddRef();return S_OK;
    }
    STUB(GetAttributeValue,(TEXTATTRIBUTEID,VARIANT*))
    STUB(GetBoundingRectangles,(SAFEARRAY**)) STUB(GetEnclosingElement,(IUIAutomationElement**))
    HRESULT STDMETHODCALLTYPE GetText(int n,BSTR* out)override{*out=SysAllocStringLen(value.data(),(UINT)std::min<size_t>(value.size(),n));return S_OK;}
    STUB(Move,(TextUnit,int,int*))
    HRESULT STDMETHODCALLTYPE MoveEndpointByUnit(TextPatternRangeEndpoint side,TextUnit,int count,int* moved)override{if(side==TextPatternRangeEndpoint_Start)begin+=count;else end+=count;*moved=count;return S_OK;}
    STUB(MoveEndpointByRange,(TextPatternRangeEndpoint,IUIAutomationTextRange*,TextPatternRangeEndpoint))
    STUB(Select,()) STUB(AddToSelection,()) STUB(RemoveFromSelection,()) STUB(ScrollIntoView,(BOOL)) STUB(GetChildren,(IUIAutomationElementArray**))
};
struct Array:IUIAutomationTextRangeArray {
    Range* range;int count=1;ULONG refs=1;Array(Range* r):range(r){}
    STUB(QueryInterface,(REFIID,void**))
    ULONG STDMETHODCALLTYPE AddRef()override{return ++refs;} ULONG STDMETHODCALLTYPE Release()override{return --refs;}
    HRESULT STDMETHODCALLTYPE get_Length(int* out)override{*out=count;return S_OK;}
    HRESULT STDMETHODCALLTYPE GetElement(int,IUIAutomationTextRange** out)override{*out=range;range->AddRef();return S_OK;}
};
int main(){
    Range expected,actual;Array selection(&actual);int passed=0,failed=0;
    auto check=[&](bool ok){ok?passed++:failed++;};
    check(selectedUiaRangeMatches(&expected,&selection,L"와타시 "));
    actual.end=actual.begin;check(!selectedUiaRangeMatches(&expected,&selection,L"와타시 "));
    actual.end=8;check(selectedUiaRangeMatches(&expected,&selection,L"와타시 "));
    actual.begin=3;check(!selectedUiaRangeMatches(&expected,&selection,L"와타시 "));
    actual.begin=4;actual.value=L"변경됨 ";check(!selectedUiaRangeMatches(&expected,&selection,L"와타시 "));
    actual.value=L"와타시 ";selection.count=2;check(!selectedUiaRangeMatches(&expected,&selection,L"와타시 "));
    selection.count=0;check(!selectedUiaRangeMatches(&expected,&selection,L"와타시 "));
    check(!selectedUiaRangeMatches(&expected,nullptr,L"와타시 "));
    check(actual.refs==1);
    {
        Range context,caret,match;context.found=&match;match.value=L"\x110b\x116a\x1110\x1161\x1109\x1175";
        match.begin=9;match.end=15;caret.begin=caret.end=15;IUIAutomationTextRange* result=nullptr;
        check(findUiaSuffix(&context,&caret,match.value,&result));if(result)result->Release();
        caret.begin=caret.end=16;check(!findUiaSuffix(&context,&caret,match.value,&result));
        check(!findUiaSuffix(&context,&caret,L"다른 단어",&result));
        check(match.refs==1);
    }
    {
        Range context,caret,clone;caret.begin=caret.end=8;clone.begin=clone.end=8;caret.cloned=&clone;
        IUIAutomationTextRange* result=nullptr;
        check(findUiaSuffix(&context,&caret,L"와타시 ",&result) && clone.begin==4);if(result)result->Release();
        clone.begin=8;clone.value=L"앞 와타시 ";check(!findUiaSuffix(&context,&caret,L"와타시 ",&result));
        check(clone.refs==1);
    }
    printf("{\"passed\":%d,\"failed\":%d}\n",passed,failed);return failed?1:0;
}
