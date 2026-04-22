# Scheduled Weather Printer (Public Version)

A small, local Python application that generates simple message cards throughout the day. Each card includes:

- Current weather data from NOAA
- Minimal ASCII art
- A short message

This public version is designed for terminal output only. It does not require or assume any printer hardware.

## Features

- Runs locally with no external services beyond NOAA weather
- Generates cards on demand or on a schedule
- Rotates greetings, messages, and art
- Prevents immediate or recent repeats
- Supports special date overrides, such as holidays
- Uses JSON files for all user-facing content so it is easy to customize

## File Structure

```text
schedule-weather-printer/
├── src/
│   └── weather_gift/
│       ├── __init__.py
│       ├── cli.py
│       ├── main.py
│       ├── scheduler.py
│       ├── weather.py
│       ├── content.py
│       ├── format.py
│       ├── output.py
│       ├── config.py
│       └── fixtures.py
├── assets/
│   ├── greetings.json
│   ├── messages.json
│   ├── art.json
│   └── special_days.json
├── data/
│   ├── greeting_history.json
│   ├── message_history.json
│   └── art_history.json
├── tests/
│   └── test_*.py
├── config.example.json
├── README.md
├── SPEC.md
├── .gitignore
└── pyproject.toml

### Notes

- `src/weather_gift/` contains the core application logic
- `assets/` contains all user-editable content (messages, greetings, art)
- `data/` stores runtime history for repeat-prevention (generated automatically)
- `config.example.json` shows how to override defaults locally

## Installation

### 1. Clone the repository

```
git clone <your-repo-url>
cd weather-gift
```

### 2. (Optional) Create a virtual environment

```
python3 -m venv venv
source venv/bin/activate
```

### 3. No dependencies required

This project uses only the Python standard library.

---

## Running the App

### Run once (recommended for testing)

```
PYTHONPATH=src python3 -m weather_gift.cli run --mode test
```

### Run with a fixed time (deterministic output)

```
PYTHONPATH=src python3 -m weather_gift.cli run \
  --mode test \
  --now 2026-04-17T08:30:00
```

### Run in production mode (live weather)

```
PYTHONPATH=src python3 -m weather_gift.cli run --mode production
```

---

## Scheduler (optional)

Run the app continuously on a schedule:

```
PYTHONPATH=src python3 -m weather_gift.cli schedule --mode production
```

Scheduled times:

* Morning → 8:30 AM
* Afternoon → 5:30 PM
* Night → 8:30 PM

---

## Output

All output is printed to the terminal as a formatted card.

---

## Customization

All user-facing content is stored in JSON files:

* `messages.json`
* `greetings.json`
* `art.json`
* `special_days.json`

You can safely edit these to personalize the output without changing code.

Optional local config:

* Copy `config.example.json` to `config.json` for local overrides
* `config.json` and `config.test.json` are optional and should stay uncommitted

---

## Notes

* This version is intended as a clean, shareable example
* Content is neutral by default
* Printer integration is not included in this version
