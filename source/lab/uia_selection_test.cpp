#include <windows.h>
#include <uiautomation.h>
#include <string>
#include <stdio.h>
#include "uia_selection.h"
#define STUB(name,args) HRESULT STDMETHODCALLTYPE name args override{return E_NOTIMPL;}
struct Range:IUIAutomationTextRange {
    ULONG refs=1;int begin=4,end=8;std::wstring value=L"와타시 ";
    STUB(QueryInterface,(REFIID,void**))
    ULONG STDMETHODCALLTYPE AddRef()override{return ++refs;}
    ULONG STDMETHODCALLTYPE Release()override{return --refs;}
    STUB(Clone,(IUIAutomationTextRange**)) STUB(Compare,(IUIAutomationTextRange*,BOOL*))
    HRESULT STDMETHODCALLTYPE CompareEndpoints(TextPatternRangeEndpoint a,IUIAutomationTextRange* other,TextPatternRangeEndpoint b,int* out)override {
        auto r=static_cast<Range*>(other);*out=(a==TextPatternRangeEndpoint_Start?begin:end)-(b==TextPatternRangeEndpoint_Start?r->begin:r->end);return S_OK;
    }
    STUB(ExpandToEnclosingUnit,(TextUnit)) STUB(FindAttribute,(TEXTATTRIBUTEID,VARIANT,BOOL,IUIAutomationTextRange**))
    STUB(FindText,(BSTR,BOOL,BOOL,IUIAutomationTextRange**)) STUB(GetAttributeValue,(TEXTATTRIBUTEID,VARIANT*))
    STUB(GetBoundingRectangles,(SAFEARRAY**)) STUB(GetEnclosingElement,(IUIAutomationElement**))
    HRESULT STDMETHODCALLTYPE GetText(int n,BSTR* out)override{*out=SysAllocStringLen(value.data(),(UINT)std::min<size_t>(value.size(),n));return S_OK;}
    STUB(Move,(TextUnit,int,int*)) STUB(MoveEndpointByUnit,(TextPatternRangeEndpoint,TextUnit,int,int*))
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
    printf("{\"passed\":%d,\"failed\":%d}\n",passed,failed);return failed?1:0;
}
