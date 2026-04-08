import subprocess
import os

def open_with_notepadpp(file_path):
    notepad_path = r"C:\Program Files\Notepad++\notepad++.exe"

    if not os.path.exists(notepad_path):
        raise RuntimeError("NOTEPAD++ NOT FOUND")

    if not os.path.exists(file_path):
        raise RuntimeError(f"FILE NOT FOUND: {file_path}")

    subprocess.Popen([notepad_path, file_path])