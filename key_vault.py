import os
import json
import time
import threading
from typing import Dict, List, Optional, Any

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "api_keys_config.json")

class KeyVault:
    """
    Thread-safe Multi-LLM API Key Pool & Failover Manager.
    Allows registering multiple API keys per provider (Groq, OpenAI, Anthropic, OpenRouter, Gemini).
    Automatically rotates to healthy backup keys when rate limits (429) or token quotas are reached.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(KeyVault, cls).__new__(cls)
                cls._instance._init_vault()
            return cls._instance

    def _init_vault(self):
        self.lock = threading.Lock()
        self.providers: Dict[str, Dict[str, Any]] = {
            "groq": {
                "keys": [],
                "current_index": 0,
                "key_stats": {},
                "env_var": "GROQ_API_KEY"
            },
            "openai": {
                "keys": [],
                "current_index": 0,
                "key_stats": {},
                "env_var": "OPENAI_API_KEY"
            },
            "openrouter": {
                "keys": [],
                "current_index": 0,
                "key_stats": {},
                "env_var": "OPENROUTER_API_KEY"
            },
            "anthropic": {
                "keys": [],
                "current_index": 0,
                "key_stats": {},
                "env_var": "ANTHROPIC_API_KEY"
            },
            "gemini": {
                "keys": [],
                "current_index": 0,
                "key_stats": {},
                "env_var": "GEMINI_API_KEY"
            }
        }
        self.load_from_storage()

    def load_from_storage(self):
        """Loads configured keys from api_keys_config.json and environment variables."""
        with self.lock:
            # 1. First seed with environment variables
            for prov, data in self.providers.items():
                env_val = os.getenv(data["env_var"])
                if env_val and env_val.strip():
                    for k in env_val.split(","):
                        k_clean = k.strip()
                        if k_clean and k_clean not in data["keys"]:
                            data["keys"].append(k_clean)

            # 2. Merge stored configuration if file exists
            if os.path.exists(CONFIG_FILE):
                try:
                    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                        saved = json.load(f)
                        for prov, keys in saved.items():
                            if prov in self.providers and isinstance(keys, list):
                                for k in keys:
                                    k_clean = str(k).strip()
                                    if k_clean and k_clean not in self.providers[prov]["keys"]:
                                        self.providers[prov]["keys"].append(k_clean)
                except Exception as e:
                    print(f"[KeyVault Notice] Error loading {CONFIG_FILE}: {e}")

            # Ensure current active keys are written to os.environ
            self._sync_env_variables_locked()

    def save_to_storage(self):
        """Persists keys to api_keys_config.json."""
        with self.lock:
            data_to_save = {prov: info["keys"] for prov, info in self.providers.items()}
            try:
                with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                    json.dump(data_to_save, f, indent=2)
            except Exception as e:
                print(f"[KeyVault Notice] Error saving {CONFIG_FILE}: {e}")

    def _sync_env_variables_locked(self):
        for prov, data in self.providers.items():
            if data["keys"]:
                idx = data["current_index"] % len(data["keys"])
                active_key = data["keys"][idx]
                os.environ[data["env_var"]] = active_key

    def get_active_key(self, provider: str = "groq") -> Optional[str]:
        """Returns the current active key for a provider."""
        with self.lock:
            p_data = self.providers.get(provider.lower())
            if not p_data or not p_data["keys"]:
                return os.getenv(p_data["env_var"] if p_data else "GROQ_API_KEY")
            idx = p_data["current_index"] % len(p_data["keys"])
            return p_data["keys"][idx]

    def rotate_key(self, provider: str = "groq", failed_key: Optional[str] = None, reason: str = "429 RateLimit") -> str:
        """
        Rotates to the next available key in the provider's pool upon rate limits.
        Returns the new active key.
        """
        with self.lock:
            p_data = self.providers.get(provider.lower())
            if not p_data or not p_data["keys"]:
                return os.getenv(p_data["env_var"] if p_data else "GROQ_API_KEY", "")

            keys = p_data["keys"]
            if len(keys) <= 1:
                print(f"[KeyVault Warning] Provider '{provider}' has only 1 key registered. Cannot rotate.")
                return keys[0]

            old_idx = p_data["current_index"]
            new_idx = (old_idx + 1) % len(keys)
            p_data["current_index"] = new_idx
            new_key = keys[new_idx]

            # Mark stats
            cur_time = time.time()
            if failed_key:
                stat = p_data["key_stats"].setdefault(failed_key, {"fail_count": 0, "last_fail": 0})
                stat["fail_count"] += 1
                stat["last_fail"] = cur_time

            os.environ[p_data["env_var"]] = new_key
            masked_old = self._mask_key(keys[old_idx])
            masked_new = self._mask_key(new_key)
            print(f"\n[KeyVault Failover Alert] Provider '{provider}' switched key from {masked_old} -> {masked_new} (Reason: {reason}) [Slot {new_idx+1}/{len(keys)}]\n")
            return new_key

    def update_provider_keys(self, provider: str, keys: List[str]):
        """Sets or replaces the key pool for a provider."""
        cleaned_keys = [str(k).strip() for k in keys if str(k).strip()]
        with self.lock:
            if provider.lower() in self.providers:
                self.providers[provider.lower()]["keys"] = cleaned_keys
                self.providers[provider.lower()]["current_index"] = 0
                self._sync_env_variables_locked()
        self.save_to_storage()

    def add_key(self, provider: str, key: str) -> bool:
        """Adds a single key to the pool."""
        clean = str(key).strip()
        if not clean:
            return False
        with self.lock:
            p_data = self.providers.get(provider.lower())
            if not p_data:
                return False
            if clean not in p_data["keys"]:
                p_data["keys"].append(clean)
                self._sync_env_variables_locked()
        self.save_to_storage()
        return True

    def remove_key(self, provider: str, key_index: int) -> bool:
        """Removes a key by index."""
        with self.lock:
            p_data = self.providers.get(provider.lower())
            if not p_data or key_index < 0 or key_index >= len(p_data["keys"]):
                return False
            p_data["keys"].pop(key_index)
            if p_data["current_index"] >= len(p_data["keys"]):
                p_data["current_index"] = max(0, len(p_data["keys"]) - 1)
            self._sync_env_variables_locked()
        self.save_to_storage()
        return True

    def get_status(self) -> Dict[str, Any]:
        """Returns sanitized status payload suitable for the UI settings modal."""
        with self.lock:
            summary = {}
            for prov, data in self.providers.items():
                keys = data["keys"]
                cur_idx = data["current_index"]
                masked_keys = [
                    {
                        "index": i,
                        "masked": self._mask_key(k),
                        "is_active": (i == (cur_idx % len(keys))) if keys else False,
                        "status": "healthy"
                    }
                    for i, k in enumerate(keys)
                ]
                summary[prov] = {
                    "total_keys": len(keys),
                    "active_index": cur_idx % len(keys) if keys else 0,
                    "env_var": data["env_var"],
                    "keys": masked_keys
                }
            return summary

    def get_vault_status(self) -> Dict[str, Any]:
        """Alias for get_status."""
        return self.get_status()

    @staticmethod
    def _mask_key(key: str) -> str:
        if not key:
            return ""
        if len(key) <= 8:
            return key[:2] + "..." + key[-2:]
        return key[:6] + "..." + key[-4:]

vault = KeyVault()
