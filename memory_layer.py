"""
MAK Enterprise OS - Persistent Cognitive Memory & Knowledge Graph Layer
Powered by Cognee & LanceDB.

Provides:
- Knowledge graph indexing & entity-relationship extraction (cognify)
- Multi-modal memory search (Graph Completion, RAG, Chunks, Insights)
- Cross-session memory recall tool for LangChain and LangGraph multi-agent teams.
"""

import os
import sys
import asyncio
from typing import List, Optional, Union

# Set utf-8 stdout encoding for Windows console compatibility
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure root workspace is available for key_vault imports
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from dotenv import load_dotenv
load_dotenv()

from key_vault import vault

# ---------------------------------------------------------------------
# 1. Cognee Environment & Provider Configuration
# ---------------------------------------------------------------------
os.environ["ENABLE_BACKEND_ACCESS_CONTROL"] = "false"
os.environ["CACHING"] = "false"
os.environ["SESSION_MEMORY"] = "false"
os.environ["VECTOR_DB_PROVIDER"] = "lancedb"

openrouter_key = vault.get_active_key("openrouter") or os.getenv("OPENROUTER_API_KEY")
groq_key = vault.get_active_key("groq") or os.getenv("GROQ_API_KEY")
openai_key = vault.get_active_key("openai") or os.getenv("OPENAI_API_KEY")

if openrouter_key:
    os.environ["LLM_PROVIDER"] = "openai"
    os.environ["LLM_ENDPOINT"] = "https://openrouter.ai/api/v1"
    os.environ["LLM_API_KEY"] = openrouter_key
    os.environ["LLM_MODEL"] = "openai/meta-llama/llama-3.3-70b-instruct"
    os.environ["EMBEDDING_PROVIDER"] = "openai"
    os.environ["EMBEDDING_ENDPOINT"] = "https://openrouter.ai/api/v1"
    os.environ["EMBEDDING_API_KEY"] = openrouter_key
    os.environ["EMBEDDING_MODEL"] = "openai/text-embedding-3-small"
    os.environ["EMBEDDING_DIMENSIONS"] = "1536"
elif groq_key:
    os.environ["LLM_PROVIDER"] = "openai"
    os.environ["LLM_ENDPOINT"] = "https://api.groq.com/openai/v1"
    os.environ["LLM_API_KEY"] = groq_key
    os.environ["LLM_MODEL"] = "openai/llama-3.3-70b-versatile"
    os.environ["EMBEDDING_PROVIDER"] = "openai"
    os.environ["EMBEDDING_ENDPOINT"] = "https://api.groq.com/openai/v1"
    os.environ["EMBEDDING_API_KEY"] = groq_key
    os.environ["EMBEDDING_MODEL"] = "openai/text-embedding-3-small"
    os.environ["EMBEDDING_DIMENSIONS"] = "1536"
elif openai_key:
    os.environ["LLM_PROVIDER"] = "openai"
    os.environ["LLM_API_KEY"] = openai_key
    os.environ["LLM_MODEL"] = "gpt-4o-mini"
    os.environ["EMBEDDING_PROVIDER"] = "openai"
    os.environ["EMBEDDING_API_KEY"] = openai_key
    os.environ["EMBEDDING_MODEL"] = "text-embedding-3-small"
    os.environ["EMBEDDING_DIMENSIONS"] = "1536"

import cognee
from cognee.modules.search.types import SearchType

try:
    from langchain.tools import tool
except ImportError:
    try:
        from langchain_core.tools import tool
    except ImportError:
        def tool(func):
            func.is_tool = True
            return func


# ---------------------------------------------------------------------
# 2. Knowledge Ingestion & Graph Extraction (Cognify Engine)
# ---------------------------------------------------------------------
async def cognify_knowledge_base(directory_path: str = "./company_knowledge_base") -> str:
    """
    Ingests all markdown, text, or documentation files from the designated directory
    into Cognee, extracting semantic entities and relationships, and generating
    persistent LanceDB vector and graph indexes.

    Args:
        directory_path (str): Relative or absolute path to documentation folder.

    Returns:
        str: Summary of cognified documents and graph creation status.
    """
    abs_dir = os.path.abspath(directory_path)
    if not os.path.exists(abs_dir):
        return f"[Cognee Ingestion Error]: Directory '{abs_dir}' does not exist."

    supported_extensions = {".md", ".txt", ".json", ".pdf", ".rst"}
    ingested_files = []

    for root, _, files in os.walk(abs_dir):
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in supported_extensions:
                file_full_path = os.path.join(root, file)
                try:
                    await cognee.add(file_full_path)
                    ingested_files.append(file)
                except Exception as e:
                    print(f"[Cognee Add Warning] Could not add '{file}': {e}")

    if not ingested_files:
        return f"[Cognee Ingestion Notice]: No supported documents found in '{abs_dir}'."

    try:
        print(f"[Cognee Cognify] Building knowledge graph and vector indexes for {len(ingested_files)} documents...")
        await cognee.cognify()
        return (
            f"Successfully cognified {len(ingested_files)} enterprise documents from '{directory_path}'.\n"
            f"Ingested files: {', '.join(ingested_files)}\n"
            f"Knowledge Graph & LanceDB vector store initialized."
        )
    except Exception as e:
        return f"[Cognee Cognify Error]: Failed to construct knowledge graph: {e}"


# ---------------------------------------------------------------------
# 3. Semantic & Graph Memory Query Engine
# ---------------------------------------------------------------------
async def _async_query_memory(query: str, search_type: str = "GRAPH") -> str:
    """
    Internal asynchronous memory search across Cognee knowledge graph and vector index.
    """
    type_map = {
        "GRAPH": SearchType.GRAPH_COMPLETION,
        "GRAPH_COMPLETION": SearchType.GRAPH_COMPLETION,
        "RAG": SearchType.RAG_COMPLETION,
        "RAG_COMPLETION": SearchType.RAG_COMPLETION,
        "SUMMARIES": SearchType.SUMMARIES,
        "CHUNKS": SearchType.CHUNKS,
        "HYBRID": SearchType.HYBRID_COMPLETION,
        "INSIGHTS": SearchType.INSIGHTS if hasattr(SearchType, "INSIGHTS") else SearchType.GRAPH_COMPLETION
    }

    target_type = type_map.get(search_type.upper().strip(), SearchType.GRAPH_COMPLETION)

    try:
        results = await cognee.search(query_text=query, query_type=target_type)
        if not results:
            # Fallback to RAG completion if graph returned empty
            if target_type == SearchType.GRAPH_COMPLETION:
                results = await cognee.search(query_text=query, query_type=SearchType.RAG_COMPLETION)

        if not results:
            return f"[Enterprise Memory]: No relevant facts or graph relations found for query: '{query}'."

        if isinstance(results, list):
            formatted_items = []
            for item in results:
                if isinstance(item, str):
                    formatted_items.append(item.strip())
                elif hasattr(item, "text"):
                    formatted_items.append(getattr(item, "text", "").strip())
                elif isinstance(item, dict):
                    formatted_items.append(str(item))
                else:
                    formatted_items.append(str(item).strip())
            return "\n\n".join(formatted_items)
        return str(results)
    except Exception as e:
        return f"[Memory Query Notice]: Query completed with note: {e}"


def query_memory(query: str, search_type: str = "GRAPH") -> str:
    """
    Synchronous entrypoint for querying Cognee memory and formatting semantic entities,
    relationships, and relevant context into a clean summary string.

    Args:
        query (str): The search phrase or question.
        search_type (str): 'GRAPH', 'RAG', 'SUMMARIES', 'CHUNKS', or 'HYBRID'.

    Returns:
        str: Formatted context summary and entity connections.
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # In an already running event loop (e.g. FastAPI / Async worker)
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                result = pool.submit(lambda: asyncio.run(_async_query_memory(query, search_type))).result()
            return result
        else:
            return loop.run_until_complete(_async_query_memory(query, search_type))
    except Exception:
        return asyncio.run(_async_query_memory(query, search_type))


# ---------------------------------------------------------------------
# 4. LangChain / LangGraph Enterprise Memory Tool
# ---------------------------------------------------------------------
@tool
def search_enterprise_memory(query: str) -> str:
    """Searches the persistent enterprise knowledge graph for long-term facts, entity connections, and historical context across past sessions and notes."""
    print(f"\n[Enterprise Memory Tool] Searching knowledge graph & vector memory for: '{query}'...")
    result = query_memory(query=query, search_type="GRAPH")
    return result


# ---------------------------------------------------------------------
# Self-Test / CLI Entrypoint
# ---------------------------------------------------------------------
if __name__ == "__main__":
    print("==================================================================")
    print(" [COGNEE MEMORY] MAK ENTERPRISE OS - KNOWLEDGE GRAPH LAYER")
    print("==================================================================")
    
    # 1. Ingest knowledge base
    print("\n[Step 1] Ingesting & Cognifying Knowledge Base...")
    status = asyncio.run(cognify_knowledge_base("./company_knowledge_base"))
    print(status)
    
    # 2. Test queries
    print("\n[Step 2] Testing Semantic Knowledge Graph Queries...")
    test_queries = [
        "What is the standard enterprise hurdle rate?",
        "What are the pricing tiers and starter plan details?",
        "What are the guidelines for marketing calls to action?"
    ]
    
    for q in test_queries:
        print(f"\nQuery: '{q}'")
        res = search_enterprise_memory.invoke(q) if hasattr(search_enterprise_memory, "invoke") else search_enterprise_memory(q)
        print(f"Memory Recall:\n{res}")
