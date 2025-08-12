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

MAX_SINGLE_CHUNK_MS = 60_000
OVERLAP_MS = 10_000
WEBM_MAGIC = b"\x1a\x45\xdf\xa3"


@anvil.server.callable
def process_audio_whisper(audio_blob, language):
  return anvil.server.launch_background_task(
    "bg_process_audio_whisper", audio_blob, language
  )


@anvil.server.background_task
def bg_process_audio_whisper(audio_blob, language):
  # --- Helper for Whisper API call ---
  def whisper_call(seg):
    buf = io.BytesIO()
    seg.export(buf, format="wav")
    buf.seek(0)
    buf.name = "audio.wav"

    for n in range(RETRY_LIMIT):
      try:
        return client.audio.transcriptions.create(
          model="whisper-1", file=buf, language=language
        ).text
      except Exception as e:
        if n < RETRY_LIMIT - 1:
          time.sleep(2**n)
          print(f"[WARN] Whisper retry {n + 1}/{RETRY_LIMIT}: {e}")
        else:
          return {
            "error": "La transcription par Whisper a échoué après plusieurs tentatives."
          }

  # --- 0. Convert to raw bytes ---
  if isinstance(audio_blob, str):
    try:
      audio_bytes = base64.b64decode(audio_blob, validate=True)
    except Exception:
      return {"error": "Chaîne audio Base-64 invalide."}
  elif hasattr(audio_blob, "get_bytes"):
    audio_bytes = audio_blob.get_bytes()
  elif isinstance(audio_blob, (bytes, bytearray)):
    audio_bytes = bytes(audio_blob)
  else:
    return {"error": "Type de blob audio non supporté."}

  # --- 1. Load with pydub ---
  def try_load(fmt=None):
    try:
      return AudioSegment.from_file(io.BytesIO(audio_bytes), format=fmt)
    except Exception:
      return None

  audio = None
  header = audio_bytes[:16]
  if header.startswith(WEBM_MAGIC):
    audio = try_load("webm")
  elif header.startswith(b"OggS"):
    audio = try_load("ogg")
  elif header.startswith(b"fLaC"):
    audio = try_load("flac")
  elif header.startswith(b"RIFF"):
    audio = try_load("wav")
  elif header[:3] in (b"\xff\xf1", b"\xff\xf9") or header.startswith(b"ID3"):
    audio = try_load("mp3")
  elif header[4:8] in (b"M4A ", b"MP4 ", b"isom", b"iso2", b"mp42"):
    audio = try_load("mp4")
  elif header.startswith(b"caff"):
    audio = try_load("caf")

  if audio is None:
    for fmt in ["webm", "ogg", "flac", "wav", "mp3", "m4a", "caf", "mp4", "aac"]:
      audio = try_load(fmt)
      if audio:
        break

  if audio is None:
    return {"error": "Format audio non supporté. Le fichier n'a pas pu être lu."}

  # --- 2. Sanity checks and Normalization ---
  if len(audio) < 150:
    pad = AudioSegment.silent(duration=300)
    audio = pad + audio + pad

  if audio.dBFS == float("-inf") or audio.dBFS < -80:
    return {"error": "L'audio est silencieux. Veuillez enregistrer à nouveau."}

  audio = audio.set_channels(1).set_frame_rate(16000)

  # --- 3. Transcription (with chunking) ---
  if len(audio) <= MAX_SINGLE_CHUNK_MS:
    transcription = whisper_call(audio)
  else:
    parts, p = [], 0
    while p < len(audio):
      q = min(p + MAX_SINGLE_CHUNK_MS + OVERLAP_MS, len(audio))
      parts.append(whisper_call(audio[p:q]).strip())
      p += MAX_SINGLE_CHUNK_MS
    transcription = " ".join(parts)

  return transcription
