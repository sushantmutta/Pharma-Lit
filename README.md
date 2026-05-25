# Pharma R&D Agent

## Setup (5 minutes)
1. git clone / download this project
2. `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and add your free Gemini API key from aistudio.google.com
4. `python run.py --demo`        # runs demo and opens UI
5. `streamlit run ui/app.py`     # open UI separately anytime

## Get your free Gemini API key
1. Go to aistudio.google.com
2. Click "Get API key"
3. Copy key into `.env` as GOOGLE_API_KEY

## What it does
- Searches PubMed for recent papers on your disease area
- Reads and embeds them locally (no data leaves your machine)
- Uses Gemini to identify and score drug targets
- Generates a cited hypothesis brief
- Shows everything in a web UI
