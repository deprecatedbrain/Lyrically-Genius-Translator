import openai
import os
import sys
import questionary
from questionary import Style
from dotenv import load_dotenv
from lyricsgenius import Genius
from requests.exceptions import HTTPError

yellow_theme = Style([
    ("qmark", "fg:#ffff00 bold"),
    ("question", "fg:#ffffff"),
    ("answer", "fg:#ffff00 bold"),
    ("pointer", "fg:#ffff00 bold"),
    ("highlighted", "fg:#ffff00 bold"),
    ("selected", "fg:#ffff00"), 
    ("separator", "fg:#ffff00"),
    ("instruction", "fg:#cccc00"),
])

load_dotenv()
GENIUS_API_KEY = os.getenv("GENIUS_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not GENIUS_API_KEY:
    print("Error: GENIUS_API_KEY not found. Please set it in your .env file.")
    sys.exit(1)
if not OPENAI_API_KEY:
    print("Error: OPENAI_API_KEY not found. Please set it in your .env file.")
    sys.exit(1)

openai.api_key = OPENAI_API_KEY
genius_client = Genius(GENIUS_API_KEY)
VERSION = "0.1.0"

def handle_http_error(e):
    status = None
    try:
        status = e.response.status_code
    except Exception:
        pass
    if status == 401:
        print("Authentication error: Invalid or expired Genius API key.")
        print("Please update your GENIUS_API_KEY in the .env file and restart the program.")
        sys.exit(1)
    else:
        print(f"HTTP error ({status}): {e}")

def main():
    print(f"Lyrically Genius Translation v{VERSION}\n")

    model = questionary.select(
        "Which OpenAI model should be used for translation?",
        choices=[
            "gpt-4.1",
            "gpt-4.1-mini",
            "gpt-4.1-nano",
            "gpt-4o",
            "gpt-4o-mini"
        ],
        style=yellow_theme
    ).ask()

    while True:
        search_query = questionary.text("What song?", style=yellow_theme).ask()
        try:
            search_results = genius_client.search(search_query)
        except HTTPError as e:
            handle_http_error(e)
            continue

        # Present search results to the user
        hits = search_results.get('hits', [])
        if not hits:
            print("No results found. Try another query.")
            continue
        choices = [hit['result']['full_title'] for hit in hits]
        choices.append("🔄 Search again")

        selected = questionary.select(
            "Select a result:",
            choices=choices,
            style=yellow_theme
        ).ask()

        if selected == "🔄 Search again":
            continue

        selected_hit = next(
            (hit for hit in hits if hit['result']['full_title'] == selected),
            None
        )
        if not selected_hit:
            print("Could not find the selected song. Please try again.")
            continue

        song_title = selected_hit['result']['title']
        artist_name = selected_hit['result']['primary_artist']['name']
        print(f"Fetching lyrics for: {song_title} by {artist_name}...\n")

        try:
            song = genius_client.search_song(song_title, artist_name)
            lyrics = song.lyrics
        except HTTPError as e:
            handle_http_error(e)
            continue
        except Exception as e:
            print(f"Unexpected error: {e}")
            continue

        target = questionary.text(
            "Translate to which language?", 
            style=yellow_theme
        ).ask()

        instructions = (
            "You are a translating AI. You will be provided with a language to translate to and from. Make sure to retain all meaning and nuances from the original text as possible. Provide only the translated text, nothing extra."
        )
        
        input_msg = f"Translate from: Detect Language\nTranslate to: {target}\n\n[BEGIN_LYRICS]\n{lyrics}"

        try:
            response = openai.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": instructions},
                    {"role": "user", "content": input_msg}
                ]
            )
            translated = response.choices[0].message.content
        except Exception as e:
            print(f"Error from OpenAI API: {e}")
            continue

        print("\n=== Translated Lyrics ===\n")
        print(translated)
        print("\n========================\n")

        again = questionary.confirm(
            "Translate another song?", 
            default=True,
            style=yellow_theme
        ).ask()

        if not again:
            print("Goodbye!")
            break

if __name__ == "__main__":
    main()
