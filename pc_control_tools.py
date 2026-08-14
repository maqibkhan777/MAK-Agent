import os
import subprocess
from typing import List
from langchain_core.tools import tool


@tool
def run_application(app_name: str, app_path: str = "") -> str:
    """
    Opens a desktop application on the host Windows machine. 
    Use app_path for a specific software directory (e.g., 'C:\\Program Files\\...').
    Use app_name for default system apps (e.g., 'notepad', 'calc').
    """
    try:
        if app_path and os.path.exists(app_path):
            subprocess.Popen([app_path])
            return f"Successfully launched application at: {app_path}"
        else:
            # Fallback for system apps natively in the Windows PATH
            subprocess.Popen(app_name, shell=True)
            return f"Attempted to launch system application: {app_name}"
    except Exception as e:
        return f"Failed to open {app_name}. Error: {str(e)}"


@tool
def close_application(app_name: str) -> str:
    """
    Closes a running desktop application by its process name (e.g., 'notepad.exe', 'spotify.exe').
    """
    try:
        # Executes the native Windows taskkill command
        result = subprocess.run(['taskkill', '/IM', app_name, '/F'], capture_output=True, text=True)
        if result.returncode == 0:
            return f"Successfully closed {app_name}."
        else:
            return f"Could not close {app_name}. It might not be running. Details: {result.stderr.strip()}"
    except Exception as e:
        return f"Error attempting to close {app_name}: {str(e)}"


@tool
def search_local_file(file_name: str, search_directory: str = "C:\\Users\\Objects\\Documents") -> str:
    """
    Searches for a specific file by name within a given directory.
    Default directory is the user's Documents folder.
    """
    try:
        if not os.path.exists(search_directory):
            # Fallback to current working directory if specified path doesn't exist
            search_directory = os.getcwd()

        found_files = []
        # Walk through the directory tree
        for root, dirs, files in os.walk(search_directory):
            for file in files:
                if file_name.lower() in file.lower():
                    found_files.append(os.path.join(root, file))
            # Cap at 50 results to prevent context overload
            if len(found_files) >= 50:
                break
        
        if found_files:
            return f"Found {len(found_files)} matching file(s) in {search_directory}:\n" + "\n".join(found_files)
        else:
            return f"No files matching '{file_name}' were found in {search_directory}."
    except Exception as e:
        return f"Error searching for file: {str(e)}"


# Export the tools as a list so they can be easily bound to our agent
pc_tools = [run_application, close_application, search_local_file]
