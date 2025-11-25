"""EcoScan - Smart Recycling Assistant Chat Interface"""

import streamlit as st
from agents import (
    OrchestratorAgent,
    ProductIntelligenceAgent,
    LocationAgent,
    SynthesisAgent,
)
from memory_service import MemoryService

# Page configuration
st.set_page_config(
    page_title="EcoScan - Smart Recycling Assistant",
    page_icon="♻️",
    layout="centered"
)

# Initialize session state for conversation history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Initialize user profile
if "user_profile" not in st.session_state:
    st.session_state.user_profile = {
        "location": None,
        "zip_code": None,
        "setup_complete": False
    }

# Initialize agents and memory service (singleton pattern)
if "orchestrator" not in st.session_state:
    # Step 1: Initialize MemoryService
    memory_service = MemoryService(storage_path="data/ecoscan_memory.json")

    # Create specialized agents
    product_intelligence = ProductIntelligenceAgent()  # Material analysis
    location = LocationAgent()  # Local recycling rules
    synthesis = SynthesisAgent()  # Recommendations and tips

    # Create and initialize orchestrator with memory service
    orchestrator = OrchestratorAgent(memory_service=memory_service)
    orchestrator.initialize_agents(product_intelligence, location, synthesis)

    st.session_state.orchestrator = orchestrator
    st.session_state.memory_service = memory_service

# App header
st.title("♻️ EcoScan")
st.caption("Smart Recycling Assistant - Know what's actually recyclable in your area")

# User profile setup (if not completed)
if not st.session_state.user_profile["setup_complete"]:
    st.info("👋 Welcome to EcoScan! Please set up your profile to get started.")

    with st.form("profile_setup"):
        st.subheader("Profile Setup")
        st.write("We need your location to provide accurate recycling information for your area.")

        location_input = st.text_input(
            "Enter your city or zip code",
            placeholder="e.g., San Francisco, CA or 94102"
        )

        submitted = st.form_submit_button("Save Location")

        if submitted and location_input:
            st.session_state.user_profile["location"] = location_input
            st.session_state.user_profile["setup_complete"] = True
            st.success(f"✅ Profile saved! Location set to: {location_input}")
            st.rerun()
        elif submitted:
            st.error("Please enter a valid location")

# Main chat interface (only show if profile is set up)
if st.session_state.user_profile["setup_complete"]:
    # Display current location in sidebar
    with st.sidebar:
        st.header("Your Profile")
        st.write(f"📍 **Location:** {st.session_state.user_profile['location']}")

        if st.button("Change Location"):
            st.session_state.user_profile["setup_complete"] = False
            st.rerun()

        st.divider()

        st.header("About EcoScan")
        st.info(
            "EcoScan helps you determine if items are actually recyclable in your area. "
            "Many plastics labeled as recyclable aren't accepted by local programs."
        )

        st.header("How to Use")
        st.write("📝 **Describe the item:**")
        st.code("Is this PETE #1 plastic bottle recyclable?")

        st.write("📸 **Upload a photo:** (coming soon)")
        st.caption("Take a picture of the recycling symbol")

        st.divider()

        st.header("Common Plastic Codes")
        st.markdown("""
        - ♻️ **#1 PETE**: Water bottles (widely accepted)
        - ♻️ **#2 HDPE**: Milk jugs (widely accepted)
        - ⚠️ **#3 PVC**: Pipes (rarely accepted)
        - ⚠️ **#4 LDPE**: Plastic bags (special bins)
        - ✅ **#5 PP**: Yogurt cups (check locally)
        - ❌ **#6 PS**: Styrofoam (rarely accepted)
        - ❌ **#7 Other**: Mixed (usually not recyclable)
        """)

        st.divider()

        if st.button("Clear Chat History"):
            st.session_state.messages = []
            st.rerun()

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Image upload option (placeholder for future implementation)
    with st.expander("📸 Upload Image (Coming Soon)"):
        uploaded_file = st.file_uploader(
            "Take a photo of the recycling symbol or product",
            type=["jpg", "jpeg", "png"],
            disabled=True  # Will enable when image processing is implemented
        )
        st.caption("🚧 Image analysis will be available soon!")

    # Chat input
    if prompt := st.chat_input("What item would you like to check?"):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)

        # Get assistant response
        with st.chat_message("assistant"):
            with st.spinner("Analyzing recyclability..."):
                # Process request through orchestrator
                result = st.session_state.orchestrator.process_request(prompt)

                # Format response (temporary until agents are implemented)
                if result.get("status") == "not_implemented":
                    response = f"""I'm analyzing your item for recycling! ♻️

**Your query:** {prompt}
**Your location:** {st.session_state.user_profile['location']}

The EcoScan multi-agent system will:
1. 🔍 **Identify the material** type and plastic codes
2. 📍 **Check local rules** for your area
3. ✅ **Provide instructions** on how to recycle it properly

*Note: Agent implementation is in progress. Soon I'll provide accurate, location-specific recycling guidance!*

**Common tips while we're building:**
- PETE #1 and HDPE #2 are widely accepted
- Always rinse containers before recycling
- Remove caps and labels when possible
- When in doubt, check your local recycling program
"""
                else:
                    response = result.get("message", "Something went wrong")

                st.markdown(response)

        # Add assistant message to chat history
        st.session_state.messages.append({"role": "assistant", "content": response})

        # Step 2: Ingest - Add session to memory
        session_data = {
            "user_query": prompt,
            "assistant_response": response,
            "timestamp": st.session_state.messages[-1].get("timestamp") if "timestamp" in st.session_state.messages[-1] else None,
            "conversation_context": {
                "message_count": len(st.session_state.messages),
                "session_id": id(st.session_state)  # Unique session identifier
            }
        }

        metadata = {
            "location": st.session_state.user_profile.get("location"),
            "zip_code": st.session_state.user_profile.get("zip_code"),
            "query_type": "recyclability_check"
        }

        # Store in long-term memory
        st.session_state.memory_service.add_session_to_memory(
            session_data=session_data,
            user_id=st.session_state.user_profile.get("location"),  # Using location as user_id for now
            metadata=metadata
        )

else:
    # Show welcome message if profile not set up
    st.write("")
    st.write("### Why EcoScan?")
    st.write(
        "Not all 'recyclable' plastics are actually recycled. "
        "Different cities accept different materials, and many items with recycling symbols "
        "aren't accepted by local programs. EcoScan provides accurate, location-specific guidance."
    )

    col1, col2 = st.columns(2)

    with col1:
        st.write("**✅ We help you:**")
        st.write("- Know what's recyclable near you")
        st.write("- Understand plastic codes")
        st.write("- Avoid contaminating recycling")
        st.write("- Make informed choices")

    with col2:
        st.write("**🌍 Impact:**")
        st.write("- Reduce waste")
        st.write("- Prevent contamination")
        st.write("- Support proper recycling")
        st.write("- Educate consumers")
