"""Finish a Windows app build with its external updater and release archive."""
import ast
import shutil
import subprocess
import sys
from pathlib import Path

from package_release import package


def source_version():
    tree = ast.parse(Path(__file__).with_name("app.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "VERSION" for t in node.targets):
            return ast.literal_eval(node.value)
    raise RuntimeError("VERSION is missing")


if __name__ == "__main__":
    from build_security import verify
    print('Security baseline:',verify())
    # Exercise the actual frozen Python, Qt DLLs, platform plugin and UI font.
    # Loading archived Python code in the build interpreter cannot verify ABI.
    subprocess.run([str(Path("dist/Lexift/Lexift.exe").resolve()), "--verify-runtime"],
                   check=True, timeout=30,
                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--noupx", "--onefile",
                    "--windowed", "--name", "LexiftUpdater", "--distpath", "module/helper-dist",
                    "--workpath", "module/build/updater", "--specpath", "module/build", "module/update_apply.py"], check=True)
    shutil.copy2("module/helper-dist/LexiftUpdater.exe", "dist/Lexift/module/LexiftUpdater.exe")
    print("Release ZIP:", package(Path("dist/Lexift"), Path("release"), source_version()))
