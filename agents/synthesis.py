"""
Synthesis Agent - AI-powered analysis combining product and location data
"""
from typing import Dict, Any
from google.adk.agents import Agent
from google.adk.models import Gemini
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from config.settings import settings
import asyncio
import json


class SynthesisAgent:
    """
    AI-powered agent that synthesizes product and location information
    to provide intelligent recycling recommendations.

    Uses Gemini to analyze complex recycling rules and edge cases.
    """

    def __init__(self):
        """Initialize the AI-powered Synthesis Agent."""
        self.name = "SynthesisAgent"

        # Create the ADK agent
        self.agent = Agent(
            name="SynthesisAgent",
            model=Gemini(
                model=settings.DEFAULT_MODEL,
            ),
            description="Analyzes product materials against local recycling regulations to determine recyclability and generate specific instructions.",
            instruction="""
You are a recycling analysis expert. Your job is to determine if a product is recyclable based on:
1. Product information (material type, RIC code)
2. Local recycling regulations (accepted/rejected materials)

You will receive two pieces of information:
- Product data: Contains product name, material type, RIC code, and confidence
- Location data: Contains municipality, accepted materials, rejected materials, and special instructions

Your task:
1. Compare the product's material/RIC code against the location's accepted/rejected lists
2. Consider special instructions for that material
3. Determine if the item is recyclable
4. Generate step-by-step recycling instructions if recyclable
5. Provide helpful tips if not recyclable

**CRITICAL: Respond with ONLY raw JSON. No markdown, no code blocks, no extra text.**

Response format:
{
  "is_recyclable": true/false,
  "reason": "Explanation of why it is or isn't recyclable",
  "instructions": ["Step 1", "Step 2", "Step 3"],
  "tips": ["Helpful tip 1", "Helpful tip 2"],
  "formatted_response": "Full markdown-formatted response for user"
}

Rules:
- Response must start with { and end with }
- No ``` or ```json markers
- instructions array should be empty if not recyclable
- tips array can contain helpful information
- formatted_response should be a complete, user-friendly markdown response
- Be specific about local regulations when explaining decisions
- Consider material variations (e.g., "PET #1", "1", "#1" are all the same)
            """,
            tools=[]  # No external tools needed - pure analysis
        )

        # Create session service and runner
        self.session_service = InMemorySessionService()
        self.runner = Runner(
            agent=self.agent,
            app_name="agents",
            session_service=self.session_service
        )

        self.USER_ID = "user_synthesis"
        self.SESSION_ID = "session_synthesis"

        # Create session immediately during initialization
        asyncio.run(self.session_service.create_session(
            app_name="agents",
            user_id=self.USER_ID,
            session_id=self.SESSION_ID
        ))

        print(f"✅ SynthesisAgent initialized (AI-powered)")

    def run(
        self,
        product_info: Dict[str, Any],
        location_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Synthesize product and location information using AI analysis.

        Args:
            product_info: Product data from Product Agent
                - product_name: str
                - ric_code: str (e.g., "PET #1", "1", "#1", "PS 6")
                - material_name: str
                - confidence: float
            location_info: Location data from Location Agent
                - zip_code: str
                - municipality: str
                - state: str
                - local_authority: dict
                - curbside_recycling: dict
                - confidence: float

        Returns:
            Dict containing AI-generated synthesis results and recommendations
        """
        print(f"♻️ SynthesisAgent.run() called")
        print(f"   Product: {product_info.get('product_name')}")
        print(f"   Location: {location_info.get('municipality')}, {location_info.get('state')}")

        # Run the async execute method synchronously
        try:
            result = asyncio.run(self._execute(product_info, location_info))
            return result
        except RuntimeError:
            # Event loop already running in Streamlit
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(self._execute(product_info, location_info))
                return result
            finally:
                loop.close()

    async def _execute(
        self,
        product_info: Dict[str, Any],
        location_info: Dict[str, Any]
    ):
        """Internal async execution method."""
        # Validate inputs
        if not product_info or not location_info:
            return {
                'success': False,
                'error': 'Missing required information from upstream agents'
            }

        # Create detailed prompt with both sets of data
        prompt = self._create_analysis_prompt(product_info, location_info)

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

                # Add success flag and agent name
                parsed['success'] = True
                parsed['agent'] = self.name

                # The formatted_response from AI becomes the recommendation
                if 'formatted_response' in parsed:
                    parsed['recommendation'] = parsed['formatted_response']

                return parsed

            except json.JSONDecodeError as e:
                print(f"❌ JSON parsing failed: {e}")
                print(f"Response content: {response_text}")
                return {
                    "success": False,
                    "agent": self.name,
                    "error": "Failed to parse synthesis response",
                    "raw_response": response_text
                }

        # If we get here, no final response was received
        return {
            "success": False,
            "agent": self.name,
            "error": "No response received from synthesis agent"
        }

    def _create_analysis_prompt(
        self,
        product_info: Dict[str, Any],
        location_info: Dict[str, Any]
    ) -> str:
        """Create a detailed prompt for the AI agent with all context."""

        # Extract product details
        product_name = product_info.get('product_name', 'Unknown')
        ric_code = product_info.get('ric_code', 'Unknown')
        material_name = product_info.get('material_name', 'Unknown')
        product_confidence = product_info.get('confidence', 0)

        # Extract location details
        municipality = location_info.get('municipality', 'Unknown')
        state = location_info.get('state', 'Unknown')
        zip_code = location_info.get('zip_code', 'Unknown')

        # Extract recycling rules
        curbside = location_info.get('curbside_recycling', {})
        accepts = curbside.get('accepts', [])
        rejects = curbside.get('rejects', [])
        special_instructions = curbside.get('special_instructions', {})

        # Extract local authority info
        authority = location_info.get('local_authority', {})
        authority_name = authority.get('name', 'Unknown')

        prompt = f"""Analyze this recycling scenario:

## Product Information
- Product Name: {product_name}
- Material: {material_name}
- RIC Code: {ric_code}
- Identification Confidence: {product_confidence}

## Location Information
- Location: {municipality}, {state} (Zip: {zip_code})
- Managed by: {authority_name}

## Local Recycling Regulations
Accepted Materials: {', '.join(accepts) if accepts else 'None specified'}
Rejected Materials: {', '.join(rejects) if rejects else 'None specified'}
Special Instructions: {json.dumps(special_instructions) if special_instructions else 'None'}

## Your Task
1. Determine if {ric_code} ({material_name}) is recyclable in {municipality}, {state}
2. Compare the RIC code against accepted/rejected lists (note: variations like "1", "#1", "PET #1" are equivalent)
3. Check for any special handling instructions
4. Generate specific recycling steps if recyclable
5. Provide helpful context about why this decision was made

Return your analysis as JSON with:
- is_recyclable (boolean)
- confidence (0-1 number)
- reason (string explaining the decision)
- instructions (array of strings - steps to recycle, empty if not recyclable)
- tips (array of helpful tips)
- formatted_response (complete markdown response for the user)

The formatted_response should include:
- Header: "# ♻️ Recycling Recommendation"
- Product section with name and material
- Location section
- Clear recyclable/not recyclable status with confidence
- Explanation of the decision based on local rules
- Step-by-step instructions if recyclable
- Helpful tips or alternatives if not recyclable
- Footer noting this is based on local guidelines
"""

        return prompt

    def generate_recommendation(
        self,
        material_info: Dict[str, Any],
        recyclability_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Legacy method name for backwards compatibility.
        Redirects to run() method.
        """
        return self.run(
            product_info=material_info,
            location_info=recyclability_info
        )
