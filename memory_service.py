"""Memory Service for long-term agent memory storage and retrieval"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import json


class MemoryService:
    """
    Long-term memory service for storing and retrieving agent session data.

    This service follows the three-step integration pattern:
    1. Initialize - Create MemoryService and provide to agents
    2. Ingest - Transfer session data to memory using add_session_to_memory()
    3. Retrieve - Search stored memories using search_memory()
    """

    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize the memory service.

        Args:
            storage_path: Optional path to persistent storage file
        """
        self.storage_path = storage_path or "memory_store.json"
        self.memories: List[Dict[str, Any]] = []
        self._load_memories()

    def _load_memories(self):
        """Load memories from persistent storage if available"""
        try:
            with open(self.storage_path, 'r') as f:
                self.memories = json.load(f)
        except FileNotFoundError:
            # No existing memory file, start fresh
            self.memories = []
        except json.JSONDecodeError:
            # Corrupted file, start fresh
            self.memories = []

    def _save_memories(self):
        """Save memories to persistent storage"""
        try:
            with open(self.storage_path, 'w') as f:
                json.dump(self.memories, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to save memories: {e}")

    def add_session_to_memory(
        self,
        session_data: Dict[str, Any],
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Ingest session data into long-term memory.

        Args:
            session_data: The session conversation or interaction data to store
            user_id: Optional user identifier for personalized memory
            metadata: Optional additional metadata (location, tags, etc.)

        Returns:
            True if successfully added, False otherwise
        """
        try:
            memory_entry = {
                "timestamp": datetime.now().isoformat(),
                "user_id": user_id,
                "session_data": session_data,
                "metadata": metadata or {}
            }

            self.memories.append(memory_entry)
            self._save_memories()
            return True
        except Exception as e:
            print(f"Error adding session to memory: {e}")
            return False

    def search_memory(
        self,
        query: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search and retrieve stored memories.

        Args:
            query: Optional search query to match against memory content
            user_id: Optional filter by specific user
            limit: Maximum number of results to return
            filters: Optional additional filters (e.g., date range, metadata tags)

        Returns:
            List of matching memory entries
        """
        results = []

        for memory in self.memories:
            # Filter by user_id if provided
            if user_id and memory.get("user_id") != user_id:
                continue

            # Apply custom filters if provided
            if filters:
                match = True
                for key, value in filters.items():
                    if key in memory.get("metadata", {}) and memory["metadata"][key] != value:
                        match = False
                        break
                if not match:
                    continue

            # If query provided, search in session data
            if query:
                session_str = json.dumps(memory.get("session_data", {})).lower()
                if query.lower() not in session_str:
                    continue

            results.append(memory)

            # Limit results
            if len(results) >= limit:
                break

        return results

    def get_recent_memories(self, count: int = 5, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieve the most recent memories.

        Args:
            count: Number of recent memories to retrieve
            user_id: Optional filter by specific user

        Returns:
            List of recent memory entries
        """
        filtered_memories = self.memories

        if user_id:
            filtered_memories = [m for m in self.memories if m.get("user_id") == user_id]

        # Sort by timestamp (most recent first) and return top N
        sorted_memories = sorted(
            filtered_memories,
            key=lambda x: x.get("timestamp", ""),
            reverse=True
        )

        return sorted_memories[:count]

    def clear_memory(self, user_id: Optional[str] = None):
        """
        Clear memories, optionally filtered by user.

        Args:
            user_id: If provided, only clear memories for this user
        """
        if user_id:
            self.memories = [m for m in self.memories if m.get("user_id") != user_id]
        else:
            self.memories = []

        self._save_memories()

    def get_memory_stats(self) -> Dict[str, Any]:
        """
        Get statistics about stored memories.

        Returns:
            Dictionary with memory statistics
        """
        return {
            "total_memories": len(self.memories),
            "unique_users": len(set(m.get("user_id") for m in self.memories if m.get("user_id"))),
            "oldest_memory": self.memories[0].get("timestamp") if self.memories else None,
            "newest_memory": self.memories[-1].get("timestamp") if self.memories else None
        }
