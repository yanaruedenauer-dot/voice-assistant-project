
# Jeeves — Voice Assistant for Restaurant Booking (Phase 3)

Jeeves is a multilingual, privacy-preserving voice assistant that helps users find and book restaurants.
The system performs speech recognition, natural-language understanding, slot-filling dialog management, sentiment adaptation, and local recommendations—entirely offline for privacy and robustness.
Example use:

“Book an Italian restaurant in Berlin for two at 7 p.m.”

## Key features:
Multilingual Speech-to-Text: OpenAI Whisper STT (German/English).
Custom NLU + Dialog Manager: intent & slot extraction with fallback logic.
Sentiment Module: adjusts tone dynamically (positive/neutral/negative).
Accessibility Support: recognizes wheelchair, step-free, and restroom needs.
Group Preferences: merges multi-user constraints (dietary & accessibility).
Privacy & GDPR Compliance: local data processing, encrypted preference storage.
Monitoring & Evaluation: logs latency, booking completion, and accuracy.

## Architecture
Layers and core modules:
Client (Input/Output): Microphone / Keyboard ↔ TTS / Speaker

Orchestration: Whisper STT → NLU (Intent & Slot) → Dialog Manager (+ Sentiment Module) → Recommendation Engine → Response Builder → TTS

Data & Monitoring: Local Restaurant Dataset (Zomato.csv), Accessibility Data (Wheelmap/OSM), Encrypted User Preferences, Logs & Metrics

## Setup
1. Clone repository: 
git clone https://github.com/yanaruedenauer-dot/voice-assistant-project
cd voice-assistant-project

2. Create virtual environment
python -m venv .venv
source .venv/bin/activate   # macOS / Linux
# or
.venv\Scripts\activate      # Windows

3. Install dependencies
pip install -r requirements.txt


## Dataset
The project uses the Zomato Restaurants Dataset (Kaggle). 
Place the CSV at data/zomato.csv or download via:
mkdir -p data
kaggle datasets download -d shrutimehta/zomato-restaurants-data -p data
unzip -o data/zomato-restaurants-data.zip -d data

## Run the Assistant
Interactive (voice or text mode):
python run_local.py
The assistant automatically asks for missing slots:

City
Cuisine
Guests
Time
Accessibility (wheelchair, step-free, restroom)

Example dialog (English/German mix):
Hi! How can I help?
> I’d like to book an Italian restaurant.
For how many people?
> Two.
What time?
> Seven p.m.
In which city?
> Berlin.
Do you need wheelchair access?
> Yes.
Here are good matches:
• Trattoria Roma (Italian, ★4.5) [♿ wheelchair | 🚻 restroom]
• Sushi Zen (Japanese, ★4.3) [⬆ step-free]

## Group Preference Flow
Jeeves can capture and merge multiple users’ preferences:
> start group of 3
> add
> Berlin, Italian, wheelchair access
> add
> Berlin, vegan, step-free entrance
> add
> Berlin, sushi, no accessibility
> end group
> show results
The system merges constraints (OR-rule for accessibility, majority for cuisine) and lists the top matches.

## GDPR & Security
All processing runs locally — no cloud APIs.
User preferences can be stored only after explicit consent.
Command:remember my preferences / Description:Save preferences locally (AES-encrypted via Fernet).
Command:load my preferences / Decrypt and restore preferences.
Command: delete my data / Permanently remove encrypted file.

Security details
Encryption at rest (Fernet AES-128 CBC + HMAC).
Key stored locally (data/secret.key).
No identifiers or speech data saved.
Deletion = complete removal of user_prefs.enc.

## Evaluation & Metrics
Metrics are logged in data/metrics.log.
Metric	            Target	        Result (Phase 3 Test)
Response Latency	≤ 2 s	        ≈ 1.8 – 2.3 s
Intent              F1 Score	    ≥ 0.8	≈ 0.79
Booking Completion 
Rate	            ≥ 80 %	        ≈ 82 %
Sentiment Response
Accuracy	        –	            > 90 % qualitative
Accessibility 
Query Handling     	–	            keyword + dialogue

Command:python tools/summarize_metrics.py
- prints average ASR / recommender latencies and booking success ratio.

## Testing
Run automated tests:
pytest -q
6 passed in 2.1 s

Test coverage:
Slot extraction (city, cuisine, guests, time)
Accessibility logic
Group merge preferences
Fallback recommendations
Sentiment adaptation

## Project Structure
src/
 ├── data/loader.py
 ├── dialog/
 │    ├── manager.py
 │    ├── group.py
 │    └── slots.py
 ├── models/preferences.py
 ├── monitor/metrics.py
 ├── nlp/sentiment_en.py
 ├── privacy/data_privacy.py
 ├── reco/recommender.py
 └── utils/normalize.py

Additional:
run_local.py – entry point
data/zomato.csv – restaurant dataset
data/metrics.log – runtime metrics
data/user_prefs.enc – encrypted user data

## NotesNotes & Limitations
-Prototype only; no live API bookings.
-Dataset is static (Zomato Kaggle).
-Whisper STT uses CPU by default; GPU optional.
-Sentiment model (Transformers) limited to English.
-Accessibility integration uses placeholder tags (ready for Wheelmap API extension).

## Acknowledgements
OpenAI Whisper (STT)
Hugging Face Transformers (Sentiment)
pandas, PyTorch, sounddevice
IU International University — Voice Assistants and NLP Course

Submission-ready:
Aligns with Phase 2 feedback.
Includes accessibility, group logic, GDPR, and monitoring.
Matches final diagram (Phase 3 PDF).
Fully reproducible offline.

