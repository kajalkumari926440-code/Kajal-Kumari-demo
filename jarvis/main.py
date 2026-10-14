
import os
import re
import platform
import webbrowser
from datetime import datetime

import speech_recognition as sr
import pywhatkit
import pyttsx3
from dotenv import load_dotenv
from google import genai
from google.genai import types


# ==================== CONFIGURATION ====================

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = "gemini-3.8-flash"
OPERATING_SYSTEM = platform.system()

if not API_KEY:
    raise SystemExit(
        "GEMINI_API_KEY missing hai. Project folder mein .env file check karo."
    )

print(f"Operating System: {OPERATING_SYSTEM}")

client = genai.Client(api_key=API_KEY)

recognizer = sr.Recognizer()
recognizer.dynamic_energy_threshold = True
recognizer.pause_threshold = 0.8


# ==================== AUTO VOICE ENGINE ====================

def initialize_voice():
    """Automatically select a suitable voice engine for the OS."""

    drivers = {
        "Windows": "sapi5",
        "Darwin": "nsss",
        "Linux": "espeak",
    }

    driver = drivers.get(OPERATING_SYSTEM)

    try:
        if driver:
            engine = pyttsx3.init(driverName=driver)
        else:
            engine = pyttsx3.init()

        engine.setProperty("rate", 175)
        engine.setProperty("volume", 1.0)
        return engine

    except Exception as error:
        print(f"Voice engine initialization failed: {error}")
        print("Jarvis text mode mein continue karega.")
        return None


speaker = initialize_voice()


# ==================== GEMINI CHAT ====================

try:
    chat = client.chats.create(
        model=MODEL,
        config=types.GenerateContentConfig(
            system_instruction=(
                "You are Jarvis, a helpful personal voice assistant. "
                "Reply in the same language as the user where possible. "
                "Use simple Hindi, Hinglish, or English. "
                "Keep answers concise and natural for speech. "
                "Avoid unnecessary Markdown and tables."
            ),
            temperature=0.7,
        ),
    )
except Exception as error:
    raise SystemExit(f"Gemini initialization error: {error}")


# ==================== TEXT TO SPEECH ====================

def say(text):
    """Print the response and speak it using the detected OS engine."""

    if not text:
        return

    text = str(text).strip()
    print(f"\nJarvis: {text}\n")

    if speaker is None:
        return

    spoken_text = re.sub(
        r"```.*?```", "code block omitted", text, flags=re.DOTALL
    )
    spoken_text = re.sub(r"https?://\S+", "link", spoken_text)
    spoken_text = re.sub(r"[*#_`]", "", spoken_text)
    spoken_text = re.sub(r"\s+", " ", spoken_text).strip()

    try:
        speaker.say(spoken_text)
        speaker.runAndWait()
    except Exception as error:
        print(f"Voice output error: {error}")


# ==================== SPEECH RECOGNITION ====================

def take_command():
    """Listen through the default microphone."""

    try:
        with sr.Microphone() as source:
            print("Listening... Bolo!")
            recognizer.adjust_for_ambient_noise(source, duration=0.5)

            audio = recognizer.listen(
                source,
                timeout=8,
                phrase_time_limit=12,
            )

        print("Recognizing...")

        query = recognizer.recognize_google(
            audio, language="en-IN"
        ).strip().lower()

        if query:
            print(f"You: {query}")

        return query

    except sr.WaitTimeoutError:
        print("Koi awaaz nahi mili.")
    except sr.UnknownValueError:
        print("Awaaz samajh nahi aayi. Dobara bolo.")
    except sr.RequestError as error:
        print(f"Speech recognition internet/service error: {error}")
    except (OSError, AttributeError) as error:
        print(f"Microphone error: {error}")
        print("Microphone permission, audio device aur PyAudio check karo.")

    return ""


# ==================== GEMINI AI ====================

def ask_gemini(query):
    """Ask Gemini and return its text response."""

    try:
        response = chat.send_message(query)
        answer = getattr(response, "text", None)

        if answer and answer.strip():
            return answer.strip()

        return "Sorry, mujhe abhi iska answer nahi mila."

    except Exception as error:
        print(f"GEMINI ERROR: {error}")
        message = str(error).lower()

        if "429" in message or "resource_exhausted" in message:
            return "Gemini request limit reach ho gayi hai. Baad mein try karo."
        if "404" in message or "not_found" in message:
            return "Gemini model available nahi hai. Model ID check karo."
        if "api key" in message or "api_key" in message:
            return "Gemini API key check karo."
        if "connection" in message or "timeout" in message:
            return "Internet connection check karo."

        return "Gemini se response nahi mila. Terminal mein error check karo."


# ==================== COMMAND HANDLER ====================

def handle_command(query):
    """Run local commands or ask Gemini."""

    if not query:
        return True

    # Exit
    if query in {
        "exit", "quit", "goodbye", "stop jarvis",
        "jarvis stop", "band ho jao",
    }:
        say("Goodbye! Jarvis signing off.")
        return False

    # Greetings
    if query in {"hi", "hello", "hey", "hi jarvis", "hello jarvis"}:
        say("Hello! Main Jarvis hoon. Batao, kya help chahiye?")
        return True

    # Websites
    websites = {
        "youtube": "https://www.youtube.com",
        "open youtube": "https://www.youtube.com",
        "youtube kholo": "https://www.youtube.com",
        "google": "https://www.google.com",
        "open google": "https://www.google.com",
        "google kholo": "https://www.google.com",
        "github": "https://github.com",
        "open github": "https://github.com",
        "github kholo": "https://github.com",
        "chatgpt": "https://chatgpt.com",
        "open chatgpt": "https://chatgpt.com",
    }

    if query in websites:
        site = websites[query]
        say(f"{query} open kar raha hoon.")
        webbrowser.open(site)
        return True

    # Time
    if query in {"time", "current time", "what is the time", "time batao"}:
        say(f"Abhi time hai {datetime.now().strftime('%I:%M %p')}.")
        return True

    # Date
    if query in {"date", "today's date", "what is the date", "date batao"}:
        say(f"Aaj ki date hai {datetime.now().strftime('%d %B %Y')}.")
        return True

    # YouTube playback
    if query.startswith("play "):
        song = query[5:].strip()

        if song:
            say(f"YouTube par {song} play karne ki koshish kar raha hoon.")
            try:
                pywhatkit.playonyt(song)
            except Exception as error:
                print(f"YouTube error: {error}")
                say("Video open nahi ho paya.")

        return True

    # Other questions: Gemini
    answer = ask_gemini(query)
    say(answer)
    return True


# ==================== MAIN ====================

def main():
    print("=" * 48)
    print("       CROSS-PLATFORM JARVIS")
    print("=" * 48)
    print(f"OS: {OPERATING_SYSTEM}")
    print(f"Gemini model: {MODEL}")
    print("Commands: YouTube, Google, play songs, ask questions, exit")
    print()

    say("Hello! Jarvis is online. How can I help you?")

    while True:
        query = take_command()

        if query:
            if not handle_command(query):
                break


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nJarvis stopped.")
    finally:
        if speaker is not None:
            try:
                speaker.stop()
            except Exception:
                pass
