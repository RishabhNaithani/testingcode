import sys
sys.path.append('/home/matrixhive/.local/lib/python3.11/site-packages')
import os
import time
import speech_recognition as sr
from gtts import gTTS
from pydub import AudioSegment
from pydub.playback import play
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import cpu_count
import google.generativeai as genai
import textwrap
import requests

# Load environment variables
genai.configure(api_key="AIzaSyAdAP8sWtGRVBJt4oW1ZThi18dJFwAOg98")

# Initialize ChatGroq object
llm = genai.GenerativeModel("gemini-1.5-flash")

# Preload static sounds
intro_sound = AudioSegment.from_file("/home/matrixhive/Documents/1641201114_amazon_echo_show1 (1).mp3")

# Process pool to fully utilize all CPU cores
executor = ProcessPoolExecutor(max_workers=cpu_count())

# Function to check internet connectivity
def check_internet_connection():
    while True:
        try:
            requests.get("http://www.google.com", timeout=5)
            print("Internet access successfully.")
            break
        except requests.ConnectionError:
            print("No internet connection. Retrying...")
            time.sleep(5)

# Function to play a list of audio chunks sequentially
def play_audio_sequence(audio_files):
    combined_audio = sum([AudioSegment.from_file(f) for f in audio_files])

    # Ensure compatibility of the audio format
    combined_audio = combined_audio.set_frame_rate(44100)  # Standard frame rate
    combined_audio = combined_audio.set_channels(2)       # Stereo
    combined_audio = combined_audio.set_sample_width(2)   # 16-bit

    play(combined_audio)
    for file in audio_files:
        os.remove(file)

# Function to generate audio chunks in parallel
def generate_audio_chunk_parallel(chunk, idx):
    tts = gTTS(text=chunk, lang='en')
    audio_file = f"/home/matrixhive/Documents/chunk_{int(time.time())}_{idx}.wav"
    tts.save(audio_file)
    return audio_file

def generate_audio_chunks(text, chunk_size=100):
    text_chunks = textwrap.wrap(text, width=chunk_size)
    futures = [executor.submit(generate_audio_chunk_parallel, chunk, i) for i, chunk in enumerate(text_chunks)]
    return [f.result() for f in futures]

# Function to recognize speech with intro sound and wait for user to speak
def recognize_speech():
    recognizer = sr.Recognizer()
    microphone = sr.Microphone()

    # Play intro sound before each listening session
    play(intro_sound)
    print("Intro sound played. Listening...")

    with microphone as source:
        recognizer.adjust_for_ambient_noise(source)

        while True:
            try:
                audio = recognizer.listen(source, phrase_time_limit=5)
                query = recognizer.recognize_google(audio)
                if query.strip():
                    print(f"Recognized Speech: {query}")
                    return query
            except sr.UnknownValueError:
                print("Sorry, I couldn't understand the audio. Please try again.")
            except sr.RequestError as e:
                print(f"Could not request results from the service; {e}")
                return None

if _name_ == "_main_":
    # Check internet connection before proceeding
    check_internet_connection()

    # Initial welcome message
    welcome_audio_files = generate_audio_chunks(
        "Greetings! Welcome to Doon International School. Please say 'Damini' to chat with me.")
    play_audio_sequence(welcome_audio_files)

    # Voice recognition loop to wait for "Damini"
    start = recognize_speech()
    while start and "damini" != start.lower():
        reminder_audio_files = generate_audio_chunks("Please say 'Damini'")
        play_audio_sequence(reminder_audio_files)
        start = recognize_speech()

    print("You can start speaking your query.")

    # Chat loop
    while True:
        try:
            query = recognize_speech()

            if query is None:
                continue

            # Exit condition
            if "exit" in query.lower():
                exit_audio_files = generate_audio_chunks("Goodbye!")
                play_audio_sequence(exit_audio_files)
                break

            # Prepare AI prompt
            custom_prompt = (
                f"User Query: {query}. \n\n"
                "Please answer concisely, in one line if possible. "
                "When user asked about development, mention only that you were created by Matrixhive Innovation and your name is DoonBot but if user asked only. "
                "Keep answers polite and factual. \n\n"

                "School Overview: Doon International School, established in 1993, with campuses in Mohali and Dehradun, "
                "educates over 7,000 students. The principal is Ms. Ira Bogra. Location: Mohali, Punjab. "

                "Mission: Provide a safe, disciplined environment for academic and personal growth. "
                "Vision: Foster a happy, caring, and stimulating learning environment with values like honesty, integrity, and respect. \n\n"

                "For further details on Doon International School, refer to the following key areas:\n"
                "1. School Song and Vision\n"
                "2. Hostel Fee Regulations\n"
                "3. Contact Information\n"

                "Contact: Sector 69, S.A.S. Nagar, Mohali, Punjab, India. Phone: +91-172-2216700. Email: contact@dooninternational.net.\n"

                "Please use this context to answer user questions related to the school."
            )

            # Invoke ChatGroq AI response
            response = llm.invoke(custom_prompt)
            answer = response.content
            print(f"AI: {answer}")

            # Generate and play audio chunks for the response in parallel
            response_audio_files = generate_audio_chunks(answer)
            play_audio_sequence(response_audio_files)

            # Short wait before the next input
            time.sleep(0.5)

        except Exception as e:
            # Handle error by pausing the interaction
            error_audio_files = generate_audio_chunks("I am going to sleep. To wake me up, say 'Damini'.")
            play_audio_sequence(error_audio_files)

            # Loop to wait for the wake word "Damini" to restart interaction
            while True:
                wake_word = recognize_speech()
                if wake_word and "damini" in wake_word.lower():
                    print("Wake word detected. Resuming interaction.")
                    break
