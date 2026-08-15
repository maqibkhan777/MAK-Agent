import os
import json
import threading
from typing import Dict, Any, List, Optional
import db_manager
from key_vault import vault

try:
    from langchain_groq import ChatGroq
    from langchain_core.messages import SystemMessage, HumanMessage
except ImportError:
    ChatGroq = None


class CognitiveMemoryEngine:
    """
    Manages long-term conversational memory, episodic dialogue history,
    and adaptive user persona impression formation.
    """

    def __init__(self):
        db_manager.init_db()

    def get_cognitive_context(self, session_id: str = "default") -> str:
        """
        Synthesizes active user impressions, learned preferences, and recent multi-turn
        dialogue into a prompt injection block for LangGraph agents.
        """
        profile = db_manager.get_user_profile("primary_user")
        history = db_manager.get_recent_chat_history(session_id=session_id, limit=10)

        lines = ["\n[COGNITIVE MEMORY & USER IMPRESSION PROFILE]"]

        if profile:
            lines.append(f"• User Impression: {profile.get('summary_impression', 'N/A')}")
            lines.append(f"• Technical Level: {profile.get('technical_level', 'Expert')}")
            lines.append(f"• Tone & Formatting Preference: {profile.get('preferred_tone', 'Concise, structured')}")
            prefs = profile.get("key_preferences", [])
            if prefs:
                lines.append("• Key Learned Preferences:")
                for p in prefs[:6]:
                    lines.append(f"   - {p}")
            projects = profile.get("active_projects", [])
            if projects:
                lines.append(f"• Active Work Context: {', '.join(projects)}")
            lines.append(f"• Interaction Experience: {profile.get('total_interactions', 1)} sessions logged")

        if history:
            lines.append("\n[RECENT MULTI-TURN CONVERSATION HISTORY (Context Continuity)]:")
            for turn in history:
                u_text = turn.get('user_prompt', '').strip()
                a_text = turn.get('agent_response', '').strip()
                # Preserve essential context while preventing excessive token explosion
                if len(u_text) > 500:
                    u_text = u_text[:500] + "..."
                if len(a_text) > 800:
                    a_text = a_text[:800] + "..."
                dept = turn.get('department_used', 'agent')
                lines.append(f"User: {u_text}")
                lines.append(f"MAK ({dept}): {a_text}\n")

        lines.append("[END OF COGNITIVE MEMORY]\n")
        return "\n".join(lines)

    def record_turn(
        self,
        session_id: str,
        user_prompt: str,
        agent_response: str,
        department_used: str = "general_ops"
    ):
        """
        Saves conversation turn and triggers background impression reflection.
        """
        try:
            # 1. Save to SQLite database
            db_manager.save_chat_turn(
                session_id=session_id,
                user_prompt=user_prompt,
                agent_response=agent_response,
                department_used=department_used
            )

            # 2. Trigger asynchronous persona impression updater
            threading.Thread(
                target=self._reflect_and_update_impression,
                args=(user_prompt, agent_response),
                daemon=True
            ).start()
        except Exception as e:
            print(f"[Memory Engine Error] Failed to record turn: {e}")

    def _reflect_and_update_impression(self, user_prompt: str, agent_response: str):
        """
        Analyzes conversation turn to incrementally evolve user persona impression.
        """
        try:
            profile = db_manager.get_user_profile("primary_user")
            total = profile.get("total_interactions", 0) + 1

            # Simple rule-based adaptive extraction + periodic LLM reflection
            current_prefs = profile.get("key_preferences", [])
            current_projects = profile.get("active_projects", [])

            # Check for domain keywords
            prompt_lower = user_prompt.lower()
            if "fastapi" in prompt_lower or "electron" in prompt_lower or "langgraph" in prompt_lower:
                if "MAK Enterprise AI Agency" not in current_projects:
                    current_projects.append("MAK Enterprise AI Agency")

            if "hyperlink" in prompt_lower or "citation" in prompt_lower or "concise" in prompt_lower:
                pref = "Values high-density structured responses with direct markdown hyperlinks"
                if pref not in current_prefs:
                    current_prefs.append(pref)

            if "local browser" in prompt_lower or "port 9222" in prompt_lower or "cdp" in prompt_lower:
                pref = "Utilizes local Chrome CDP debugging session on port 9222"
                if pref not in current_prefs:
                    current_prefs.append(pref)

            # Update impression summary
            db_manager.update_user_profile(
                summary_impression=profile.get("summary_impression"),
                key_preferences=current_prefs[:8],
                active_projects=current_projects[:6]
            )
        except Exception as e:
            print(f"[Impression Reflection Error]: {e}")

    def get_profile_data(self) -> Dict[str, Any]:
        """Returns the full user cognitive profile for UI inspection."""
        return db_manager.get_user_profile("primary_user")

    def clear_memory(self, session_id: Optional[str] = None):
        """Clears memory history."""
        db_manager.clear_chat_history(session_id)


# Global Singleton
memory = CognitiveMemoryEngine()
