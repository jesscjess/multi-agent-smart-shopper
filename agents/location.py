# agents/location.py
from google.adk.agents import Agent
from google.adk.models import Gemini
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from config.settings import settings
from google.adk.tools import google_search
import asyncio
import json


class LocationAgent:
    """Wrapper for the Location ADK agent."""
    
    def __init__(self):
        """Initialize the location agent."""
        self.agent = Agent(
            name="LocationAgent",
            model=Gemini(
                model=settings.DEFAULT_MODEL,
            ),
            description="An agent that takes a zip code, finds the assigned residential recycling store, provides recycling regulations and accepted RIC codes for that store.",
            instruction="""
**CRITICAL: You must respond with ONLY valid JSON. No markdown, no explanations, no additional text before or after the JSON.**

Your task:
1. Receive a zip code from the user
2. Search for the assigned residential recycling facility/program for that zip code
3. Find DETAILED recycling regulations including:
   - Which specific RIC codes are accepted (look for #1, #2, #3, #4, #5, #6, #7)
   - Which RIC codes are rejected
   - Specific preparation rules (caps on/off, rinsing, flattening, etc.)
   - Any material-specific instructions
4. Return ONLY the JSON response (no markdown code blocks, no text)

**Search Strategy:**
- Look for "[zip code] recycling guidelines"
- Look for "[municipality name] curbside recycling rules"
- Look for the waste management company or local government recycling page
- Find specific information about caps/lids, rinsing, and preparation requirements

**If the zip code is invalid, return ONLY this JSON:**
{"success": false, "error": "Reason it failed"}

**If successful, return ONLY this JSON structure:**
{
  "zip_code": "zipcode of the user",
  "municipality": "municipality of that zipcode",
  "state": "which state does this zipcode belong to",
  "local_authority": {
    "name": "name of the waste management company or local recycling program",
    "website": "official recycling guidelines website",
    "phone": "customer service phone number"
  },
  "curbside_recycling": {
    "accepts": ["PET #1", "HDPE #2", "PP #5"],
    "rejects": ["PVC #3", "PS #6", "OTHER #7"],
    "special_instructions": "Any special instructions for recycling"
  },
  "confidence": 0.85
}

Rules:
- DO NOT use markdown code blocks (no ```json or ```)
- DO NOT add any explanatory text before or after the JSON
- Confidence must be a number between 0 and 1 (e.g., 0.85, not "0.85")
- The "special_instructions" should be SPECIFIC - find actual local rules, not generic advice
- If you cannot find complete information, fill in what you can and set confidence lower
- Only respond in English
""",
            tools=[google_search]
        )
        
        # Create session service and runner
        self.session_service = InMemorySessionService()
        self.runner = Runner(
            agent=self.agent,
            app_name="agents",
            session_service=self.session_service
        )
        
        self.USER_ID = "user_location"
        self.SESSION_ID = "session_location"

        # Create session immediately during initialization (async call)
        asyncio.run(self.session_service.create_session(
            app_name="agents",
            user_id=self.USER_ID,
            session_id=self.SESSION_ID
        ))

        print(f"✅ LocationAgent initialized")
    
    def run(self, zip_code: str, debug: bool = False):
        """
        Run location lookup synchronously.
        
        Args:
            zip_code: 5-digit US zip code
            debug: Whether to use debug mode
            
        Returns:
            Parsed JSON response
        """
        print(f"🔍 LocationAgent.run() called with zip_code: {zip_code}")
        
        # Run the async execute method synchronously
        try:
            result = asyncio.run(self._execute(zip_code))
            return result
        except RuntimeError:
            # Event loop already running in Streamlit
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(self._execute(zip_code))
                return result
            finally:
                loop.close()
    
    async def _execute(self, zip_code: str):
        """Internal async execution method."""
        # Session was already created in __init__

        # Create prompt
        prompt = f"Find recycling information for zip code: {zip_code}"

        # Create message
        message = types.Content(role="user", parts=[types.Part(text=prompt)])

        # Run agent and collect response with proper cleanup
        response_text = None
        event_stream = self.runner.run_async(
            user_id=self.USER_ID,
            session_id=self.SESSION_ID,
            new_message=message
        )

        try:
            async for event in event_stream:
                if event.is_final_response():
                    response_text = event.content.parts[0].text
                    break
        finally:
            # Ensure generator is properly closed
            await event_stream.aclose()

        # Process response after generator is closed
        if response_text:
            # Try to parse as JSON
            try:
                # Remove markdown code blocks if present
                if '```json' in response_text or '```' in response_text:
                    response_text = response_text.replace('```json', '').replace('```', '').strip()

                parsed = json.loads(response_text)
                return parsed
            except json.JSONDecodeError as e:
                print(f"❌ JSON parsing failed: {e}")
                print(f"Response content: {response_text}")
                return {
                    "success": False,
                    "error": "Failed to parse response",
                    "raw_response": response_text
                }

        # If we get here, no final response was received
        return {
            "success": False,
            "error": "No response received from agent"
        }