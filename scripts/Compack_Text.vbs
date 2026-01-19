Set WshShell = CreateObject("WScript.Shell")
scriptDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
cmd = """" & scriptDir & "\Compack_Text.bat"""
WshShell.Run cmd, 0, False
