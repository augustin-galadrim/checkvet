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
  # --- Remplacement des logs par des prints formatés ---

  print(
    f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] {CONTEXT} --- BG_TASK_START --- Tâche de fond démarrée."
  )
  print(
    f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] {CONTEXT} --- BG_TASK_INFO --- Langue: {language}, Type MIME: {mime_type}"
  )

  def whisper_call(segment):
    wav_buffer = io.BytesIO()
    segment.export(wav_buffer, format="wav")
    wav_buffer.seek(0)
    wav_buffer.name = "audio.wav"

    for n in range(RETRY_LIMIT):
      try:
        print(
          f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [DEBUG] {CONTEXT} Appel API Whisper, tentative {n + 1}/{RETRY_LIMIT}."
        )
        transcript = client.audio.transcriptions.create(
          model="whisper-1", file=wav_buffer, language=language
        )
        print(
          f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [DEBUG] {CONTEXT} Appel API Whisper réussi."
        )
        return transcript.text
      except Exception as e:
        wait_time = 2**n
        print(
          f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [WARNING] {CONTEXT} Tentative {n + 1} de l'API Whisper a échoué : {e}. Nouvelle tentative dans {wait_time}s..."
        )
        if n < RETRY_LIMIT - 1:
          time.sleep(wait_time)
        else:
          print(
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] {CONTEXT} La transcription Whisper a échoué après {RETRY_LIMIT} tentatives."
          )
          print(traceback.format_exc())
          return {
            "error": "La transcription Whisper a échoué après plusieurs tentatives."
          }

  # --- Étape 0 : Obtenir les octets bruts de l'objet Media ---
  try:
    audio_bytes = audio_blob.get_bytes()
    print(
      f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] {CONTEXT} CHECKPOINT 1 : Taille des octets reçus du client : {len(audio_bytes)} octets."
    )
    if len(audio_bytes) < 1000:
      print(
        f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [WARNING] {CONTEXT} La taille des données reçues est très faible, suspectant un fichier vide ou corrompu."
      )
  except Exception as e:
    print(
      f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] {CONTEXT} CHECKPOINT 1 ÉCHEC : Impossible d'obtenir les octets de l'objet média : {e}"
    )
    print(traceback.format_exc())
    return {"error": "Objet média invalide reçu."}

  # --- CHECKPOINT 2 : Tentative de chargement par pydub ---
  raw_audio = None
  file_format = None
  if mime_type and "/" in mime_type:
    file_format = mime_type.split("/")[1].replace("x-", "")
    if file_format in ["aac", "mpeg"]:
      file_format = "m4a" if file_format == "aac" else "mp3"

  try:
    print(
      f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] {CONTEXT} CHECKPOINT 2 : Tentative de chargement de l'audio avec l'indice de format : '{file_format}'"
    )
    raw_audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format=file_format)
  except Exception as e:
    print(
      f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [WARNING] {CONTEXT} Impossible de charger l'audio avec l'indice '{file_format}': {e}. Tentative de détection automatique."
    )
    try:
      raw_audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
    except Exception as final_e:
      print(
        f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] {CONTEXT} CHECKPOINT 2 ÉCHEC : Pydub n'a pas réussi à charger l'audio. Erreur : {final_e}"
      )
      print(traceback.format_exc())
      return {
        "error": "Format audio non supporté. Le fichier n'a pas pu être lu par le serveur."
      }

  # --- CHECKPOINT 3 : Vérifier le résultat après chargement par pydub ---
  duration_ms = len(raw_audio)
  dbfs = raw_audio.dBFS
  print(
    f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] {CONTEXT} CHECKPOINT 3 : Durée de l'audio après chargement par pydub : {duration_ms} ms."
  )
  print(
    f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] {CONTEXT} CHECKPOINT 3 : Niveau sonore (dBFS) : {dbfs}."
  )
  if duration_ms == 0:
    print(
      f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] {CONTEXT} ERREUR FATALE : Pydub a chargé l'audio mais sa durée est de 0 ms. Le fichier est considéré comme vide."
    )
    return "Erreur de décodage, audio vide."

  # --- Normalisation ---
  try:
    print(
      f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] {CONTEXT} Normalisation de l'audio en WAV mono 16kHz pour le traitement."
    )
    normalized_audio = raw_audio.set_frame_rate(16000).set_channels(1)
  except Exception as e:
    print(
      f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] {CONTEXT} Échec lors de l'étape de normalisation de l'audio : {e}"
    )
    print(traceback.format_exc())
    return {"error": "Échec de la normalisation de l'audio."}

  # --- Traitement Final ---
  if normalized_audio.dBFS == float("-inf") or normalized_audio.dBFS < -80:
    print(
      f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [WARNING] {CONTEXT} L'audio semble être silencieux après normalisation."
    )
    return ""

  if len(normalized_audio) <= MAX_SINGLE_CHUNK_MS:
    transcription = whisper_call(normalized_audio)
  else:
    print(
      f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] {CONTEXT} L'audio normalisé est trop long ({len(normalized_audio)}ms). Découpage en morceaux."
    )
    parts = []
    p = 0
    while p < len(normalized_audio):
      chunk = normalized_audio[p : p + MAX_SINGLE_CHUNK_MS]
      parts.append(whisper_call(chunk).strip())
      p += MAX_SINGLE_CHUNK_MS
    transcription = " ".join(parts)

  print(
    f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] {CONTEXT} Transcription terminée. Longueur du résultat : {len(transcription)} caractères."
  )
  print(
    f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [DEBUG] {CONTEXT} Transcription Finale (100 premiers caractères) : {transcription[:100]}"
  )
  return transcription
