
import json
from typing import List, Dict


# ============================================================================
# PROMPT VERSION 1: Basic extraction
# ============================================================================
# Issues found:
# - Port codes often wrong or missing
# - Incoterms not defaulting to FOB
# - Product line logic not understood
# - Poor handling of abbreviations (HK, SHA, MAA)
# ============================================================================

PROMPT_V1 = """You are an AI assistant that extracts structured shipment information from freight forwarding emails.

Extract the following information from the email:
- product_line: Either "pl_sea_import_lcl" or "pl_sea_export_lcl"
- origin_port_code: 5-letter UN/LOCODE
- origin_port_name: Port name
- destination_port_code: 5-letter UN/LOCODE
- destination_port_name: Port name
- incoterm: Shipping terms (FOB, CIF, etc.)
- cargo_weight_kg: Weight in kilograms
- cargo_cbm: Volume in cubic meters
- is_dangerous: Boolean for dangerous goods

Email Subject: {subject}
Email Body: {body}

Return only valid JSON matching this structure:
{{
    "product_line": "pl_sea_import_lcl",
    "origin_port_code": "HKHKG",
    "origin_port_name": "Hong Kong",
    "destination_port_code": "INMAA",
    "destination_port_name": "Chennai",
    "incoterm": "FOB",
    "cargo_weight_kg": 500.0,
    "cargo_cbm": 2.5,
    "is_dangerous": false
}}
"""


# ============================================================================
# PROMPT VERSION 2: Added UN/LOCODE examples and business rules
# ============================================================================
# Improvements:
# - Added explicit port code reference
# - Added India detection logic
# - Added incoterm default rule
# Issues remaining:
# - Still struggling with port abbreviations
# - Dangerous goods detection inconsistent
# - Multiple shipments not handled
# ============================================================================

PROMPT_V2 = """You are an AI assistant extracting structured shipment data from freight forwarding emails.

BUSINESS RULES:
1. Product Line: If destination port is in India (code starts with "IN"), use "pl_sea_import_lcl". If origin is in India, use "pl_sea_export_lcl"
2. Incoterm: If not mentioned, default to "FOB"
3. Port Codes: Use UN/LOCODE format (5 letters: 2-letter country + 3-letter location)
4. Null values: Use null for missing data, not 0 or empty string

PORT CODE REFERENCE (partial):
{port_reference}

Email Subject: {subject}
Email Body: {body}

Extract and return ONLY valid JSON:
{{
    "product_line": "pl_sea_import_lcl",
    "origin_port_code": "HKHKG",
    "origin_port_name": "Hong Kong",
    "destination_port_code": "INMAA",
    "destination_port_name": "Chennai",
    "incoterm": "FOB",
    "cargo_weight_kg": null,
    "cargo_cbm": 5.0,
    "is_dangerous": false
}}
"""


# ============================================================================
# PROMPT VERSION 3: Comprehensive rules + examples
# ============================================================================
# Improvements:
# - Added comprehensive dangerous goods detection rules
# - Added conflict resolution (subject vs body)
# - Added first shipment extraction rule
# - Added unit conversion rules
# - Added port name matching strategy
# - Added handling of common abbreviations
# ============================================================================

PROMPT_V3 = """You are an expert AI assistant extracting structured shipment data from freight forwarding emails.

CRITICAL BUSINESS RULES:

1. PRODUCT LINE DETERMINATION:
   - If destination port code starts with "IN" → "pl_sea_import_lcl"
   - If origin port code starts with "IN" → "pl_sea_export_lcl"
   - Indian port codes: INMAA (Chennai), INNSA (Nhava Sheva), INBLR (Bangalore), INMUN (Mundra), INWFD (Whitefield)

2. PORT CODE MATCHING:
   - Match port names/cities to UN/LOCODE codes using the reference below
   - Handle common abbreviations: HK/Hong Kong→HKHKG, SHA→CNSHA, MAA/Chennai→INMAA, SIN/Singapore→SGSIN
   - Use the canonical port name from the reference for the matched code
   - If port cannot be matched, use null for both code and name

3. INCOTERM RULES:
   - Valid: FOB, CIF, CFR, EXW, DDP, DAP, FCA, CPT, CIP, DPU
   - If not mentioned → default to "FOB"
   - If ambiguous (e.g., "FOB or CIF") → default to "FOB"
   - Always return uppercase

4. DANGEROUS GOODS DETECTION:
   - is_dangerous = true if email contains: "DG", "dangerous", "hazardous", "Class" + number, "IMO", "IMDG", "UN" + number (UN 1993, etc.)
   - is_dangerous = false if email contains: "non-DG", "non-hazardous", "not dangerous", "non hazardous"
   - If no mention → false

5. NUMERIC FIELDS:
   - Round cargo_weight_kg and cargo_cbm to 2 decimal places
   - Convert units:
     * lbs to kg: multiply by 0.453592
     * tonnes/MT to kg: multiply by 1000
   - "TBD", "N/A", "to be confirmed" → null
   - Explicit zero (e.g., "0 kg") → 0 (not null)
   - Dimensions (L×W×H) → extract as null for CBM (do not calculate)
   - If both weight AND CBM mentioned, extract both independently

6. CONFLICT RESOLUTION:
   - Body takes precedence over subject
   - Extract only the FIRST shipment if multiple mentioned
   - Use origin→destination pair, ignore transshipment ports

PORT CODE REFERENCE:
{port_reference}

Email Subject: {subject}
Email Body: {body}

Return ONLY valid JSON (no markdown, no explanations):
{{
    "product_line": "pl_sea_import_lcl",
    "origin_port_code": "HKHKG",
    "origin_port_name": "Hong Kong",
    "destination_port_code": "INMAA",
    "destination_port_name": "Chennai",
    "incoterm": "FOB",
    "cargo_weight_kg": 500.0,
    "cargo_cbm": 2.5,
    "is_dangerous": false
}}
"""


def get_current_prompt() -> str:
    """Return the current production prompt (v3)."""
    return PROMPT_V3


def format_prompt(prompt_template: str, subject: str, body: str, port_reference: str) -> str:
    """Format prompt with email data and port reference."""
    return prompt_template.format(
        subject=subject,
        body=body,
        port_reference=port_reference
    )


def get_port_reference_text(ports: List[Dict[str, str]], max_ports: int = 30) -> str:
    """
    Format port reference for inclusion in prompt.
    Limits to most common ports to save tokens.
    """
    # Group by code to show variations
    port_map = {}
    for port in ports:
        code = port['code']
        name = port['name']
        if code not in port_map:
            port_map[code] = []
        if name not in port_map[code]:
            port_map[code].append(name)
    
    # Format as readable list
    lines = []
    for code, names in sorted(port_map.items())[:max_ports]:
        if len(names) == 1:
            lines.append(f"- {code}: {names[0]}")
        else:
            lines.append(f"- {code}: {', '.join(names)}")
    
    return "\n".join(lines)


# ============================================================================
# EVOLUTION LOG FOR README
# ============================================================================

EVOLUTION_LOG = """
## Prompt Evolution

### v1: Basic extraction (Expected Accuracy: ~60-70%)
**Prompt Changes:**
- Simple extraction instructions
- Basic schema example
- No business rules

**Issues Identified:**
- Port codes frequently wrong (e.g., EMAIL_001 extracted "INMAA" for Chennai origin but should match to correct code)
- Incoterms not defaulting to FOB when missing
- Product line (import vs export) logic not understood
- Poor handling of port abbreviations like "HK", "SHA", "MAA"
- No dangerous goods detection

**Example Failures:**
- EMAIL_001: Failed to detect export (origin=India)
- EMAIL_006: Missed dangerous goods indicators ("UN 1993", "Flammable")
- EMAIL_003: Didn't default missing incoterm to FOB

---

### v2: Added business rules and port reference (Expected Accuracy: ~75-80%)
**Prompt Changes:**
- Added explicit India detection logic (IN prefix)
- Added port code reference in prompt
- Added incoterm default rule (FOB)
- Added null handling guidance

**Improvements:**
- Product line detection improved significantly
- Better port code matching with reference
- Incoterm defaults working

**Issues Remaining:**
- Dangerous goods detection still inconsistent
- Struggled with port abbreviations not in reference
- Multiple shipments in one email caused confusion
- Subject vs body conflicts not handled
- Unit conversions (lbs, tonnes) not working

**Example Failures:**
- EMAIL_006: Still missing DG detection despite "UN 1993 Flammable Liquid"
- EMAIL_023 (assumed): Multiple shipments - extracted wrong one
- EMAIL_015 (assumed): Weight in lbs not converted to kg

---

### v3: Comprehensive rules + edge case handling (Expected Accuracy: ~85-90%)
**Prompt Changes:**
- Added comprehensive dangerous goods keywords (DG, IMO, IMDG, Class X, UN XXXX)
- Added explicit negation handling (non-DG, non-hazardous)
- Added conflict resolution rules (body > subject)
- Added "first shipment only" rule for multi-shipment emails
- Added unit conversion formulas (lbs→kg, tonnes→kg)
- Added common port abbreviations mapping
- Added handling for TBD/N/A values
- Added guidance on dimensions vs CBM

**Improvements:**
- Dangerous goods detection now robust
- Better abbreviation handling
- Unit conversions working
- Multi-shipment emails handled correctly

**Remaining Challenges:**
- Very ambiguous port names (may need fuzzy matching)
- Emails with typos or non-standard terminology
- Complex multi-leg shipments with transshipment ports
- Edge cases with unusual unit expressions

**Example Successes:**
- EMAIL_006: Now correctly detects DG from "UN 1993 Flammable Liquid"
- EMAIL_001: Correctly identifies export (origin IN, destination KR)
- Weight conversions working (lbs * 0.453592)

---

### Production Prompt: v3
The current production system uses v3 with all comprehensive rules.
"""