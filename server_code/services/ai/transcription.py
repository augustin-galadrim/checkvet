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
def bg_process_audio_whisper(audio_blob, language, mime_type=None):
  """
  Processes an audio blob by first sanitizing its file structure and then transcribing it.
  This robustly handles files from sources like iPhones that place metadata at the end.
  """
  print(
    f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] {CONTEXT} --- BG_TASK_START --- Tâche de fond démarrée."
  )
  print(
    f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] {CONTEXT} --- BG_TASK_INFO --- Langue: {language}, Type MIME: {mime_type}"
  )

  try:
    # STEP 1: Get bytes and save to a temporary file. This is crucial for FFmpeg to seek properly.
    audio_bytes = audio_blob.get_bytes()
    print(
      f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] {CONTEXT} CHECKPOINT 1: Octets reçus du client: {len(audio_bytes)} octets."
    )

    with anvil.media.TempFile() as tmp_file_path:
      with open(tmp_file_path, "wb") as f:
        f.write(audio_bytes)

        # STEP 2: Load the audio from the file path.
        # This is the critical sanitization step. By loading from a file path,
        # we force FFmpeg to seek for the 'moov atom' (even at the end) and
        # correctly reconstruct the audio stream in memory.
      print(
        f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] {CONTEXT} CHECKPOINT 2: Chargement de l'audio depuis le fichier temporaire pour réparation..."
      )
      raw_audio = AudioSegment.from_file(tmp_file_path)

      duration_ms = len(raw_audio)
      print(
        f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] {CONTEXT} CHECKPOINT 3: Audio chargé avec succès. Durée détectée: {duration_ms} ms."
      )

      # If duration is still too short, the file is genuinely empty or corrupted.
      if duration_ms < 500:  # Using a 500ms threshold
        print(
          f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [WARNING] {CONTEXT} La durée est trop courte. L'audio est peut-être silencieux ou corrompu."
        )
        return ""

        # STEP 3: Normalize the (now correct) audio and prepare it for Whisper.
      normalized_audio = raw_audio.set_frame_rate(16000).set_channels(1)

      wav_buffer = io.BytesIO()
      normalized_audio.export(wav_buffer, format="wav")
      wav_buffer.seek(0)
      wav_buffer.name = "audio.wav"

      # STEP 4: Call the Whisper API with the clean WAV data.
      for n in range(RETRY_LIMIT):
        try:
          print(
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [DEBUG] {CONTEXT} Appel API Whisper, tentative {n + 1}/{RETRY_LIMIT}."
          )
          wav_buffer.seek(0)
          transcript = client.audio.transcriptions.create(
            model="whisper-1", file=wav_buffer, language=language
          )

          final_transcription = transcript.text
          print(
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] {CONTEXT} Transcription terminée. Longueur: {len(final_transcription)} caractères."
          )
          return final_transcription

        except Exception as e:
          wait_time = 2**n
          print(
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [WARNING] {CONTEXT} Tentative {n + 1} de l'API Whisper a échoué: {e}. Nouvelle tentative dans {wait_time}s..."
          )
          if n < RETRY_LIMIT - 1:
            time.sleep(wait_time)
          else:
            print(
              f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] {CONTEXT} La transcription Whisper a échoué après {RETRY_LIMIT} tentatives."
            )
            return {
              "error": "La transcription Whisper a échoué après plusieurs tentatives."
            }

  except Exception as e:
    print(
      f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] {CONTEXT} Une erreur critique est survenue: {e}"
    )
    print(traceback.format_exc())
    return {
      "error": "Une erreur serveur est survenue lors du traitement du fichier audio."
    }

@anvil.server.callable
def transcribe_direct_to_whisper(audio_blob, language, mime_type):
  """
    Attempts to transcribe an audio blob by sending it directly to Whisper
    without any conversion. This is for diagnostic purposes.
    """
  print(f"--- DIRECT TRANSCRIPTION ATTEMPT ---")
  try:
    # Step 1: Get the raw bytes from the client.
    audio_bytes = audio_blob.get_bytes()
    print(f"Received {len(audio_bytes)} bytes to send directly to Whisper.")

    # Step 2: The OpenAI library needs a file-like object, not just raw bytes.
    # We also MUST give it a filename with a proper extension so the API knows how to handle it.
    in_memory_file = io.BytesIO(audio_bytes)
    extension = mime_type.split('/')[-1] # e.g., 'mp4' from 'audio/mp4'
    filename = f"audio.{extension}"
    in_memory_file.name = filename # This is the crucial part

    print(f"Sending data to Whisper API, identifying it as '{filename}'...")

    # Step 3: Make the direct API call.
    transcript = client.audio.transcriptions.create(
      model="whisper-1",
      file=in_memory_file,
      language=language
    )

    result_text = transcript.text
    print(f"SUCCESS: Direct transcription returned {len(result_text)} characters.")
    print(f"   -> Transcription: '{result_text}'")
    return {"success": True, "transcription": result_text}

  except Exception as e:
    error_message = f"FAILURE: Direct transcription crashed. Error: {str(e)}"
    print(error_message)
    print(traceback.format_exc()) # Print full traceback for detailed debugging
    return {"success": False, "error": error_message}