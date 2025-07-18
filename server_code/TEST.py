import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
import io
import base64
from datetime import datetime
from pydub import AudioSegment
import anvil.users
import anvil.server
from .AI import client


@anvil.server.callable
def process_and_log_test(audio_blob):
  """
  Processes an incoming audio blob (bytes or base64-encoded string),
  transcribes it via Whisper, logs the transcription to the microphone_tests
  table with the current user as 'user', the transcription text as 'test',
  and the current time as 'date', and returns the transcription text.
  """
  try:
    print(f"[process_and_log_test] Received audio_blob type: {type(audio_blob)}")

    # Convert the audio_blob to bytes if it's a base64-encoded string
    if isinstance(audio_blob, str):
      print("[process_and_log_test] Converting base64 string to bytes...")
      audio_bytes = base64.b64decode(audio_blob)
    else:
      audio_bytes = audio_blob

    print(f"[process_and_log_test] Audio bytes length: {len(audio_bytes)}")
    print(f"[process_and_log_test] First 100 bytes (hex): {audio_bytes[:100].hex()}")

    # (Optional) Save raw bytes to a temporary file for debugging
    with open('raw_audio_input_test', 'wb') as f:
      f.write(audio_bytes)
    print("[process_and_log_test] Raw audio saved to 'raw_audio_input_test'")

    # --- Attempt to detect the audio format automatically ---
    try:
      audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
      print("[process_and_log_test] Audio format auto-detected successfully.")
    except Exception as e:
      print("[process_and_log_test] Auto-detection failed. Attempting manual format checks...")
      header = audio_bytes[:4]
      if header.startswith(b'OggS'):
        guessed_format = 'ogg'
      elif header.startswith(b'fLaC'):
        guessed_format = 'flac'
      elif header.startswith(b'RIFF'):
        guessed_format = 'wav'
      elif header.startswith(b'\xFF\xF1') or header.startswith(b'\xFF\xF9'):
        guessed_format = 'mp3'
      else:
        guessed_format = 'mp3'
      print(f"[process_and_log_test] Guessed format: {guessed_format}")
      audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format=guessed_format)

    print(f"[process_and_log_test] Audio loaded successfully. Duration: {len(audio)} ms")

    # --- Optional Audio Optimization / Downsampling ---
    audio = audio.set_frame_rate(12000).set_channels(1)
    print(f"[process_and_log_test] Audio optimized. New duration: {len(audio)} ms")

    # --- Convert to a consistent format (e.g., MP3) for Whisper ---
    buffer = io.BytesIO()
    audio.export(buffer, format="mp3", bitrate="16k")
    mp3_bytes = buffer.getvalue()
    print(f"[process_and_log_test] Converted to MP3. Size: {len(mp3_bytes)} bytes")

    # Create a file-like object from the MP3 bytes (Whisper requires a file-like object)
    audio_file = io.BytesIO(mp3_bytes)
    audio_file.name = 'audio.mp3'

    # Use the converted MP3 file for transcription via Whisper
    response = client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file,
        language="fr"
    )
    transcription_text = response.text
    print("[process_and_log_test] Transcription completed successfully.")
    print(f"[process_and_log_test] Transcription: {transcription_text}")

    # --- Log the transcription to the microphone_tests table ---
    current_user = anvil.users.get_user()
    current_time = datetime.now()  # Get the current time
    app_tables.microphone_tests.add_row(
        user=current_user,
        test=transcription_text,
        date=current_time
    )
    print("[process_and_log_test] Transcription logged to 'microphone_tests' with current time.")

    return transcription_text

  except Exception as e:
    error_message = f"[process_and_log_test] Error: {str(e)}"
    print(error_message)
    raise Exception("Error processing audio test transcription: " + str(e))
