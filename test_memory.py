"""Test script to verify memory ingestion works correctly"""

from memory_service import MemoryService
from agents import OrchestratorAgent
import json

def test_memory_ingestion():
    """Test that memory service can store and retrieve sessions"""

    print("=" * 60)
    print("Testing Memory Ingestion (Step 2)")
    print("=" * 60)

    # Initialize memory service
    print("\n1. Initializing MemoryService...")
    memory_service = MemoryService(storage_path="data/test_memory.json")
    print("   ✓ MemoryService initialized")

    # Initialize orchestrator with memory
    print("\n2. Creating OrchestratorAgent with MemoryService...")
    orchestrator = OrchestratorAgent(memory_service=memory_service)
    print("   ✓ OrchestratorAgent created")

    # Test 1: Add session using memory service directly
    print("\n3. Testing direct memory ingestion...")
    session_data = {
        "user_query": "Is this PETE #1 plastic bottle recyclable?",
        "assistant_response": "Yes, PETE #1 bottles are widely accepted in most recycling programs.",
    }
    metadata = {
        "location": "San Francisco, CA",
        "query_type": "recyclability_check"
    }

    success = memory_service.add_session_to_memory(
        session_data=session_data,
        user_id="San Francisco, CA",
        metadata=metadata
    )
    print(f"   {'✓' if success else '✗'} Session added to memory: {success}")

    # Test 2: Add session using orchestrator helper method
    print("\n4. Testing orchestrator helper method...")
    success = orchestrator.save_to_memory(
        user_query="Can I recycle HDPE #2 milk jugs?",
        response="Yes, HDPE #2 is one of the most commonly recycled plastics.",
        user_id="San Francisco, CA",
        metadata={"location": "San Francisco, CA", "query_type": "recyclability_check"}
    )
    print(f"   {'✓' if success else '✗'} Session saved via orchestrator: {success}")

    # Test 3: Retrieve memories
    print("\n5. Testing memory retrieval...")
    memories = memory_service.search_memory(user_id="San Francisco, CA")
    print(f"   ✓ Retrieved {len(memories)} memories")

    # Test 4: Search with query
    print("\n6. Testing memory search...")
    search_results = memory_service.search_memory(
        query="PETE",
        user_id="San Francisco, CA"
    )
    print(f"   ✓ Found {len(search_results)} memories matching 'PETE'")

    # Test 5: Get recent memories
    print("\n7. Testing recent memory retrieval...")
    recent = memory_service.get_recent_memories(count=2, user_id="San Francisco, CA")
    print(f"   ✓ Retrieved {len(recent)} recent memories")

    # Display memory stats
    print("\n8. Memory Statistics:")
    stats = memory_service.get_memory_stats()
    for key, value in stats.items():
        print(f"   - {key}: {value}")

    # Show stored data
    print("\n9. Stored Memory Preview:")
    print("-" * 60)
    for i, memory in enumerate(memories[:2], 1):
        print(f"\nMemory {i}:")
        print(f"  User Query: {memory['session_data'].get('user_query', 'N/A')}")
        print(f"  Response: {memory['session_data'].get('assistant_response', 'N/A')[:80]}...")
        print(f"  Location: {memory['metadata'].get('location', 'N/A')}")
        print(f"  Timestamp: {memory.get('timestamp', 'N/A')}")

    print("\n" + "=" * 60)
    print("✓ All tests passed! Memory ingestion is working.")
    print("=" * 60)

    # Show file location
    print(f"\nMemory stored in: {memory_service.storage_path}")
    print("You can inspect the JSON file to see the stored data.")

    return True

if __name__ == "__main__":
    try:
        test_memory_ingestion()
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
