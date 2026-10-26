#pragma once
static bool editableTextRange(CONTROLTYPEID type,const VARIANT& readOnly,bool writableValue) {
    if(readOnly.vt==VT_BOOL)return readOnly.boolVal==VARIANT_FALSE;
    return type==UIA_EditControlTypeId || type==UIA_DocumentControlTypeId || writableValue;
}
