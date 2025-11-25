"""Orchestrator Agent - Main coordinator for routing requests and managing subagent interactions"""

from typing import Dict, Any, Optional


class OrchestratorAgent:
    """
    Main coordinator that routes user recycling queries to appropriate subagents
    and aggregates results for final recommendation.
    """

    def __init__(self, memory_service: Optional[Any] = None):
        """
        Initialize the orchestrator with references to subagents and memory service.

        Args:
            memory_service: Optional MemoryService instance for long-term memory
        """
        self.product_intelligence = None  # ProductIntelligenceAgent
        self.location = None  # LocationAgent
        self.synthesis = None  # SynthesisAgent
        self.memory_service = memory_service  # MemoryService for storing/retrieving past interactions

    def process_request(self, user_query: str, user_location: str = None, request_type: str = "recyclability_check") -> Dict[str, Any]:
        """
        Process user recycling query through the multi-agent pipeline.

        Args:
            user_query: User's recycling question (e.g., "Is this PETE #1 bottle recyclable?")
            user_location: User's location for local recycling rules
            request_type: Type of request - "location_setup", "location_update", or "recyclability_check"

        Returns:
            Dict containing recyclability analysis and recommendations
        """
        # Handle location setup/update requests
        if request_type in ["location_setup", "location_update"]:
            return self._handle_location_setup(user_location, is_update=(request_type == "location_update"))

        # Handle recyclability check requests
        return self._handle_recyclability_check(user_query, user_location)

    def _handle_location_setup(self, user_location: str, is_update: bool = False) -> Dict[str, Any]:
        """
        Handle location setup or update by calling Location Agent and saving to memory.

        Args:
            user_location: User's location (city, state or zip code)
            is_update: True if updating existing location, False if first-time setup

        Returns:
            Dict containing location data and recycling facility information
        """
        if not user_location:
            return {
                "status": "error",
                "message": "No location provided. Please enter your city or zip code."
            }

        # Call Location Agent to get recycling facility information
        # TODO: Location Agent will implement get_recycling_info() method
        if not self.location:
            return {
                "status": "error",
                "message": "Location agent not initialized"
            }

        try:
            # Get recycling facility data from Location Agent
            location_data = self.location.get_recycling_info(user_location)

            if not location_data or location_data.get("status") == "error":
                return {
                    "status": "error",
                    "message": f"Could not find recycling information for {user_location}. Please check your location and try again."
                }

            # Save location data to long-term memory
            if self.memory_service:
                session_data = {
                    "query_type": "location_update" if is_update else "location_setup",
                    "user_location": user_location,
                    "location_data": location_data,
                    "action": "updated location" if is_update else "initial setup"
                }

                metadata = {
                    "agent": "location_agent",
                    "zip_code": location_data.get("zip_code"),
                    "municipality": location_data.get("municipality"),
                    "state": location_data.get("state"),
                    "query_type": "location_setup"
                }

                self.memory_service.add_session_to_memory(
                    session_data=session_data,
                    user_id=user_location,
                    metadata=metadata
                )

            # Return success with location data
            return {
                "status": "success",
                "message": self._format_location_response(location_data, is_update),
                "location_data": location_data,
                "handled_by": ["location_agent"]
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Error retrieving location information: {str(e)}"
            }

    def _format_location_response(self, location_data: Dict[str, Any], is_update: bool = False) -> str:
        """
        Format location data into user-friendly response.

        Args:
            location_data: Location and recycling facility data from Location Agent
            is_update: Whether this is an update or initial setup

        Returns:
            Formatted string response for user
        """
        action = "updated" if is_update else "set up"
        municipality = location_data.get("municipality", "your area")
        state = location_data.get("state", "")
        location_str = f"{municipality}, {state}" if state else municipality

        authority = location_data.get("local_authority", {})
        curbside = location_data.get("curbside_recycling", {})

        response = f"✅ Location {action}! You're in **{location_str}**.\n\n"
        response += f"**Your Local Recycling Program:**\n"

        if authority:
            response += f"- Provider: {authority.get('name', 'N/A')}\n"
            if authority.get('website'):
                response += f"- Website: {authority.get('website')}\n"
            if authority.get('phone'):
                response += f"- Phone: {authority.get('phone')}\n"

        response += f"\n**Curbside Recycling Accepts:**\n"
        accepts = curbside.get("accepts", [])
        if accepts:
            for item in accepts[:5]:  # Show first 5 items
                response += f"- ✅ {item}\n"
            if len(accepts) > 5:
                response += f"- ...and {len(accepts) - 5} more items\n"

        response += f"\n**Not Accepted:**\n"
        rejects = curbside.get("rejects", [])
        if rejects:
            for item in rejects[:3]:  # Show first 3 items
                response += f"- ❌ {item}\n"
            if len(rejects) > 3:
                response += f"- ...and {len(rejects) - 3} more items\n"

        response += f"\n💡 Now you can ask me about specific items to see if they're recyclable in your area!"

        return response

    def _handle_recyclability_check(self, user_query: str, user_location: str) -> Dict[str, Any]:
        """
        Handle recyclability check by coordinating Product Intelligence, Location (via memory), and Synthesis agents.

        Args:
            user_query: User's question about an item
            user_location: User's location

        Returns:
            Dict containing recyclability verdict and response
        """
        if not user_query:
            return {
                "status": "error",
                "message": "Please provide an item to check for recyclability."
            }

        if not user_location:
            return {
                "status": "error",
                "message": "Location not set. Please set up your location first."
            }

        try:
            # Step 1: Call Product Intelligence Agent to identify material
            # Using the existing analyze_item() method
            if not self.product_intelligence:
                return {
                    "status": "error",
                    "message": "Product Intelligence agent not initialized"
                }

            material_info = self.product_intelligence.analyze_item(item_description=user_query)

            # Check if implementation is complete
            if material_info.get("status") == "not_implemented":
                return {
                    "status": "not_implemented",
                    "message": "Product Intelligence Agent not yet implemented. The agent needs to analyze items and identify materials."
                }

            # Step 2: Retrieve location data from memory
            if not self.memory_service:
                return {
                    "status": "error",
                    "message": "Memory service not available. Cannot retrieve location data."
                }

            # Search memory for location data
            location_memories = self.memory_service.search_memory(
                user_id=user_location,
                filters={"agent": "location_agent"},
                limit=1
            )

            if not location_memories:
                # Fallback: try to get location data directly from Location Agent
                if self.location:
                    location_data = self.location.get_recycling_info(user_location)
                    if location_data.get("status") == "error":
                        return {
                            "status": "error",
                            "message": f"No recycling information found for {user_location}. Please update your location."
                        }
                else:
                    return {
                        "status": "error",
                        "message": "No location data found in memory. Please set up your location first."
                    }
            else:
                # Get location data from memory
                location_data = location_memories[0].get("session_data", {}).get("location_data", {})

            # Step 3: Call Synthesis Agent to generate response
            # Using the existing generate_recommendation() method
            if not self.synthesis:
                return {
                    "status": "error",
                    "message": "Synthesis agent not initialized"
                }

            synthesis_result = self.synthesis.generate_recommendation(
                material_info=material_info,
                recyclability_info=location_data
            )

            # Check if implementation is complete
            if synthesis_result.get("status") == "not_implemented":
                return {
                    "status": "not_implemented",
                    "message": "Synthesis Agent not yet implemented. The agent needs to generate recommendations based on material and location data."
                }

            # Format the response from synthesis result
            response_message = synthesis_result.get("recommendation", "No recommendation generated")

            return {
                "status": "success",
                "message": response_message,
                "material_info": material_info,
                "location_checked": location_data.get("municipality", "your area"),
                "handled_by": ["product_intelligence", "synthesis"]
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Error processing recyclability check: {str(e)}"
            }

    def initialize_agents(self, product_intelligence, location, synthesis):
        """
        Initialize subagent references.

        Args:
            product_intelligence: ProductIntelligenceAgent instance
            location: LocationAgent instance
            synthesis: SynthesisAgent instance
        """
        self.product_intelligence = product_intelligence
        self.location = location
        self.synthesis = synthesis

    def save_to_memory(
        self,
        user_query: str,
        response: str,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Helper method to save interaction to long-term memory.

        Args:
            user_query: The user's question or request
            response: The assistant's response
            user_id: Optional user identifier
            metadata: Optional metadata (location, tags, etc.)

        Returns:
            True if successfully saved, False otherwise
        """
        if not self.memory_service:
            return False

        session_data = {
            "user_query": user_query,
            "assistant_response": response,
            "agent_type": "orchestrator"
        }

        return self.memory_service.add_session_to_memory(
            session_data=session_data,
            user_id=user_id,
            metadata=metadata
        )

    def retrieve_relevant_memories(
        self,
        query: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 5
    ) -> list:
        """
        Helper method to retrieve relevant past interactions from memory.

        Args:
            query: Optional search query
            user_id: Optional user filter
            limit: Maximum number of memories to retrieve

        Returns:
            List of relevant memory entries
        """
        if not self.memory_service:
            return []

        return self.memory_service.search_memory(
            query=query,
            user_id=user_id,
            limit=limit
        )
