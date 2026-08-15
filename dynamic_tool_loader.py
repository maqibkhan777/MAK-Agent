import os
import sys
import glob
import inspect
import importlib.util
from typing import List, Dict, Any, Optional, Callable
from langchain_core.tools import BaseTool, StructuredTool, tool as langchain_tool

SANDBOX_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "dynamic_tools"))
_REGISTERED_DYNAMIC_TOOLS: Dict[str, Any] = {}


def load_dynamic_tools(force_reload: bool = False) -> List[Any]:
    """
    Scans the dynamic_tools/ sandbox directory and dynamically registers
    all valid Python functions and @tool definitions as active LangChain/LangGraph tools.
    """
    global _REGISTERED_DYNAMIC_TOOLS

    if _REGISTERED_DYNAMIC_TOOLS and not force_reload:
        return list(_REGISTERED_DYNAMIC_TOOLS.values())

    loaded_tools: Dict[str, Any] = {}
    os.makedirs(SANDBOX_DIR, exist_ok=True)

    # Ensure dynamic_tools is on sys.path
    if SANDBOX_DIR not in sys.path:
        sys.path.insert(0, SANDBOX_DIR)

    py_files = glob.glob(os.path.join(SANDBOX_DIR, "*.py"))

    for file_path in py_files:
        base_name = os.path.basename(file_path)
        if base_name.startswith("__"):
            continue

        module_name = f"dynamic_tools.{base_name[:-3]}"

        try:
            # Dynamically load the module using importlib
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if spec is None or spec.loader is None:
                continue

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            # Inspect module attributes for tools and callable functions
            for attr_name, attr_value in inspect.getmembers(module):
                if attr_name.startswith("_"):
                    continue

                # Case 1: Already a LangChain or CrewAI Tool object
                if isinstance(attr_value, BaseTool) or hasattr(attr_value, "run") and hasattr(attr_value, "name"):
                    tool_key = getattr(attr_value, "name", attr_name)
                    loaded_tools[tool_key] = attr_value
                    print(f"  [Dynamic Tool Loader] Registered existing @tool: '{tool_key}' from {base_name}")

                # Case 2: Plain callable function (wrap as StructuredTool / langchain_tool)
                elif inspect.isfunction(attr_value) and attr_value.__module__ == module_name:
                    doc = inspect.getdoc(attr_value) or f"Dynamically loaded tool {attr_name}"
                    try:
                        # Wrap as LangChain tool
                        wrapped_tool = langchain_tool(attr_value)
                        loaded_tools[attr_name] = wrapped_tool
                        print(f"  [Dynamic Tool Loader] Wrapped and registered function: '{attr_name}' from {base_name}")
                    except Exception as wrap_err:
                        print(f"  [Dynamic Tool Loader Warning] Could not wrap {attr_name}: {wrap_err}")

        except Exception as err:
            print(f"[Dynamic Tool Loader Error] Failed importing '{base_name}': {err}")

    _REGISTERED_DYNAMIC_TOOLS = loaded_tools
    print(f"\n[Dynamic Tool Engine] Total Active Dynamic Tools: {len(_REGISTERED_DYNAMIC_TOOLS)}\n")
    return list(_REGISTERED_DYNAMIC_TOOLS.values())


def reload_dynamic_tools() -> List[Any]:
    """Force reloads all scripts in dynamic_tools/ directory."""
    return load_dynamic_tools(force_reload=True)


def get_dynamic_tool(name: str) -> Optional[Any]:
    """Retrieves a registered dynamic tool by name."""
    tools = load_dynamic_tools()
    for t in tools:
        if getattr(t, "name", "") == name:
            return t
    return None


def list_dynamic_tools_catalog() -> List[Dict[str, str]]:
    """Returns a list of all registered dynamic tool descriptions."""
    tools = load_dynamic_tools()
    catalog = []
    for t in tools:
        catalog.append({
            "name": getattr(t, "name", str(t)),
            "description": getattr(t, "description", "")
        })
    return catalog


if __name__ == "__main__":
    print("Testing Dynamic Tool Loader...")
    active_tools = load_dynamic_tools(force_reload=True)
    print(f"Successfully loaded {len(active_tools)} tools: {[getattr(t, 'name', '') for t in active_tools]}")
