#include <windows.h>
#include <oleacc.h>
#include <string>
#include <vector>
#include <algorithm>
#include <stdio.h>
static bool nativeHangul(wchar_t c){return (c>=0xac00 && c<=0xd7a3)||c==L'-';}
static bool inlineCommitSpace=false;
#include "ia2_adapter.h"
#define STUB(name,args) HRESULT STDMETHODCALLTYPE name args override{return E_NOTIMPL;}
struct TextProvider : KsAccessible2,KsAccessibleText,KsEditableText,IServiceProvider {
    ULONG refs=1;LONG state=STATE_SYSTEM_FOCUSED,msaaRole=ROLE_SYSTEM_TEXT,ia2State=0x8,selections=0,begin=0,end=0;
    bool serviceOnly=false,asynchronousSelection=false,ignoreReplacement=false;
    LONG replacementCalls=0;
    LONG deferredReads=0;bool pendingEdit=false;std::wstring deferredValue;
    LONG selectionWrites=0;
    LONG caret=0,reads=0;bool endGeometry=true;
    std::wstring value=L"prefix 고치소-사마 suffix";
    TextProvider(){caret=(LONG)value.find(L" suffix");}
    HRESULT STDMETHODCALLTYPE QueryInterface(REFIID iid,void** p) override {
        *p=nullptr;
        if(IsEqualIID(iid,IID_IUnknown)||IsEqualIID(iid,IID_IAccessible)||IsEqualIID(iid,IID_IDispatch))*p=(IAccessible*)this;
        else if(IsEqualIID(iid,IID_IServiceProvider))*p=(IServiceProvider*)this;
        else if(IsEqualIID(iid,ksAccessible2IID))*p=(KsAccessible2*)this;
        else if(!serviceOnly && IsEqualIID(iid,ksTextIID))*p=(KsAccessibleText*)this;
        else if(!serviceOnly && IsEqualIID(iid,ksEditableIID))*p=(KsEditableText*)this;
        if(!*p)return E_NOINTERFACE;AddRef();return S_OK;
    }
    ULONG STDMETHODCALLTYPE AddRef() override{return ++refs;}
    ULONG STDMETHODCALLTYPE Release() override{return --refs;}
    STUB(GetTypeInfoCount,(UINT*)) STUB(GetTypeInfo,(UINT,LCID,ITypeInfo**))
    STUB(GetIDsOfNames,(REFIID,LPOLESTR*,UINT,LCID,DISPID*))
    STUB(Invoke,(DISPID,REFIID,LCID,WORD,DISPPARAMS*,VARIANT*,EXCEPINFO*,UINT*))
    STUB(get_accParent,(IDispatch**)) STUB(get_accChildCount,(LONG*)) STUB(get_accChild,(VARIANT,IDispatch**))
    STUB(get_accName,(VARIANT,BSTR*)) STUB(get_accValue,(VARIANT,BSTR*)) STUB(get_accDescription,(VARIANT,BSTR*))
    HRESULT STDMETHODCALLTYPE get_accRole(VARIANT,VARIANT* v)override{VariantInit(v);v->vt=VT_I4;v->lVal=msaaRole;return S_OK;}
    HRESULT STDMETHODCALLTYPE get_accState(VARIANT,VARIANT* v)override{VariantInit(v);v->vt=VT_I4;v->lVal=state;return S_OK;}
    STUB(get_accHelp,(VARIANT,BSTR*)) STUB(get_accHelpTopic,(BSTR*,VARIANT,LONG*))
    STUB(get_accKeyboardShortcut,(VARIANT,BSTR*)) STUB(get_accFocus,(VARIANT*)) STUB(get_accSelection,(VARIANT*))
    STUB(get_accDefaultAction,(VARIANT,BSTR*)) STUB(accSelect,(LONG,VARIANT))
    STUB(accLocation,(LONG*,LONG*,LONG*,LONG*,VARIANT)) STUB(accNavigate,(LONG,VARIANT,VARIANT*))
    STUB(accHitTest,(LONG,LONG,VARIANT*)) STUB(accDoDefaultAction,(VARIANT))
    STUB(put_accName,(VARIANT,BSTR)) STUB(put_accValue,(VARIANT,BSTR))
    STUB(get_nRelations,(LONG*)) STUB(get_relation,(LONG,IUnknown**)) STUB(get_relations,(LONG,IUnknown**,LONG*))
    STUB(role,(LONG*)) STUB(scrollTo,(int)) STUB(scrollToPoint,(int,LONG,LONG)) STUB(get_groupPosition,(LONG*,LONG*,LONG*))
    HRESULT STDMETHODCALLTYPE get_states(LONG* out)override{*out=ia2State;return S_OK;}
    HRESULT STDMETHODCALLTYPE QueryService(REFGUID service,REFIID iid,void** out)override {
        *out=nullptr;if(!IsEqualIID(service,IID_IAccessible))return E_NOINTERFACE;
        if(IsEqualIID(iid,ksTextIID))*out=(KsAccessibleText*)this;
        else if(IsEqualIID(iid,ksEditableIID))*out=(KsEditableText*)this;
        if(!*out)return E_NOINTERFACE;AddRef();return S_OK;
    }
    HRESULT STDMETHODCALLTYPE addSelection(LONG a,LONG b)override{selectionWrites++;if(!asynchronousSelection){selections=1;begin=a;end=b;}return S_OK;}
    STUB(get_attributes,(LONG,LONG*,LONG*,BSTR*))
    HRESULT STDMETHODCALLTYPE get_caretOffset(LONG* out)override{*out=caret;return S_OK;}
    HRESULT STDMETHODCALLTYPE get_characterExtents(LONG offset,int,LONG* x,LONG* y,LONG* w,LONG* h)override {
        if(!endGeometry && offset==caret)return E_FAIL;
        *x=-1200+offset*10;*y=300;*w=10;*h=24;return S_OK;
    }
    HRESULT STDMETHODCALLTYPE get_nSelections(LONG* n)override{*n=selections;return S_OK;}
    STUB(get_offsetAtPoint,(LONG,LONG,int,LONG*))
    HRESULT STDMETHODCALLTYPE get_selection(LONG,LONG* a,LONG* b)override{*a=begin;*b=end;return S_OK;}
    HRESULT STDMETHODCALLTYPE get_text(LONG a,LONG b,BSTR* s)override {
        reads++;if(a<0||b<a||b>(LONG)value.size())return E_INVALIDARG;
        *s=SysAllocStringLen(value.data()+a,b-a);return S_OK;
    }
    STUB(get_textBeforeOffset,(LONG,int,LONG*,LONG*,BSTR*))
    STUB(get_textAfterOffset,(LONG,int,LONG*,LONG*,BSTR*))
    STUB(get_textAtOffset,(LONG,int,LONG*,LONG*,BSTR*)) STUB(removeSelection,(LONG)) HRESULT STDMETHODCALLTYPE setCaretOffset(LONG n)override{caret=n;return S_OK;}
    HRESULT STDMETHODCALLTYPE setSelection(LONG,LONG a,LONG b)override{selectionWrites++;if(!asynchronousSelection){begin=a;end=b;}return S_OK;}
    HRESULT STDMETHODCALLTYPE get_nCharacters(LONG* n)override{if(pendingEdit && --deferredReads<=0){value=deferredValue;pendingEdit=false;}*n=(LONG)value.size();return S_OK;}
    STUB(scrollSubstringTo,(LONG,LONG,int)) STUB(scrollSubstringToPoint,(LONG,LONG,int,LONG,LONG))
    STUB(get_newText,(KsTextSegment*)) STUB(get_oldText,(KsTextSegment*))
    STUB(copyText,(LONG,LONG)) STUB(deleteText,(LONG,LONG)) STUB(insertText,(LONG,BSTR*))
    STUB(cutText,(LONG,LONG)) STUB(pasteText,(LONG)) STUB(setAttributes,(LONG,LONG,BSTR*))
    HRESULT STDMETHODCALLTYPE replaceText(LONG a,LONG b,BSTR* text)override {
        replacementCalls++;if(ignoreReplacement)return S_OK;
        if(deferredReads>0){deferredValue=value;deferredValue.replace(a,b-a,*text,SysStringLen(*text));pendingEdit=true;return S_OK;}
        value.replace(a,b-a,*text,SysStringLen(*text));return S_OK;
    }
};
static int passed=0,failed=0;
static void check(const char* name,bool ok){printf("{\"test\":\"%s\",\"passed\":%s}\n",name,ok?"true":"false");ok?passed++:failed++;}
int main(){
    TextProvider provider;
    {
        Ia2Snapshot a,b;check("editable text snapshot",readIa2Object(&provider,a));
        check("only word before caret",a.token==L"고치소-사마" && a.start==7 && a.after==L" suffix");
        check("caret on negative-origin monitor",a.caret.left<0 && a.caret.bottom==324);
        check("stable identity and range",readIa2Object(&provider,b) && sameIa2(a,b));
        check("range verified without selecting",prepareIa2Replacement(&provider,a) && provider.selectionWrites==0);
        check("Unicode replacement and caret after text",replaceIa2(a,L"ご馳走様") && provider.value==L"prefix ご馳走様 suffix" && provider.caret==a.start+4);
    }
    check("COM references balanced",provider.refs==1);
    for(auto flags:{STATE_SYSTEM_PROTECTED,STATE_SYSTEM_READONLY,STATE_SYSTEM_UNAVAILABLE}) {
        TextProvider guarded;guarded.state|=flags;Ia2Snapshot snapshot;
        check("blocked field never read",!readIa2Object(&guarded,snapshot) && snapshot.blocked && guarded.reads==0);
    }
    {
        TextProvider unfocused;unfocused.state=0;Ia2Snapshot snapshot;
        check("unfocused field refused",!readIa2Object(&unfocused,snapshot) && unfocused.reads==0);
    }
    {
        TextProvider selected;selected.selections=1;selected.begin=1;selected.end=4;Ia2Snapshot snapshot;
        check("nonempty selection refused",!readIa2Object(&selected,snapshot) && selected.reads==0);
    }
    {
        TextProvider fallback;fallback.endGeometry=false;Ia2Snapshot snapshot;
        check("last character caret fallback",readIa2Object(&fallback,snapshot) && snapshot.caret.left==-1200+fallback.caret*10);
    }
    {
        TextProvider changed;Ia2Snapshot a,b;readIa2Object(&changed,a);changed.value+=L"!";
        check("changed suffix invalidates range",readIa2Object(&changed,b) && !sameIa2(a,b));
    }
    {
        TextProvider one,two;Ia2Snapshot a,b;
        check("different field invalidates range",readIa2Object(&one,a) && readIa2Object(&two,b) && !sameIa2(a,b));
    }
    {
        TextProvider contenteditable;contenteditable.msaaRole=ROLE_SYSTEM_GROUPING;Ia2Snapshot snapshot;
        check("contenteditable via IA2 editable state",readIa2Object(&contenteditable,snapshot));
    }
    {
        TextProvider readonlyDocument;readonlyDocument.ia2State=0;Ia2Snapshot snapshot;
        check("caret browsing document is not editable",!readIa2Object(&readonlyDocument,snapshot) && readonlyDocument.reads==0);
    }
    {
        TextProvider services;services.serviceOnly=true;Ia2Snapshot snapshot;
        check("IServiceProvider interface discovery",readIa2Object(&services,snapshot));
    }
    {
        TextProvider composition;Ia2Snapshot before,settled;readIa2Object(&composition,before);
        composition.value.insert(composition.caret,L" ");composition.caret++;inlineCommitSpace=true;
        check("exact IME completion space accepted",readIa2Object(&composition,settled) && sameIa2AfterCommitSpace(before,settled));
        check("space included in verified replacement range",prepareIa2Replacement(&composition,settled) && replaceIa2(settled,L"ご馳走様") && composition.value==L"prefix ご馳走様 suffix");
        inlineCommitSpace=false;
    }
    {
        TextProvider moved;Ia2Snapshot before,wrong;readIa2Object(&moved,before);
        moved.value.insert(moved.caret,L"  ");moved.caret+=2;inlineCommitSpace=true;
        check("two spaces cannot reuse original range",!readIa2Object(&moved,wrong) || !sameIa2AfterCommitSpace(before,wrong));
        inlineCommitSpace=false;
    }
    {
        TextProvider remote;remote.asynchronousSelection=true;Ia2Snapshot snapshot;
        check("remote textarea snapshot",readIa2Object(&remote,snapshot));
        check("remote selection cache is not required",prepareIa2Replacement(&remote,snapshot) && remote.selectionWrites==0);
        check("remote textarea replacement preserves surrounding text",replaceIa2(snapshot,L"ご馳走様") && remote.value==L"prefix ご馳走様 suffix" && remote.caret==snapshot.start+4);
    }
    {
        TextProvider changed;Ia2Snapshot snapshot;readIa2Object(&changed,snapshot);changed.value+=L"!";
        check("stale remote text cannot be prepared for replacement",!prepareIa2Replacement(&changed,snapshot) && changed.selectionWrites==0);
    }
    {
        TextProvider noChange;noChange.ignoreReplacement=true;Ia2Snapshot snapshot;readIa2Object(&noChange,snapshot);
        check("acknowledged edit without changed text is not success",!replaceIa2(snapshot,L"ご馳走様"));
        check("failed asynchronous edit is not replayed",noChange.replacementCalls==1);
    }
    {
        TextProvider delayed;Ia2Snapshot snapshot;readIa2Object(&delayed,snapshot);delayed.deferredReads=3;
        check("delayed text cache is confirmed without replay",replaceIa2(snapshot,L"ご馳走様") && delayed.replacementCalls==1 && delayed.value==L"prefix ご馳走様 suffix");
    }
    {
        TextProvider ancestor;ancestor.state=STATE_SYSTEM_READONLY;Ia2Snapshot snapshot;
        check("unfocused readonly ancestor does not block other backends",!readIa2Object(&ancestor,snapshot) && !snapshot.blocked && ancestor.reads==0);
    }
    printf("{\"passed\":%d,\"failed\":%d,\"fixture\":\"IAccessible2 COM provider\",\"firefox_end_to_end\":false}\n",passed,failed);
    return failed?1:0;
}
