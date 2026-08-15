import os
import shutil
import subprocess
import winreg
from typing import Optional, List
from langchain_core.tools import tool

# Common system app aliases mapping directly to Windows executables or URIs
SYSTEM_APP_ALIASES = {
    "calc": "calc.exe",
    "calculator": "calc.exe",
    "notepad": "notepad.exe",
    "paint": "mspaint.exe",
    "mspaint": "mspaint.exe",
    "explorer": "explorer.exe",
    "file explorer": "explorer.exe",
    "files": "explorer.exe",
    "task manager": "taskmgr.exe",
    "taskmgr": "taskmgr.exe",
    "cmd": "cmd.exe",
    "command prompt": "cmd.exe",
    "terminal": "wt.exe",
    "powershell": "powershell.exe",
    "edge": "msedge.exe",
    "microsoft edge": "msedge.exe",
    "chrome": "chrome.exe",
    "google chrome": "chrome.exe",
    "code": "code.cmd",
    "vscode": "code.cmd",
    "vs code": "code.cmd",
    "docker": "Docker Desktop.exe",
    "docker desktop": "Docker Desktop.exe",
    "mattermost": "Mattermost.exe",
    "settings": "ms-settings:",
}


def _find_app_in_start_menu_and_paths(clean_name: str) -> Optional[str]:
    """
    Scans Windows Start Menu shortcuts (.lnk), Desktop, and standard Program Files
    directories to find an application executable or shortcut matching clean_name.
    """
    search_dirs = [
        os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs"),
        os.path.expandvars(r"%ALLUSERSPROFILE%\Microsoft\Windows\Start Menu\Programs"),
        os.path.expandvars(r"%USERPROFILE%\Desktop"),
        os.path.expandvars(r"%PUBLIC%\Desktop"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs"),
        os.path.expandvars(r"%ProgramFiles%"),
        os.path.expandvars(r"%ProgramFiles(x86)%"),
        os.path.expandvars(r"%LOCALAPPDATA%"),
    ]

    # Phase 1: Search for exact or prefix matching .lnk shortcuts (fast & reliable)
    for base_dir in search_dirs[:4]:
        if not os.path.exists(base_dir):
            continue
        for root, _, files in os.walk(base_dir):
            for file in files:
                f_lower = file.lower()
                if f_lower.endswith(".lnk"):
                    stem = f_lower[:-4]
                    if stem == clean_name or stem.startswith(clean_name) or clean_name in stem:
                        return os.path.join(root, file)

    # Phase 2: Search Windows Registry App Paths (HKLM & HKCU)
    registry_keys = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"),
    ]
    for root_k, subkey in registry_keys:
        try:
            with winreg.OpenKey(root_k, subkey) as key:
                count = winreg.QueryInfoKey(key)[0]
                for i in range(count):
                    try:
                        k_name = winreg.EnumKey(key, i)
                        if clean_name in k_name.lower():
                            with winreg.OpenKey(key, k_name) as target_k:
                                val, _ = winreg.QueryValueEx(target_k, "")
                                if val and os.path.exists(val):
                                    return val
                    except Exception:
                        pass
        except Exception:
            pass

    # Phase 3: Search Program Files & LocalAppData for .exe
    for base_dir in search_dirs[4:]:
        if not os.path.exists(base_dir):
            continue
        try:
            for root, _, files in os.walk(base_dir):
                # Don't descend too deep into unrelated temp or cache folders
                depth = root[len(base_dir):].count(os.sep)
                if depth > 3:
                    continue
                for file in files:
                    f_lower = file.lower()
                    if f_lower.endswith(".exe"):
                        stem = f_lower[:-4]
                        if stem == clean_name or stem.startswith(clean_name) or clean_name in stem:
                            return os.path.join(root, file)
        except Exception:
            continue

    return None


def resolve_application_path(app_name: str) -> Optional[str]:
    """
    Intelligently resolves the full executable or shortcut path for a given application name.
    """
    if not app_name:
        return None

    clean_name = app_name.strip().strip("'\"").lower()
    
    # 1. Direct path check
    if os.path.exists(app_name):
        return os.path.abspath(app_name)

    # 2. Check alias map
    if clean_name in SYSTEM_APP_ALIASES:
        alias_target = SYSTEM_APP_ALIASES[clean_name]
        # If alias is a protocol (e.g. ms-settings:)
        if ":" in alias_target and not os.path.isabs(alias_target):
            return alias_target
        which_path = shutil.which(alias_target)
        if which_path:
            return which_path
        clean_name = alias_target.lower().replace(".exe", "").replace(".cmd", "")

    # 3. System PATH check via shutil.which
    which_path = shutil.which(clean_name) or shutil.which(f"{clean_name}.exe")
    if which_path:
        return which_path

    # 4. Search Start Menu shortcuts, Registry, and Program Files
    found_path = _find_app_in_start_menu_and_paths(clean_name)
    if found_path:
        return found_path

    return None


@tool
def run_application(app_name: str, app_path: str = "") -> str:
    """
    Opens a desktop application or system software on the host Windows machine.
    Automatically discovers and launches installed applications (e.g. Mattermost, Chrome, Docker, Notepad, Calculator, VS Code).
    """
    try:
        target = app_path.strip() if app_path else app_name.strip()
        if not target:
            return "Failed to launch application: No application name or path was provided."

        resolved = resolve_application_path(target)

        if resolved:
            # If it's a URI protocol (e.g., ms-settings:)
            if ":" in resolved and not os.path.exists(resolved) and not resolved.endswith(".exe"):
                os.startfile(resolved)
                return f"Successfully opened system service: '{target}'."
            
            # Launch shortcut (.lnk) or executable (.exe) using Windows Shell
            os.startfile(resolved)
            return f"Successfully launched '{target}' (resolved to: {resolved})."
        
        # Fallback: attempt native os.startfile on raw target
        try:
            os.startfile(target)
            return f"Successfully launched '{target}'."
        except Exception:
            pass

        # Fallback: attempt subprocess with shell execution
        proc = subprocess.Popen(target, shell=True)
        return f"Dispatched launch command for: '{target}'."

    except Exception as e:
        return f"Failed to open '{app_name}'. Error details: {str(e)}"


@tool
def close_application(app_name: str) -> str:
    """
    Closes a running desktop application by its name or process name (e.g., 'notepad', 'mattermost', 'chrome.exe').
    """
    try:
        clean_name = app_name.strip().strip("'\"")
        # Remove any leading path if user passed full path
        clean_name = os.path.basename(clean_name)
        
        # Check alias if present
        lower_name = clean_name.lower()
        if lower_name in SYSTEM_APP_ALIASES:
            alias = SYSTEM_APP_ALIASES[lower_name]
            if alias.endswith(".exe"):
                clean_name = alias

        targets = [clean_name]
        if not clean_name.lower().endswith(".exe"):
            targets.append(f"{clean_name}.exe")

        closed_any = False
        last_error = ""

        for tgt in targets:
            result = subprocess.run(['taskkill', '/IM', tgt, '/F'], capture_output=True, text=True)
            if result.returncode == 0:
                closed_any = True
                break
            else:
                last_error = result.stderr.strip()

        if closed_any:
            return f"Successfully terminated process for '{app_name}'."
        else:
            return f"Could not close '{app_name}'. It might not currently be running. ({last_error})"
    except Exception as e:
        return f"Error attempting to close '{app_name}': {str(e)}"


@tool
def search_local_file(file_name: str, search_directory: str = "") -> str:
    """
    Searches for a specific file by name within a given directory.
    Default search directory is the user's home/Documents folder.
    """
    try:
        if not search_directory or not os.path.exists(search_directory):
            search_directory = os.path.expanduser(r"~\Documents")
            if not os.path.exists(search_directory):
                search_directory = os.getcwd()

        clean_query = file_name.strip().strip("'\"").lower()
        found_files = []

        for root, _, files in os.walk(search_directory):
            for file in files:
                if clean_query in file.lower():
                    found_files.append(os.path.join(root, file))
            # Cap at 50 results
            if len(found_files) >= 50:
                break

        if found_files:
            return f"Found {len(found_files)} matching file(s) in {search_directory}:\n" + "\n".join(found_files)
        else:
            return f"No files matching '{file_name}' were found in '{search_directory}'."
    except Exception as e:
        return f"Error searching for file: {str(e)}"


# Export tool list
pc_tools = [run_application, close_application, search_local_file]
