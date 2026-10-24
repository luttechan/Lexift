// IAccessible2 fallback for Gecko and other MSAA/IA2 text providers.
// ABI: LinuxA11y/IAccessible2 api/Accessible{Text,EditableText}.idl.
#pragma once
#include <servprov.h>
struct KsTextSegment {BSTR text;LONG start,end;};
struct KsAccessibleText : IUnknown {
    virtual HRESULT STDMETHODCALLTYPE addSelection(LONG,LONG)=0;
    virtual HRESULT STDMETHODCALLTYPE get_attributes(LONG,LONG*,LONG*,BSTR*)=0;
    virtual HRESULT STDMETHODCALLTYPE get_caretOffset(LONG*)=0;
    virtual HRESULT STDMETHODCALLTYPE get_characterExtents(LONG,int,LONG*,LONG*,LONG*,LONG*)=0;
    virtual HRESULT STDMETHODCALLTYPE get_nSelections(LONG*)=0;
    virtual HRESULT STDMETHODCALLTYPE get_offsetAtPoint(LONG,LONG,int,LONG*)=0;
    virtual HRESULT STDMETHODCALLTYPE get_selection(LONG,LONG*,LONG*)=0;
    virtual HRESULT STDMETHODCALLTYPE get_text(LONG,LONG,BSTR*)=0;
    virtual HRESULT STDMETHODCALLTYPE get_textBeforeOffset(LONG,int,LONG*,LONG*,BSTR*)=0;
    virtual HRESULT STDMETHODCALLTYPE get_textAfterOffset(LONG,int,LONG*,LONG*,BSTR*)=0;
    virtual HRESULT STDMETHODCALLTYPE get_textAtOffset(LONG,int,LONG*,LONG*,BSTR*)=0;
    virtual HRESULT STDMETHODCALLTYPE removeSelection(LONG)=0;
    virtual HRESULT STDMETHODCALLTYPE setCaretOffset(LONG)=0;
    virtual HRESULT STDMETHODCALLTYPE setSelection(LONG,LONG,LONG)=0;
    virtual HRESULT STDMETHODCALLTYPE get_nCharacters(LONG*)=0;
    virtual HRESULT STDMETHODCALLTYPE scrollSubstringTo(LONG,LONG,int)=0;
    virtual HRESULT STDMETHODCALLTYPE scrollSubstringToPoint(LONG,LONG,int,LONG,LONG)=0;
    virtual HRESULT STDMETHODCALLTYPE get_newText(KsTextSegment*)=0;
    virtual HRESULT STDMETHODCALLTYPE get_oldText(KsTextSegment*)=0;
};
struct KsEditableText : IUnknown {
    virtual HRESULT STDMETHODCALLTYPE copyText(LONG,LONG)=0;
    virtual HRESULT STDMETHODCALLTYPE deleteText(LONG,LONG)=0;
    virtual HRESULT STDMETHODCALLTYPE insertText(LONG,BSTR*)=0;
    virtual HRESULT STDMETHODCALLTYPE cutText(LONG,LONG)=0;
    virtual HRESULT STDMETHODCALLTYPE pasteText(LONG)=0;
    virtual HRESULT STDMETHODCALLTYPE replaceText(LONG,LONG,BSTR*)=0;
    virtual HRESULT STDMETHODCALLTYPE setAttributes(LONG,LONG,BSTR*)=0;
};
// Only the prefix through get_states is used; method order follows Accessible2.idl.
struct KsAccessible2 : IAccessible {
    virtual HRESULT STDMETHODCALLTYPE get_nRelations(LONG*)=0;
    virtual HRESULT STDMETHODCALLTYPE get_relation(LONG,IUnknown**)=0;
    virtual HRESULT STDMETHODCALLTYPE get_relations(LONG,IUnknown**,LONG*)=0;
    virtual HRESULT STDMETHODCALLTYPE role(LONG*)=0;
    virtual HRESULT STDMETHODCALLTYPE scrollTo(int)=0;
    virtual HRESULT STDMETHODCALLTYPE scrollToPoint(int,LONG,LONG)=0;
    virtual HRESULT STDMETHODCALLTYPE get_groupPosition(LONG*,LONG*,LONG*)=0;
    virtual HRESULT STDMETHODCALLTYPE get_states(LONG*)=0;
};
static const IID ksAccessible2IID={0xe89f726e,0xc4f4,0x4c19,{0xbb,0x19,0xb6,0x47,0xd7,0xfa,0x84,0x78}};
static const IID ksTextIID={0x24fd2ffb,0x3aad,0x4a08,{0x83,0x35,0xa3,0xad,0x89,0xc0,0xfb,0x4b}};
static const IID ksEditableIID={0xa59aa09a,0x7011,0x4b65,{0x93,0x9d,0x32,0xb1,0xfb,0x55,0x47,0xe3}};
static HRESULT ia2Query(IUnknown* object,REFIID iid,void** result) {
    *result=nullptr;
    HRESULT hr=object->QueryInterface(iid,result);
    if(SUCCEEDED(hr) && *result)return hr;
    IServiceProvider* services=nullptr;
    if(SUCCEEDED(object->QueryInterface(IID_IServiceProvider,(void**)&services)) && services) {
        hr=services->QueryService(IID_IAccessible,iid,result);services->Release();
    }
    return hr;
}
struct Ia2Snapshot {
    IAccessible* accessible=nullptr;
    KsAccessibleText* text=nullptr;
    KsEditableText* editable=nullptr;
    IUnknown* identity=nullptr;
    LONG start=0,end=0,length=0;
    std::wstring token,before,after;
    RECT caret={};
    bool blocked=false,positioned=false;
    ~Ia2Snapshot() {
        if(accessible)accessible->Release();if(text)text->Release();
        if(editable)editable->Release();if(identity)identity->Release();
    }
};
static VARIANT ia2Self() {VARIANT v;VariantInit(&v);v.vt=VT_I4;v.lVal=CHILDID_SELF;return v;}
static IAccessible* ia2FocusedCache=nullptr;
static HWND ia2CacheTarget=nullptr,ia2CacheFocus=nullptr;
static bool ia2FocusDirty=false;
static void clearIa2FocusCache() {
    if(ia2FocusedCache)ia2FocusedCache->Release();
    ia2FocusedCache=nullptr;ia2CacheTarget=ia2CacheFocus=nullptr;ia2FocusDirty=false;
}
static IAccessible* focusedMsaa(HWND target) {
    if(ia2FocusDirty)clearIa2FocusCache();
    GUITHREADINFO focus={sizeof focus};
    HWND window=target;
    if(GetGUIThreadInfo(0,&focus) && focus.hwndFocus && GetAncestor(focus.hwndFocus,GA_ROOT)==target)window=focus.hwndFocus;
    if(ia2FocusedCache && ia2CacheTarget==target && ia2CacheFocus==window) {
        VARIANT state;VariantInit(&state);
        bool focused=SUCCEEDED(ia2FocusedCache->get_accState(ia2Self(),&state)) &&
            state.vt==VT_I4 && (state.lVal&STATE_SYSTEM_FOCUSED);
        VariantClear(&state);
        if(focused){ia2FocusedCache->AddRef();return ia2FocusedCache;}
    }
    clearIa2FocusCache();
    IAccessible* object=nullptr;
    if(FAILED(AccessibleObjectFromWindow(window,OBJID_CLIENT,IID_IAccessible,(void**)&object)) || !object)return nullptr;
    for(int depth=0;depth<32;depth++) {
        VARIANT child;VariantInit(&child);HRESULT hr=object->get_accFocus(&child);
        IAccessible* next=nullptr;
        if(SUCCEEDED(hr) && child.vt==VT_DISPATCH && child.pdispVal)
            child.pdispVal->QueryInterface(IID_IAccessible,(void**)&next);
        else if(SUCCEEDED(hr) && child.vt==VT_I4 && child.lVal>0) {
            IDispatch* dispatch=nullptr;
            if(SUCCEEDED(object->get_accChild(child,&dispatch)) && dispatch) {
                dispatch->QueryInterface(IID_IAccessible,(void**)&next);dispatch->Release();
            }
        }
        VariantClear(&child);
        if(!next)break;
        IUnknown *a=nullptr,*b=nullptr;
        object->QueryInterface(IID_IUnknown,(void**)&a);next->QueryInterface(IID_IUnknown,(void**)&b);
        bool same=a==b;if(a)a->Release();if(b)b->Release();
        if(same){next->Release();break;}
        object->Release();object=next;
    }
    if(object){ia2FocusedCache=object;object->AddRef();ia2CacheTarget=target;ia2CacheFocus=window;}
    return object;
}
static bool ia2Substring(KsAccessibleText* text,LONG start,LONG end,std::wstring& value) {
    BSTR content=nullptr;HRESULT hr=text->get_text(start,end,&content);
    if(FAILED(hr)){if(content)SysFreeString(content);return false;}
    value=content?std::wstring(content,SysStringLen(content)):L"";
    SysFreeString(content);return value.size()==(size_t)(end-start);
}
static bool readIa2Object(IAccessible* object,Ia2Snapshot& result) {
    auto self=ia2Self();VARIANT state,role;VariantInit(&state);VariantInit(&role);
    HRESULT stateHR=object->get_accState(self,&state),roleHR=object->get_accRole(self,&role);
    bool valid=SUCCEEDED(stateHR) && state.vt==VT_I4 && (state.lVal&STATE_SYSTEM_FOCUSED);
    result.blocked=state.vt==VT_I4 && (state.lVal&(STATE_SYSTEM_PROTECTED|STATE_SYSTEM_READONLY|STATE_SYSTEM_UNAVAILABLE));
    bool textRole=SUCCEEDED(roleHR) && role.vt==VT_I4 &&
        (role.lVal==ROLE_SYSTEM_TEXT || role.lVal==ROLE_SYSTEM_DOCUMENT);
    VariantClear(&state);VariantClear(&role);
    if(!valid || result.blocked)return false;
    KsAccessible2* core=nullptr;
    if(SUCCEEDED(ia2Query(object,ksAccessible2IID,(void**)&core)) && core) {
        LONG flags=0;HRESULT hr=core->get_states(&flags);core->Release();
        if(hr==S_OK)textRole=(flags&0x8)!=0; // IA2_STATE_EDITABLE, including contenteditable.
    }
    if(!textRole)return false;
    if(FAILED(ia2Query(object,ksTextIID,(void**)&result.text)) || !result.text)return false;
    ia2Query(object,ksEditableIID,(void**)&result.editable);
    // A document without an editing interface is a reading/caret-browsing view.
    if(!result.editable)return false;
    object->AddRef();result.accessible=object;
    object->QueryInterface(IID_IUnknown,(void**)&result.identity);
    LONG count=0,caret=-1,length=0;
    if(FAILED(result.text->get_nSelections(&count)) || count<0 || count>1)return false;
    if(count==1) {
        LONG begin=-1,end=-1;
        if(FAILED(result.text->get_selection(0,&begin,&end)) || begin!=end)return false;
    }
    if(result.text->get_caretOffset(&caret)!=S_OK || caret<=0 ||
       FAILED(result.text->get_nCharacters(&length)) || caret>length)return false;
    result.end=caret;result.length=length;
    LONG begin=std::max<LONG>(0,caret-256);
    if(!ia2Substring(result.text,begin,caret,result.before) ||
       !ia2Substring(result.text,caret,std::min<LONG>(length,caret+256),result.after))return false;
    size_t at=result.before.size();
    if(inlineCommitSpace && at && result.before[at-1]==L' ')--at;
    while(at && nativeHangul(result.before[at-1]))at--;
    result.token=result.before.substr(at);result.start=caret-(LONG)result.token.size();
    if(result.token.empty() || result.token.size()>200+(inlineCommitSpace?1:0))return false;
    LONG x=0,y=0,width=0,height=0;
    if(SUCCEEDED(result.text->get_characterExtents(caret,0,&x,&y,&width,&height)) && height>0) {
        result.caret={x,y,x,y+height};result.positioned=true;
    } else if(SUCCEEDED(result.text->get_characterExtents(caret-1,0,&x,&y,&width,&height)) && height>0) {
        result.caret={x+width,y,x+width,y+height};result.positioned=true;
    }
    if(!result.positioned && SUCCEEDED(object->accLocation(&x,&y,&width,&height,self)) && width>0 && height>0) {
        result.caret={x,y,x,y+height};result.positioned=true;
    }
    LONG after=-1;
    return result.positioned && result.text->get_caretOffset(&after)==S_OK && after==caret;
}
static bool sameIa2(const Ia2Snapshot& a,const Ia2Snapshot& b) {
    return a.identity && a.identity==b.identity && a.start==b.start && a.end==b.end &&
        a.length==b.length && a.token==b.token && a.before==b.before && a.after==b.after;
}
static bool sameIa2AfterCommitSpace(const Ia2Snapshot& a,const Ia2Snapshot& b) {
    auto before=a.before+L" ";if(before.size()>256)before.erase(0,before.size()-256);
    return a.identity && a.identity==b.identity && a.start==b.start && b.end==a.end+1 && b.length==a.length+1 &&
        b.token==a.token+L" " && b.before==before && a.after==b.after;
}
static bool selectIa2(const Ia2Snapshot& snapshot) {
    LONG count=0;
    if(FAILED(snapshot.text->get_nSelections(&count)))return false;
    HRESULT hr=count?snapshot.text->setSelection(0,snapshot.start,snapshot.end):snapshot.text->addSelection(snapshot.start,snapshot.end);
    LONG begin=-1,end=-1;
    return SUCCEEDED(hr) && SUCCEEDED(snapshot.text->get_selection(0,&begin,&end)) && begin==snapshot.start && end==snapshot.end;
}
static bool replaceIa2(const Ia2Snapshot& snapshot,const std::wstring& replacement) {
    BSTR text=SysAllocStringLen(replacement.data(),(UINT)replacement.size());
    if(!text)return false;
    HRESULT hr=snapshot.editable->replaceText(snapshot.start,snapshot.end,&text);
    if(SUCCEEDED(hr))snapshot.text->setCaretOffset(snapshot.start+(LONG)replacement.size());
    SysFreeString(text);return SUCCEEDED(hr);
}
