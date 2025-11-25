"""
Synthesis Agent - Combines product and location data to generate recommendations
"""
from typing import Dict, Any, List


class SynthesisAgent:
    """
    Agent responsible for synthesizing information from Product and Location agents
    to provide actionable recycling recommendations.
    
    MVP Scope: Plastic materials with RIC codes only
    """
    
    def __init__(self):
        """Initialize the Synthesis Agent."""
        self.name = "SynthesisAgent"
    
    def run(
        self,
        product_info: Dict[str, Any],
        location_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Synthesize product and location information into recommendations.
        
        Args:
            product_info: Product data from Product Agent
                - product_name: str
                - ric_code: str (e.g., "PET #1", "1", "#1", "PS 6")
                - confidence: float
            location_info: Location data from Location Agent
                - zip_code: str
                - municipality: str
                - state: str
                - local_authority: dict
                - curbside_recycling: dict
                - confidence: float
            
        Returns:
            Dict containing synthesis results and recommendations
        """
        try:
            # Validate inputs
            if not product_info or not location_info:
                return {
                    'success': False,
                    'error': 'Missing required information from upstream agents'
                }
            
            # Determine recyclability
            recommendation = self._determine_recyclability(
                product_info,
                location_info
            )
            
            # Generate instructions if recyclable
            if recommendation['is_recyclable']:
                recommendation['instructions'] = self._create_instructions(
                    product_info,
                    location_info
                )
            
            # Format final response
            formatted_response = self._format_response(
                product_info,
                location_info,
                recommendation
            )
            
            return {
                'success': True,
                'agent': self.name,
                'recommendation': recommendation,
                'formatted_response': formatted_response
            }
            
        except Exception as e:
            return {
                'success': False,
                'agent': self.name,
                'error': str(e)
            }
    
    def _normalize_ric(self, ric_code: str) -> str:
        """
        Normalize RIC code to standard format 'MATERIAL #N'.
        
        Handles various formats:
        - "6" -> "PS #6"
        - "#6" -> "PS #6"
        - "PS 6" -> "PS #6"
        - "ps#6" -> "PS #6"
        - "PET 1" -> "PET #1"
        
        Args:
            ric_code: RIC code in any format
            
        Returns:
            Normalized RIC code in format 'MATERIAL #N'
        """
        ric_code = ric_code.strip().upper()
        
        # Mapping of numbers to full RIC codes
        ric_map = {
            '1': 'PET #1',
            '#1': 'PET #1',
            '2': 'HDPE #2',
            '#2': 'HDPE #2',
            '3': 'PVC #3',
            '#3': 'PVC #3',
            '4': 'LDPE #4',
            '#4': 'LDPE #4',
            '5': 'PP #5',
            '#5': 'PP #5',
            '6': 'PS #6',
            '#6': 'PS #6',
            '7': 'OTHER #7',
            '#7': 'OTHER #7'
        }
        
        # Check if it's just a number or #number
        if ric_code in ric_map:
            return ric_map[ric_code]
        
        # Remove all spaces and extract material and number parts
        ric_code = ric_code.replace(' ', '').replace('#', '')
        
        # Now we have something like "PET1" or "PS6"
        # Split into material letters and number
        material = ''
        number = ''
        for char in ric_code:
            if char.isalpha():
                material += char
            elif char.isdigit():
                number += char
        
        # Reconstruct with proper format
        if material and number:
            return f"{material} #{number}"
        
        # If we can't parse it, return as-is
        return ric_code
    
    def _determine_recyclability(
        self,
        product_info: Dict[str, Any],
        location_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Determine if material is recyclable based on local rules."""
        
        # Normalize the RIC code from product
        raw_ric = product_info.get('ric_code', '')
        ric_code = self._normalize_ric(raw_ric)
        
        curbside = location_info.get('curbside_recycling', {})
        
        # Normalize accepts and rejects lists
        accepts = [self._normalize_ric(item) for item in curbside.get('accepts', [])]
        rejects = [self._normalize_ric(item) for item in curbside.get('rejects', [])]
        
        # MVP: Only accept plastic materials with RIC codes
        valid_plastics = ['PET #1', 'HDPE #2', 'PVC #3', 'LDPE #4', 
                          'PP #5', 'PS #6', 'OTHER #7']
        
        if ric_code not in valid_plastics:
            return {
                'is_recyclable': False,
                'confidence': 1.0,
                'reason': 'This MVP version only supports plastic materials with Resin Identification Codes (RIC). Other materials will be supported in future updates.',
                'instructions': [],
                'tips': ['Check back soon for support of glass, paper, metal, and other materials!']
            }
        
        # Check if explicitly rejected
        if ric_code in rejects:
            return {
                'is_recyclable': False,
                'confidence': 0.9,
                'reason': f'{ric_code} is not accepted in your local curbside recycling program.',
                'instructions': [],
                'tips': []
            }
        
        # Check if explicitly accepted
        if ric_code in accepts:
            return {
                'is_recyclable': True,
                'confidence': 0.95,
                'reason': f'{ric_code} is accepted in your local curbside recycling program.'
            }
        
        # Material not found in either list - uncertain
        return {
            'is_recyclable': False,
            'confidence': 0.5,
            'reason': f'Unable to confirm if {ric_code} is accepted locally. Please check with your local recycling facility.',
            'instructions': [],
            'tips': []
        }
    
    def _create_instructions(
        self,
        product_info: Dict[str, Any],
        location_info: Dict[str, Any]
    ) -> List[str]:
        """Generate step-by-step recycling instructions."""
        
        instructions = []
        raw_ric = product_info.get('ric_code', '')
        ric_code = self._normalize_ric(raw_ric)
        
        curbside = location_info.get('curbside_recycling', {})
        special_instructions = curbside.get('special_instructions', {})
        
        # Normalize special instruction keys and check
        special_found = False
        for key, value in special_instructions.items():
            if self._normalize_ric(key) == ric_code:
                instructions.append(value)
                special_found = True
                break
        
        if not special_found:
            # Default cleaning instruction
            instructions.append("Clean and rinse the item to remove any food residue or contaminants")
        
        # Crushing/flattening for space
        if ric_code in ['PET #1', 'HDPE #2', 'PP #5']:
            instructions.append("Flatten or crush to save space in your recycling bin")
        
        # Add general instruction
        instructions.append(f"Place in your curbside recycling bin")
        
        return instructions
    
    def _format_response(
        self,
        product_info: Dict[str, Any],
        location_info: Dict[str, Any],
        recommendation: Dict[str, Any]
    ) -> str:
        """Format the final response in user-friendly markdown."""
        
        output = []
        
        # Header
        output.append("# ♻️ Recycling Recommendation\n")
        
        # Product Information
        raw_ric = product_info.get('ric_code', 'Unknown')
        normalized_ric = self._normalize_ric(raw_ric) if raw_ric != 'Unknown' else 'Unknown'
        
        output.append("## 📦 Product Information")
        output.append(f"**Product:** {product_info.get('product_name', 'Unknown')}")
        output.append(f"**Material:** {normalized_ric}\n")
        
        # Location Information
        municipality = location_info.get('municipality', 'your area')
        state = location_info.get('state', '')
        location_str = f"{municipality}, {state}" if state else municipality
        output.append(f"## 📍 Location: {location_str}\n")
        
        # Recommendation
        is_recyclable = recommendation.get('is_recyclable', False)
        confidence = recommendation.get('confidence', 0)
        reason = recommendation.get('reason', '')
        
        output.append("## 🎯 Recommendation")
        
        if is_recyclable:
            output.append(f"**Status:** ✅ Recyclable (Confidence: {confidence*100:.0f}%)\n")
            output.append(f"**Reason:** {reason}\n")
            
            # Instructions
            instructions = recommendation.get('instructions', [])
            if instructions:
                output.append("## 📋 How to Recycle")
                for i, instruction in enumerate(instructions, 1):
                    output.append(f"{i}. {instruction}")
                output.append("")
        else:
            output.append(f"**Status:** ❌ Not Recyclable\n")
            output.append(f"**Reason:** {reason}\n")
            
            # Add tips if available
            tips = recommendation.get('tips', [])
            if tips:
                output.append("## 💡 Tips")
                for tip in tips:
                    output.append(f"• {tip}")
                output.append("")
        
        # Footer
        output.append("---")
        output.append("*This recommendation is based on your local recycling guidelines.*")
        
        return "\n".join(output)