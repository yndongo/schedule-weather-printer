## Goal

A small local application that generates three daily “message cards” containing:

* weather data
* ASCII art
* a short message

Output is printed to the terminal.

---

## Core Behavior

At scheduled times or when run manually, the app will:

1. Fetch weather data (NOAA)
2. Determine time-of-day (morning / afternoon / night)
3. Check for special date overrides
4. Select greeting
5. Select art (based on time-of-day + weather category)
6. Select message
7. Apply repeat-prevention rules
8. Format into a fixed-width card
9. Print to terminal

---

## Schedule

* Morning → 8:30 AM
* Afternoon → 5:30 PM
* Night → 8:30 PM

---

## Card Format

Order:

1. Top border
2. Greeting
3. Weather block
4. ASCII art
5. Message
6. Bottom border

---

## Weather

### Data Source

* NOAA API

### Display

* Temperature (°F or N/A)
* Wind (mph)
* Rain (%)
* Lucky number (1–99)

### Rules

* Temperature rounded to integer
* Wind and rain rounded
* Missing data handled gracefully

### Fallback

If weather fails:

* Temperature: N/A
* Wind: 0 mph
* Rain: 0%
* Include fallback message text

---

## Formatting

* Fixed width (default: 32 characters)
* Text wraps as needed
* Art must fit width or fallback is used
* Degree symbol: “°”

---

## Art System

* Selected by:

  * time-of-day
  * weather category
* Not based on temperature
* Fallback used if missing or too wide

---

## Messages

* Stored in JSON
* Organized by time-of-day
* Neutral tone in public version

### Repeat Rules

* No repeat within 14 days
* History retained for 21 days

---

## Greetings

* Organized by time-of-day
* No immediate repeats

---

## Special Dates

* Override greeting and message
* Optional art override
* Weather still displayed

---

## Modes

### Production

* Live NOAA weather
* Updates history

### Test

* Deterministic behavior
* Uses fixtures when available
* Does not affect production history
* Optional `config.test.json` overlay may be used locally

---

## Error Handling

* Always produce a valid card
* Failures fall back gracefully
* Errors logged, not shown in output (except weather fallback note)

---

## Constraints

* Local execution only
* No external dependencies
* Simple, modular design

---

## End State

A reliable, local terminal application that generates clean, structured message cards with minimal setup and easy customization.
