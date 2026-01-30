
import json
import os
import time
import re
from typing import List, Dict, Optional
from pathlib import Path

from groq import Groq
from pydantic import ValidationError

from schemas import EmailInput, ShipmentExtraction, PortReference
from prompts import get_current_prompt, format_prompt, get_port_reference_text
from dotenv import load_dotenv

load_dotenv()


# Configuration
GROQ_MODEL = "llama-3.1-70b-versatile"  # Primary model
GROQ_MODEL_FALLBACK = "llama-3.3-70b-versatile"  # Fallback if primary unavailable
TEMPERATURE = 0  # Required for reproducibility
MAX_RETRIES = 3
INITIAL_RETRY_DELAY = 2  # seconds
MAX_RETRY_DELAY = 30  # seconds


class EmailExtractor:
    """Handles LLM-based extraction from freight forwarding emails."""
    
    def __init__(self, api_key: str, port_references: List[Dict[str, str]]):
        """
        Initialize extractor with Groq API client and port reference data.
        
        Args:
            api_key: Groq API key
            port_references: List of port code mappings
        """
        self.client = Groq(api_key=api_key)
        self.port_references = [PortReference(**p) for p in port_references]
        self.port_reference_text = get_port_reference_text(port_references)
        self.prompt_template = get_current_prompt()
        
        # Create port lookup for post-processing
        self.port_lookup = self._build_port_lookup(port_references)
    
    def _build_port_lookup(self, port_references: List[Dict[str, str]]) -> Dict[str, str]:
        """
        Build lookup dictionary for port code to canonical name.
        Uses first occurrence of each code as canonical.
        """
        lookup = {}
        for port in port_references:
            code = port['code']
            if code not in lookup:
                lookup[code] = port['name']
        return lookup
    
    def _extract_json_from_response(self, response_text: str) -> Optional[Dict]:
        """
        Extract JSON from LLM response, handling markdown code blocks.
        
        Args:
            response_text: Raw LLM response
            
        Returns:
            Parsed JSON dict or None if parsing fails
        """
        # Try to find JSON in markdown code blocks
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find raw JSON
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                return None
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            return None
    
    def _call_llm_with_retry(self, prompt: str, model: str) -> Optional[str]:
        """
        Call Groq LLM with exponential backoff retry logic.
        
        Args:
            prompt: Formatted prompt
            model: Model name to use
            
        Returns:
            LLM response text or None if all retries fail
        """
        retry_delay = INITIAL_RETRY_DELAY
        
        for attempt in range(MAX_RETRIES):
            try:
                response = self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert at extracting structured data from freight forwarding emails. Always return valid JSON."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=TEMPERATURE,
                    max_tokens=1000
                )
                return response.choices[0].message.content
            
            except Exception as e:
                error_msg = str(e)
                print(f"  ⚠ Attempt {attempt + 1}/{MAX_RETRIES} failed: {error_msg[:100]}")
                
                # Check if it's a rate limit error
                if "rate_limit" in error_msg.lower() or "429" in error_msg:
                    if attempt < MAX_RETRIES - 1:
                        print(f"  ⏳ Rate limited, waiting {retry_delay}s...")
                        time.sleep(retry_delay)
                        retry_delay = min(retry_delay * 2, MAX_RETRY_DELAY)
                        continue
                
                # For other errors, retry with shorter delay
                if attempt < MAX_RETRIES - 1:
                    time.sleep(1)
                    continue
                
                return None
        
        return None
    
    def _validate_and_fix_extraction(self, raw_data: Dict, email_id: str) -> Dict:
        """
        Validate extraction and apply business rule fixes.
        
        Args:
            raw_data: Raw extracted data
            email_id: Email identifier
            
        Returns:
            Validated and fixed extraction data
        """
        # Ensure port names match canonical names from reference
        if raw_data.get('origin_port_code') in self.port_lookup:
            raw_data['origin_port_name'] = self.port_lookup[raw_data['origin_port_code']]
        
        if raw_data.get('destination_port_code') in self.port_lookup:
            raw_data['destination_port_name'] = self.port_lookup[raw_data['destination_port_code']]
        
        # Ensure null consistency: if code is null, name should be null
        if raw_data.get('origin_port_code') is None:
            raw_data['origin_port_name'] = None
        if raw_data.get('destination_port_code') is None:
            raw_data['destination_port_name'] = None
        
        # Add email ID
        raw_data['id'] = email_id
        
        return raw_data
    
    def extract_single_email(self, email: EmailInput) -> ShipmentExtraction:
        """
        Extract shipment data from a single email.
        
        Args:
            email: Email input data
            
        Returns:
            Validated shipment extraction
        """
        print(f"Processing {email.id}...", end=" ")
        
        # Format prompt
        prompt = format_prompt(
            self.prompt_template,
            email.subject,
            email.body,
            self.port_reference_text
        )
        
        # Try primary model first
        response_text = self._call_llm_with_retry(prompt, GROQ_MODEL)
        
        # If primary fails, try fallback
        if response_text is None:
            print(f"  ↻ Trying fallback model...", end=" ")
            response_text = self._call_llm_with_retry(prompt, GROQ_MODEL_FALLBACK)
        
        # If both models fail, return null extraction
        if response_text is None:
            print("✗ FAILED (all retries exhausted)")
            return ShipmentExtraction(
                id=email.id,
                product_line=None,
                origin_port_code=None,
                origin_port_name=None,
                destination_port_code=None,
                destination_port_name=None,
                incoterm=None,
                cargo_weight_kg=None,
                cargo_cbm=None,
                is_dangerous=False
            )
        
        # Parse JSON response
        extracted_data = self._extract_json_from_response(response_text)
        
        if extracted_data is None:
            print("✗ FAILED (invalid JSON)")
            return ShipmentExtraction(
                id=email.id,
                product_line=None,
                origin_port_code=None,
                origin_port_name=None,
                destination_port_code=None,
                destination_port_name=None,
                incoterm=None,
                cargo_weight_kg=None,
                cargo_cbm=None,
                is_dangerous=False
            )
        
        # Validate and fix
        try:
            fixed_data = self._validate_and_fix_extraction(extracted_data, email.id)
            extraction = ShipmentExtraction(**fixed_data)
            print("✓")
            return extraction
        except ValidationError as e:
            print(f"✗ FAILED (validation error: {e})")
            return ShipmentExtraction(
                id=email.id,
                product_line=None,
                origin_port_code=None,
                origin_port_name=None,
                destination_port_code=None,
                destination_port_name=None,
                incoterm=None,
                cargo_weight_kg=None,
                cargo_cbm=None,
                is_dangerous=False
            )
    
    def extract_batch(self, emails: List[EmailInput]) -> List[ShipmentExtraction]:
        """
        Extract shipment data from multiple emails.
        
        Args:
            emails: List of email inputs
            
        Returns:
            List of validated extractions
        """
        extractions = []
        total = len(emails)
        
        print(f"\n{'='*60}")
        print(f"Starting batch extraction: {total} emails")
        print(f"{'='*60}\n")
        
        for i, email in enumerate(emails, 1):
            print(f"[{i}/{total}] ", end="")
            extraction = self.extract_single_email(email)
            extractions.append(extraction)
            
            # Rate limiting: small delay between requests
            if i < total:
                time.sleep(0.5)
        
        print(f"\n{'='*60}")
        print(f"Batch extraction complete: {total} emails processed")
        print(f"{'='*60}\n")
        
        return extractions


def load_emails(filepath: str) -> List[EmailInput]:
    """Load and validate email input data."""
    with open(filepath, 'r') as f:
        data = json.load(f)
    return [EmailInput(**email) for email in data]


def load_port_references(filepath: str) -> List[Dict[str, str]]:
    """Load port code reference data."""
    with open(filepath, 'r') as f:
        return json.load(f)


def save_extractions(extractions: List[ShipmentExtraction], filepath: str):
    """Save extraction results to JSON file."""
    data = [e.dict() for e in extractions]
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"✓ Results saved to: {filepath}")


def main():
    """Main execution function."""
    # Get API key from environment
    api_key = os.getenv('GROQ_API_KEY')
    if not api_key:
        print("Error: GROQ_API_KEY environment variable not set")
        print("Please set it using: export GROQ_API_KEY='your-api-key'")
        return
    
    # File paths
    emails_path = "emails_input.json"
    ports_path = "port_codes_reference.json"
    output_path = "output.json"
    
    # Check if files exist
    if not Path(emails_path).exists():
        print(f"Error: {emails_path} not found")
        return
    if not Path(ports_path).exists():
        print(f"Error: {ports_path} not found")
        return
    
    # Load data
    print("Loading input data...")
    emails = load_emails(emails_path)
    port_references = load_port_references(ports_path)
    print(f"✓ Loaded {len(emails)} emails")
    print(f"✓ Loaded {len(port_references)} port references")
    
    # Initialize extractor
    extractor = EmailExtractor(api_key, port_references)
    
    # Run extraction
    extractions = extractor.extract_batch(emails)
    
    # Save results
    save_extractions(extractions, output_path)
    
    # Summary
    successful = sum(1 for e in extractions if e.origin_port_code is not None)
    print(f"\nSummary:")
    print(f"  Total emails: {len(emails)}")
    print(f"  Successful extractions: {successful}")
    print(f"  Failed extractions: {len(emails) - successful}")


if __name__ == "__main__":
    main()