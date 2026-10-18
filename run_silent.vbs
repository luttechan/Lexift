Option Explicit
Dim sh, fso, base, pyexe, entry, cmd
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
base = fso.GetParentFolderName(WScript.ScriptFullName)
pyexe = base & "\.venv\Scripts\pythonw.exe"
entry = base & "\launch.pyw"
If Not fso.FileExists(pyexe) Then
  MsgBox "Run install.bat before launching KanaShift.", 16, "KanaShift"
  WScript.Quit 1
End If
sh.CurrentDirectory = base
cmd = Chr(34) & pyexe & Chr(34) & " " & Chr(34) & entry & Chr(34) & " --show"
sh.Run cmd, 0, False
