from google.adk.agents import Agent
from google.adk.models import Gemini
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from config.settings import settings
from google.adk.tools import google_search
import asyncio
import json


class ProductIntelligenceAgent:
    """Wrapper for the Product Intelligence ADK agent."""

    def __init__(self):
        """Initialize the product intelligence agent."""
        self.agent = Agent(
            name="ProductIntelligenceAgent",
            model=Gemini(
                model=settings.DEFAULT_MODEL,
            ),
            description="Provides recycling information for products by searching the internet and returns results in a structured JSON format. Categorizes product_category into beverage_container, food_container, bottle, cup, bag, packaging, or other. Ensures confidence value is between 0 and 1. If information is unavailable, returns 'NA' for all fields.",
            instruction="""
You must respond with ONLY raw JSON. No markdown code blocks, no explanations, no additional text.

Task:
1. Accept product name from user
2. Check if it's a specific branded product (e.g., "Coca-Cola Can") - if generic (e.g., "glass bottle", "plastic cup") return error format
3. Search internet for recycling information
4. Return ONLY raw JSON (no ``` markers, no text before/after)

Success format (include success field):
{"success": true, "product_name": "Product Name", "brand": "Brand", "ric_code": "PET #1", "material_name": "Polyethylene Terephthalate", "confidence": 0.89, "product_category": "beverage_container", "notes": "Summary"}

Error format:
{"success": false, "error": "Reason"}

Rules:
- Response must start with { and end with }
- No ``` or ```json markers
- No text before or after JSON
- confidence is a number 0-1, not string
- ALWAYS include "success": true or false
- For generic products: return error format
- For unknown data: use "N/A" but keep "success": true
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

        self.USER_ID = "user_product"
        self.SESSION_ID = "session_product"

        # Create session immediately during initialization (async call)
        asyncio.run(self.session_service.create_session(
            app_name="agents",
            user_id=self.USER_ID,
            session_id=self.SESSION_ID
        ))

        print(f"✅ ProductIntelligenceAgent initialized")
    
    def run(self, product_name: str, debug: bool = False):
        """
        Run product analysis synchronously.

        Args:
            product_name: Name or description of the product
            debug: Whether to use debug mode

        Returns:
            Parsed JSON response
        """
        print(f"🔍 ProductIntelligenceAgent.run() called with product: {product_name}")

        # Run the async execute method synchronously
        try:
            result = asyncio.run(self._execute(product_name))
            return result
        except RuntimeError:
            # Event loop already running in Streamlit
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(self._execute(product_name))
                return result
            finally:
                loop.close()

    async def _execute(self, product_name: str):
        """Internal async execution method."""
        # Session was already created in __init__

        # Create prompt
        prompt = f"Find recycling information for product: {product_name}"

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