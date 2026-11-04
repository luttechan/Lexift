from pathlib import Path
import shutil
R=Path(__file__).resolve().parents[1]
shutil.copy2(R/'LICENSE',R/'engine/LICENSE')
source=(R/'engine/module/Lexift.spec').read_text(encoding='utf-8')
source=source.replace('module_folder = Path(SPECPATH)','module_folder = Path(SPECPATH) / "module"')
source=source.replace("[str(project_folder / 'launch.pyw')]","[str(project_folder / 'bridge.py')]")
source=source.replace("name='Lexift'","name='LexiftEngine'",1).replace('console=False','console=True')
source=source.replace("    name='Lexift',","    name='engine-dist',")
(R/'engine/LexiftEngine.spec').write_text(source,encoding='utf-8')
print('Prepared engine build spec')
