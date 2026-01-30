# Email Shipment Data Extraction

An AI-powered system that automatically extracts structured shipment information from freight forwarding emails using the Groq API and Large Language Models.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Data Formats](#data-formats)
- [API Keys & Authentication](#api-keys--authentication)
- [Troubleshooting](#troubleshooting)

## Overview

This project processes freight forwarding emails and uses AI to extract key shipment details such as:
- **Product Line**: Type of service (sea import/export LCL)
- **Origin Port**: Source port code and name
- **Destination Port**: Target port code and name
- **Incoterms**: Shipping terms (FOB, CIF, etc.)
- **Cargo Details**: Weight, volume, and hazardous goods flag

The system uses the **Groq API** with the Llama 3.3 model for fast, accurate extraction with built-in retry logic and validation.

## Features

✅ **LLM-Powered Extraction** - Uses advanced AI for intelligent data extraction  
✅ **Batch Processing** - Processes multiple emails efficiently  
✅ **Smart Retry Logic** - Handles rate limits and transient errors gracefully  
✅ **Data Validation** - Pydantic schemas ensure data quality  
✅ **Port Reference Mapping** - Validates port codes against reference data  
✅ **Fallback Mechanisms** - Automatic model fallback if primary unavailable  
✅ **JSON Output** - Results saved in structured JSON format  

## Prerequisites

Before you begin, ensure you have:

1. **Python 3.8+** installed on your system
2. **Groq API Key** (free tier available at [console.groq.com](https://console.groq.com))
3. **Git** (optional, for version control)

### Check Python Version

```bash
python --version
# Should output Python 3.8 or higher
```

## Installation

### Step 1: Clone or Download Project

```bash
# If using git
git clone <repository-url>
cd email_extract

# Or navigate to the project folder if already downloaded
cd path/to/email_extract
```

### Step 2: Create Virtual Environment (Recommended)

```bash
# Create virtual environment
python -m venv .venv

# Activate it
# On Windows:
.venv\Scripts\activate

# On macOS/Linux:
source .venv/bin/activate
```

### Step 3: Install Dependencies

```bash
# Install required packages
pip install -r requirements.txt

# Verify installation
python test_setup.py
```

Expected output:
```
Testing package imports...
  [OK] pydantic installed
  [OK] groq installed
  [OK] python-dotenv installed
Testing file existence...
  [OK] emails_input.json found
  [OK] port_codes_reference.json found
```

## Configuration

### Step 1: Get Groq API Key

1. Visit [console.groq.com](https://console.groq.com)
2. Sign up or log in to your account
3. Navigate to **API Keys** section
4. Create a new API key
5. Copy the key (keep it secure!)

### Step 2: Set Environment Variable

**Option A: Using .env File (Recommended)**

Create a `.env` file in the project root:

```bash
GROQ_API_KEY=your_api_key_here
```

**Option B: Set System Environment Variable**

```bash
# Windows (PowerShell)
$env:GROQ_API_KEY = "your_api_key_here"

# Windows (Command Prompt)
set GROQ_API_KEY=your_api_key_here

# macOS/Linux
export GROQ_API_KEY=your_api_key_here
```

## Usage

### Quick Start

```bash
# Make sure virtual environment is activated
python extract.py
```

### Process Flow

1. **Load Input Data**
   - Reads `emails_input.json` containing email records
   - Reads `port_codes_reference.json` for port validation

2. **Initialize Extractor**
   - Connects to Groq API
   - Sets up LLM model and port reference data
   - Prepares extraction templates

3. **Process Emails**
   - For each email:
     - Formats prompt with email content
     - Calls LLM API with retry logic
     - Parses and validates extracted JSON
     - Validates port codes against reference

4. **Save Results**
   - Outputs to `output.json`
   - Shows extraction summary

### Example Output

```
Loading input data...
[+] Loaded 50 emails
[+] Loaded 47 port references

============================================================
Starting batch extraction: 50 emails
============================================================

[1/50] Processing EMAIL_001... [OK]
[2/50] Processing EMAIL_002... [OK]
[3/50] Processing EMAIL_003... [FAIL] invalid JSON

============================================================
Batch extraction complete: 50 emails processed
============================================================

[+] Results saved to: output.json

Summary:
  Total emails: 50
  Successful extractions: 48
  Failed extractions: 2
```

## Project Structure

```
email_extract/
├── extract.py                    # Main extraction script
├── schemas.py                    # Pydantic data models
├── prompts.py                    # LLM prompt templates
├── evaluate.py                   # Evaluation and metrics
├── test_setup.py                 # Setup verification script
├── requirements.txt              # Python dependencies
├── .env                          # Environment variables (create this)
├── emails_input.json             # Input email data
├── port_codes_reference.json     # Port code reference
├── ground_truth.json             # Expected results for validation
├── output.json                   # Generated extraction results
└── README.md                     # This file
```

## Data Formats

### Input: emails_input.json

```json
[
  {
    "id": "EMAIL_001",
    "subject": "FCL Sea Import Quotation - Shanghai to Los Angeles",
    "body": "Hi, we have a shipment from SHANGHAI to LOS ANGELES...",
    "sender_email": "agent@shipper.com",
    "to_emails": "client@company.com",
    "cc_emails": "accounting@company.com"
  }
]
```

### Reference: port_codes_reference.json

```json
[
  {
    "code": "CNSHA",
    "name": "Shanghai"
  },
  {
    "code": "USLAX",
    "name": "Los Angeles"
  }
]
```

### Output: output.json

```json
[
  {
    "id": "EMAIL_001",
    "product_line": "pl_sea_import_lcl",
    "origin_port_code": "CNSHA",
    "origin_port_name": "Shanghai",
    "destination_port_code": "USLAX",
    "destination_port_name": "Los Angeles",
    "incoterm": "FOB",
    "cargo_weight_kg": 5000,
    "cargo_cbm": 12.5,
    "is_dangerous": false
  }
]
```

## API Keys & Authentication

### Groq API Key Management

**Security Best Practices:**

1. ✅ **Use .env file** for local development
2. ✅ **Never commit .env to git** - add to `.gitignore`
3. ✅ **Use environment variables** in production
4. ✅ **Rotate keys regularly**
5. ❌ Never hardcode API keys in source code

### Rate Limiting

Groq API has rate limits (varies by tier):

- **Free Tier**: 100,000 tokens/day
- **Dev Tier**: Higher limits available

Monitor API usage in [console.groq.com](https://console.groq.com/settings/billing)

## Troubleshooting

### Issue: `ModuleNotFoundError: No module named 'groq'`

**Solution:**
```bash
pip install -r requirements.txt
# Or manually:
pip install groq>=1.0.0 pydantic python-dotenv
```

### Issue: `GROQ_API_KEY not set`

**Solution:**

```bash
# Check if .env file exists
# If using .env:
cat .env
# Should show: GROQ_API_KEY=your_key_here

# If using environment variable:
echo $GROQ_API_KEY  # macOS/Linux
echo %GROQ_API_KEY% # Windows CMD
$env:GROQ_API_KEY   # Windows PowerShell
```

### Issue: `UnicodeEncodeError` on Windows

**Solution:**

The script now uses ASCII characters instead of Unicode symbols. If you encounter this:

```bash
# Set encoding for PowerShell
$env:PYTHONIOENCODING = "utf-8"
python extract.py
```

### Issue: `Rate limit exceeded (429 Error)`

**Solution:**

```bash
# Wait for rate limit to reset (typically 24 hours)
# Or upgrade your Groq plan at console.groq.com

# Temporary: Increase retry delay
# Edit extract.py line 22:
MAX_RETRY_DELAY = 60  # Increase to 60 seconds
```

### Issue: `ConnectionError` or `Timeout`

**Solution:**

```bash
# Check internet connection
# Retry the script - it has automatic retry logic
python extract.py

# If persistent, check Groq service status at console.groq.com
```

### Issue: Decommissioned Model Error

**Solution:**

Update the model name in `extract.py` (line 18):

```python
# Check available models at console.groq.com
GROQ_MODEL = "llama-3.3-70b-versatile"  # Currently available model
GROQ_MODEL_FALLBACK = "mixtral-8x7b-32768"  # Alternative
```

## Advanced Usage

### Modify Extraction Prompts

Edit `prompts.py` to customize the LLM instructions and improve extraction quality.

### Change Retry Strategy

In `extract.py`, adjust these parameters:

```python
MAX_RETRIES = 3              # Number of retry attempts
INITIAL_RETRY_DELAY = 2      # Starting delay in seconds
MAX_RETRY_DELAY = 30         # Maximum delay in seconds
TEMPERATURE = 0              # LLM creativity (0 = deterministic)
```

### Evaluate Results

Compare extracted data with ground truth:

```bash
python evaluate.py
```

## Support & Documentation

- **Groq API Docs**: https://console.groq.com/docs
- **Pydantic Docs**: https://docs.pydantic.dev
- **Python Docs**: https://docs.python.org

## License

This project is licensed under the MIT License - see LICENSE file for details.

## Contributors

- Project development and maintenance

---

**Last Updated**: January 30, 2026  
**Status**: Production Ready
