#include <windows.h>
#include <uiautomation.h>
#include <stdio.h>
#include "editable_policy.h"
int main(){
    VARIANT unknown={};unknown.vt=VT_EMPTY;
    VARIANT writable={};writable.vt=VT_BOOL;writable.boolVal=VARIANT_FALSE;
    VARIANT locked=writable;locked.boolVal=VARIANT_TRUE;
    bool tests[]={editableTextRange(UIA_EditControlTypeId,unknown,false),
        editableTextRange(UIA_DocumentControlTypeId,unknown,false),
        editableTextRange(UIA_ComboBoxControlTypeId,unknown,true),
        editableTextRange(UIA_CustomControlTypeId,unknown,true),
        !editableTextRange(UIA_ComboBoxControlTypeId,unknown,false),
        !editableTextRange(UIA_CustomControlTypeId,unknown,false),
        !editableTextRange(UIA_ComboBoxControlTypeId,locked,true),
        !editableTextRange(UIA_EditControlTypeId,locked,true),
        editableTextRange(UIA_ComboBoxControlTypeId,writable,false)};
    int passed=0;for(bool ok:tests)if(ok)passed++;
    printf("{\"passed\":%d,\"failed\":%d}\n",passed,9-passed);return passed==9?0:1;
}
