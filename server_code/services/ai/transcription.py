import anvil.server
from . import client
import io
import traceback
from datetime import datetime

CONTEXT = "[SERVER:transcription]"


def transcribe_audio(audio_blob, language, mime_type):
  """
  Transcribes an audio blob by sending it directly to the Whisper API.
  This is the primary, reliable method for audio transcription.

  Returns the transcription text on success, or raises an Exception on failure.
  """
  print(
    f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] {CONTEXT} Starting audio transcription..."
  )
  try:
    # Step 1: Get the raw bytes from the client.
    audio_bytes = audio_blob.get_bytes()

    # Step 2: Prepare a file-like object for the OpenAI library.
    # The filename with a proper extension is crucial for the API.
    in_memory_file = io.BytesIO(audio_bytes)
    extension = mime_type.split("/")[-1] if "/" in mime_type else "mp4"
    filename = f"audio.{extension}"
    in_memory_file.name = filename

    print(
      f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] {CONTEXT} Sending {len(audio_bytes)} bytes to Whisper as '{filename}'..."
    )

    # Step 3: Make the direct API call.
    transcript = client.audio.transcriptions.create(
      model="whisper-1", file=in_memory_file, language=language
    )

    result_text = transcript.text
    print(
      f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] {CONTEXT} Transcription successful. Result length: {len(result_text)} chars."
    )
    return result_text

  except Exception as e:
    print(
      f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] {CONTEXT} Transcription failed. Error: {str(e)}"
    )
    print(traceback.format_exc())
    # Re-raise the exception to be caught by the calling background task.
    raise e
