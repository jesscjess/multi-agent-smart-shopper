# agents/orchestrator.py
"""
Orchestrator Agent - Coordinates the EcoScan workflow for Streamlit
"""
from typing import Dict, Any, Optional
from google.adk import Agent
from google.adk.models import Gemini
from google.adk.runners import InMemoryRunner
from config.settings import settings
import json
import asyncio
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types


def create_orchestrator_agent() -> Agent:
    """Factory function to create the intent-parsing orchestrator agent."""
    return Agent(
        name="IntentOrchestratorAgent",
        model=Gemini(
            model=settings.DEFAULT_MODEL,
        ),
        description="Analyzes user queries to determine intent and extract product information for recycling guidance.",
        instruction="""
        You are an intent analyzer for EcoScan, a recycling guidance system.

        Your job is to understand what the user is asking and extract relevant information.

        ## Response Format:

        **For product/recyclability queries:**
        ```json
        {
        "intent": "check_recyclability",
        "product": "extracted product name or description",
        "confidence": 0.95
        }
        ```

        **For general questions:**
        ```json
        {
        "intent": "general_question",
        "question_type": "how_to_recycle|what_is_ric|local_info",
        "details": "extracted details"
        }
        ```

        **For unclear input:**
        ```json
        {
        "intent": "unclear",
        "message": "What would you like to know about recycling?"
        }
        ```

        ## Rules:
        - Extract the most specific product name/description possible
        - Identify plastic codes if mentioned (e.g., "#1", "PETE", "PS #6")
        - Be conversational but always respond in valid JSON format
        - Handle casual language naturally
        """,
        tools=[]
    )


class OrchestratorAgent:
    """
    Main orchestrator that coordinates between agents and manages workflow.
    Designed to work with Streamlit's synchronous interface.
    """
    
    def __init__(self, memory_service=None):
        """
        Initialize the orchestrator.
        
        Args:
            memory_service: MemoryService instance for storing/retrieving data
        """
        self.memory_service = memory_service
        self.product_agent = None
        self.location_agent = None
        self.synthesis_agent = None
        
        # Initialize intent parsing agent - UPDATED
        self._setup_intent_agent()

    def _setup_intent_agent(self):
        """Set up the intent parsing ADK agent."""
        self.intent_agent_def = create_orchestrator_agent()

        # Create session service and runner for intent agent
        self.intent_session_service = InMemorySessionService()
        self.intent_runner = Runner(
            agent=self.intent_agent_def,
            app_name="agent",
            session_service=self.intent_session_service
        )

        self.INTENT_USER_ID = "user_intent"
        self.INTENT_SESSION_ID = "session_intent"

        # Create session immediately during initialization (async call)
        asyncio.run(self.intent_session_service.create_session(
            app_name="agent",
            user_id=self.INTENT_USER_ID,
            session_id=self.INTENT_SESSION_ID
        ))
    
    def initialize_agents(
        self,
        product_agent,
        location_agent,
        synthesis_agent
    ):
        """
        Initialize specialized agents.
        
        Args:
            product_agent: ProductIntelligenceAgent instance
            location_agent: LocationAgent instance
            synthesis_agent: SynthesisAgent instance
        """
        self.product_agent = product_agent
        self.location_agent = location_agent
        self.synthesis_agent = synthesis_agent
    
    def _run_intent_agent(self, user_query: str) -> Any:
        """Run the intent agent synchronously."""
        runner = InMemoryRunner(agent=self.intent_agent_def)
        
        try:
            result = asyncio.run(runner.run(user_query))
            return result
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(runner.run(user_query))
                return result
            finally:
                loop.close()
    
    async def _execute_intent_agent(self, user_query: str):
        """Internal async execution for intent agent."""
        # Session was already created in __init__

        # Create message
        message = types.Content(role="user", parts=[types.Part(text=user_query)])

        # Run and get response
        async for event in self.intent_runner.run_async(
            user_id=self.INTENT_USER_ID,
            session_id=self.INTENT_SESSION_ID,
            new_message=message
        ):
            if event.is_final_response():
                response_text = event.content.parts[0].text
                return response_text

        # Fallback if no response
        return "{}"
    
    def _run_intent_agent(self, user_query: str):
        """Run the intent agent synchronously."""
        try:
            result = asyncio.run(self._execute_intent_agent(user_query))
            return result
        except RuntimeError:
            # Event loop already running in Streamlit
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(self._execute_intent_agent(user_query))
                return result
            finally:
                loop.close()

    def process_request(
        self,
        user_query: str,
        user_location: Optional[str] = None,
        request_type: str = "recyclability_check"
    ) -> Dict[str, Any]:
        """
        Main entry point for processing user requests.
        Synchronous wrapper for Streamlit compatibility.
        
        Args:
            user_query: The user's question or input
            user_location: User's location (city or zip code)
            request_type: Type of request (recyclability_check, location_setup, location_update)
            
        Returns:
            Dict with status, message, and relevant data
        """
        try:
            # Handle location setup/update separately
            if request_type in ["location_setup", "location_update"]:
                return self._handle_location_request(user_location, request_type)
            
            # Handle recyclability checks
            return self._handle_recyclability_check(user_query, user_location)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                'status': 'error',
                'message': f'An error occurred: {str(e)}'
            }
    
    def _handle_location_request(
        self,
        location: str,
        request_type: str
    ) -> Dict[str, Any]:
        """
        Handle location setup or update requests.
        
        Args:
            location: User's location input
            request_type: "location_setup" or "location_update"
            
        Returns:
            Dict with status and location data
        """
        try:
            # Extract zip code if needed
            zip_code = self._extract_zip_code(location)
            
            if not zip_code:
                return {
                    'status': 'error',
                    'message': 'Please provide a valid 5-digit zip code (e.g., 94102).'
                }
            
            # Query location agent
            print(f"📍 Looking up recycling info for: {zip_code}")
            location_result = self.location_agent.run(zip_code)
            location_data = self._parse_json_response(location_result)
            
            if not location_data.get('success', True):
                return {
                    'status': 'error',
                    'message': f"Unable to find recycling information for {location}. {location_data.get('error', '')}"
                }
            
            # Save to memory
            if self.memory_service:
                self.memory_service.add_session_to_memory(
                    session_data=location_data,
                    user_id="default_user",
                    metadata={"type": "location_data", "zip_code": zip_code}
                )
            
            # Format success message
            municipality = location_data.get('municipality', location)
            state = location_data.get('state', '')
            location_str = f"{municipality}, {state}" if state else municipality
            
            authority = location_data.get('local_authority', {})
            authority_name = authority.get('name', 'your local recycling center')
            
            message = f"""
✅ **Location saved: {location_str}**

Your recycling is managed by **{authority_name}**.

I'm ready to help you check if specific items are recyclable in your area!
"""
            
            return {
                'status': 'success',
                'message': message.strip(),
                'location_data': location_data
            }
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                'status': 'error',
                'message': f'Error processing location: {str(e)}'
            }
    
    def _handle_recyclability_check(
        self,
        user_query: str,
        user_location: Optional[str]
    ) -> Dict[str, Any]:
        """
        Handle recyclability check requests.
        
        Args:
            user_query: User's question about recyclability
            user_location: User's saved location
            
        Returns:
            Dict with status and recommendation
        """
        try:
            # Step 1: Parse intent
            print("🎯 Step 1: Analyzing user intent...")
            intent_result = self._run_intent_agent(user_query)
            intent_data = self._parse_json_response(intent_result)
            
            intent = intent_data.get('intent')
            
            # Handle general questions
            if intent == 'general_question':
                return self._handle_general_question(intent_data)
            
            # Handle unclear intent
            if intent == 'unclear':
                return {
                    'status': 'needs_clarification',
                    'message': intent_data.get('message', 
                        'What would you like to know about recycling? You can ask about specific products or plastic codes.')
                }
            
            # Extract product info
            product = intent_data.get('product')
            if not product:
                return {
                    'status': 'needs_info',
                    'message': 'What item would you like to check for recyclability?'
                }
            
            # Step 2: Get product information
            print(f"🔍 Step 2: Analyzing product: {product}")
            product_result = self.product_agent.run(product)
            product_data = self._parse_json_response(product_result)
            
            if not product_data.get('success', True):
                return {
                    'status': 'error',
                    'message': f"I couldn't find specific recycling information for '{product}'. Could you provide more details or try a different product name?"
                }
            
            # Step 3: Get location data from memory
            print(f"📍 Step 3: Checking local recycling rules...")
            location_data = self._get_location_data(user_location)
            
            if not location_data:
                return {
                    'status': 'needs_location',
                    'message': 'I need your location to provide accurate recycling information. Please update your location in the sidebar.'
                }
            
            # Step 4: Synthesize recommendation
            print("🔄 Step 4: Generating recommendation...")
            synthesis_result = self.synthesis_agent.run(
                product_info=product_data,
                location_info=location_data
            )
            
            # Format response for Streamlit
            formatted_response = synthesis_result.get('recommendation', '')
            if synthesis_result.get('details'):
                formatted_response = synthesis_result['details'].get('formatted_response', formatted_response)
            
            return {
                'status': 'success',
                'message': formatted_response,
                'product_data': product_data,
                'location_data': location_data,
                'recommendation': synthesis_result
            }
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                'status': 'error',
                'message': f'Error processing request: {str(e)}'
            }
    
    def _handle_general_question(self, intent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle general questions about recycling."""
        question_type = intent_data.get('question_type')
        
        responses = {
            'what_is_ric': """
## Understanding Resin Identification Codes (RIC)

RIC codes are the numbers (1-7) inside the recycling triangle symbol on plastic products. They identify the type of plastic resin:

- **#1 PETE/PET**: Polyethylene Terephthalate (water bottles, soda bottles)
- **#2 HDPE**: High-Density Polyethylene (milk jugs, detergent bottles)
- **#3 PVC**: Polyvinyl Chloride (pipes, some packaging)
- **#4 LDPE**: Low-Density Polyethylene (plastic bags, squeeze bottles)
- **#5 PP**: Polypropylene (yogurt containers, bottle caps)
- **#6 PS**: Polystyrene (foam cups, takeout containers)
- **#7 Other**: All other plastics (mixed materials)

⚠️ **Important**: Just because something has a recycling symbol doesn't mean it's accepted in your local recycling program!
""",
            'how_to_recycle': """
## How to Recycle Properly

1. **Check local guidelines** - What's recyclable varies by location
2. **Clean containers** - Rinse food residue
3. **Remove caps/lids** - Unless guidelines say otherwise
4. **Flatten when possible** - Saves space
5. **Don't bag recyclables** - Keep them loose in the bin
6. **When in doubt, throw it out** - Contamination hurts recycling

Ask me about a specific item to get detailed guidance for your area!
"""
        }
        
        message = responses.get(question_type, 
            "I can help you check if specific items are recyclable in your area. What would you like to know?")
        
        return {
            'status': 'success',
            'message': message
        }
    
    def _get_location_data(self, user_location: Optional[str]) -> Optional[Dict[str, Any]]:
        """Get location data from memory service."""
        if not self.memory_service:
            return None

        # Search for most recent location data for this user
        results = self.memory_service.search_memory(
            user_id="default_user",
            limit=1,
            filters={"type": "location_data"}
        )

        if results:
            return results[0].get("session_data")

        return None
    
    def _extract_zip_code(self, location: str) -> Optional[str]:
        """Extract or lookup zip code from location string."""
        import re
        
        # Check if it's already a zip code
        zip_match = re.search(r'\b\d{5}\b', location)
        if zip_match:
            return zip_match.group()
        
        # For MVP, require explicit zip code
        return None
    
    def _parse_json_response(self, response: Any) -> Dict[str, Any]:
        """Parse JSON response from agents."""
        try:
            if isinstance(response, dict):
                return response
            
            response_str = str(response).strip()
            
            # Remove markdown code blocks
            if '```json' in response_str or '```' in response_str:
                response_str = response_str.replace('```json', '').replace('```', '').strip()
            
            return json.loads(response_str)
            
        except json.JSONDecodeError:
            return {'success': False, 'error': 'Unable to parse response'}