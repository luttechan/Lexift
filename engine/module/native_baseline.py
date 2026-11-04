"""Reject local-CPU builds before creating a redistributable package."""
import hashlib,json
from pathlib import Path

def verify(root):
    root=Path(root)
    for directory,binary,manifest,key in (
        ('lab','ime_candidate_host.exe','ime_candidate_host_build.json','binary_sha256'),
        ('module','kanashift_hooks.dll','native_hooks_build.json','dll_sha256'),
        ('module','lexift_keyboard.exe','keyboard_worker_build.json','binary_sha256')):
        folder=root/directory
        data=json.loads((folder/manifest).read_text(encoding='utf-8-sig'))
        if data.get('cpu')!='baseline':raise ValueError(f'{binary}: a baseline CPU build is required')
        if data.get(key)!=hashlib.sha256((folder/binary).read_bytes()).hexdigest():
            raise ValueError(f'{binary}: build manifest does not match the binary')
    return True
