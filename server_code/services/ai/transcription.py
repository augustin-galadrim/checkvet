import anvil.server
from . import client
import io
import traceback
from datetime import datetime
from pydub import AudioSegment


CONTEXT = "[SERVER:transcription]"
# Set a safe limit just below OpenAI's 25MB limit to be safe.
MAX_FILE_SIZE_BYTES = 24 * 1024 * 1024


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
    audio_bytes = audio_blob.get_bytes()
    if len(audio_bytes) > MAX_FILE_SIZE_BYTES:
      print(
        f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [WARNING] {CONTEXT} Audio file exceeds size limit. Compressing..."
      )
      try:
        audio_segment = AudioSegment.from_file(io.BytesIO(audio_bytes))
        compressed_audio_io = io.BytesIO()
        audio_segment.export(compressed_audio_io, format="mp3", bitrate="64k")
        audio_bytes = compressed_audio_io.getvalue()
        new_size_mb = len(audio_bytes) / (1024 * 1024)
        print(
          f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] {CONTEXT} Compression successful. New size: {new_size_mb:.2f} MB."
        )
      except Exception as e:
        print(
          f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] {CONTEXT} Failed to compress audio file: {e}"
        )
        raise Exception(f"Failed to compress oversized audio file: {e}")

    in_memory_file = io.BytesIO(audio_bytes)
    if mime_type and "/" in mime_type:
      # First, strip any parameters like ';codecs=opus'
      main_mime_type = mime_type.split(";")[0]
      extension = main_mime_type.split("/")[-1]

      # Handle non-standard prefixes like 'x-m4a' -> 'm4a'
      if "x-" in extension:
        extension = extension.split("x-")[-1]
      else:
        extension = "mp4"  # Fallback
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
