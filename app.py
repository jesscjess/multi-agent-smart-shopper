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
            # Call orchestrator to get recycling facility info and save to memory
            with st.spinner("Looking up recycling information for your area..."):
                result = st.session_state.orchestrator.process_request(
                    user_query="location_setup",
                    user_location=location_input,
                    request_type="location_setup"
                )

            if result.get("status") == "success":
                # Save location to profile
                st.session_state.user_profile["location"] = location_input
                location_data = result.get("location_data", {})
                st.session_state.user_profile["zip_code"] = location_data.get("zip_code")
                st.session_state.user_profile["setup_complete"] = True

                # Display location information
                st.success(result.get("message"))
                st.rerun()
            else:
                st.error(result.get("message", "Failed to retrieve location information"))
        elif submitted:
            st.error("Please enter a valid location")

# Main chat interface (only show if profile is set up)
if st.session_state.user_profile["setup_complete"]:
    # Display current location in sidebar
    with st.sidebar:
        st.header("Your Profile")
        st.write(f"📍 **Location:** {st.session_state.user_profile['location']}")

        # Initialize location update state
        if "updating_location" not in st.session_state:
            st.session_state.updating_location = False

        if st.button("Change Location"):
            st.session_state.updating_location = not st.session_state.updating_location

        # Show location update form if button clicked
        if st.session_state.updating_location:
            with st.form("location_update_form"):
                new_location = st.text_input(
                    "New location",
                    placeholder="e.g., Portland, OR or 97201"
                )
                update_submitted = st.form_submit_button("Update")

                if update_submitted and new_location:
                    with st.spinner("Updating location and retrieving recycling info..."):
                        result = st.session_state.orchestrator.process_request(
                            user_query="location_update",
                            user_location=new_location,
                            request_type="location_update"
                        )

                    if result.get("status") == "success":
                        st.session_state.user_profile["location"] = new_location
                        location_data = result.get("location_data", {})
                        st.session_state.user_profile["zip_code"] = location_data.get("zip_code")
                        st.session_state.updating_location = False
                        st.success("Location updated successfully!")
                        st.rerun()
                    else:
                        st.error(result.get("message", "Failed to update location"))
                elif update_submitted:
                    st.error("Please enter a valid location")

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
                # Process request through orchestrator with user location
                result = st.session_state.orchestrator.process_request(
                    user_query=prompt,
                    user_location=st.session_state.user_profile.get("location")
                )

                # Get response from result
                response = result.get("message", "Something went wrong")

                st.markdown(response)

        # Add assistant message to chat history
        st.session_state.messages.append({"role": "assistant", "content": response})

        # NOTE: We do NOT save recyclability checks to memory
        # Only location agent responses are saved 

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
