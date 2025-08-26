import anvil.secrets
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
import time
from . import client, RETRY_LIMIT
import base64
from pydub import AudioSegment
import io
from datetime import datetime
import traceback
import anvil.media

# --- Suppression de la dépendance au logger personnalisé ---
# from ...logging_server import get_logger
# logger = get_logger(__name__)

MAX_SINGLE_CHUNK_MS = 60_000
OVERLAP_MS = 10_000
WEBM_MAGIC = b"\x1a\x45\xdf\xa3"

# --- Contexte pour les messages de log ---
CONTEXT = "[SERVER:transcription]"


@anvil.server.callable
def process_audio_whisper(audio_blob, language, mime_type=None):
  return anvil.server.launch_background_task(
    "bg_process_audio_whisper", audio_blob, language, mime_type
  )


@anvil.server.background_task
def bg_process_audio_whisper(audio_blob, language, mime_type):
  """
  Attempts to transcribe an audio blob by sending it directly to Whisper
  without any conversion. This is for diagnostic purposes.
  """
  print(f"--- DIRECT TRANSCRIPTION ATTEMPT ---")
  try:
    audio_bytes = audio_blob.get_bytes()
    print(f"Received {len(audio_bytes)} bytes to send directly.")

    # We must create an in-memory file-like object for the OpenAI library
    in_memory_file = io.BytesIO(audio_bytes)

    # The library needs a filename to guess the type, this is crucial
    filename = f"audio.{mime_type.split('/')[1]}"  # e.g., 'audio.mp4'
    in_memory_file.name = filename
    print(f"Sending to Whisper as '{filename}'...")

    transcript = client.audio.transcriptions.create(
      model="whisper-1", file=in_memory_file, language=language
    )

    result = transcript.text
    print(f"SUCCESS: Direct transcription returned: {result}")
    return {"success": True, "transcription": result}

  except Exception as e:
    error_message = f"FAILURE: Direct transcription crashed with an error: {str(e)}"
    print(error_message)
    print(traceback.format_exc())
    return {"success": False, "error": error_message}
