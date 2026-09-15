Set WshShell = CreateObject("WScript.Shell")
Set WshEnv = WshShell.Environment("PROCESS")
WshEnv("OLLAMA_BASE_URL") = "http://127.0.0.1:11434"
WshShell.CurrentDirectory = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
WshShell.Run "cmd /c ""open-webui serve > open-webui.log 2>&1""", 0, False