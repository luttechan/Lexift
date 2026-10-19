"""Finish a Windows app build with its external updater and release archive."""
import ast
import shutil
import subprocess
import sys
from pathlib import Path

from package_release import package


def source_version():
    tree = ast.parse(Path("app.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "VERSION" for t in node.targets):
            return ast.literal_eval(node.value)
    raise RuntimeError("VERSION is missing")


if __name__ == "__main__":
    subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--noupx", "--onefile",
                    "--windowed", "--name", "KanaShiftUpdater", "--distpath", "helper-dist",
                    "--workpath", "build/updater", "--specpath", "build", "update_apply.py"], check=True)
    shutil.copy2("helper-dist/KanaShiftUpdater.exe", "dist/KanaShift/KanaShiftUpdater.exe")
    print("Release ZIP:", package(Path("dist/KanaShift"), Path("release"), source_version()))
