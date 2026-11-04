"""One-time, non-destructive import of KanaShift preferences into Lexift."""
from PySide6.QtCore import QSettings

def migrate_preferences(store,legacy=None):
    # Existing Lexift values always win. Do not merge an old configuration over
    # a partially configured or already-used Lexift installation.
    if store.allKeys():return False
    legacy=legacy if legacy is not None else QSettings('LuteTools','KanaShift')
    keys=legacy.allKeys()
    for key in keys:store.setValue(key,legacy.value(key))
    store.setValue('migration/from_kanashift',bool(keys));store.sync()
    return bool(keys)
