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
from ...logging_server import get_logger

logger = get_logger(__name__)

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
  logger.info("Starting background task for audio transcription.")
  logger.debug(f"Language for transcription: {language}")

  def whisper_call(seg):
    buf = io.BytesIO()
    seg.export(buf, format="wav")
    buf.seek(0)
    buf.name = "audio.wav"

    for n in range(RETRY_LIMIT):
      try:
        logger.debug(f"Whisper API call attempt {n + 1}/{RETRY_LIMIT}.")
        transcript = client.audio.transcriptions.create(
          model="whisper-1", file=buf, language=language
        )
        logger.debug(f"Whisper API call successful.")
        return transcript.text
      except Exception as e:
        wait_time = 2**n
        logger.warning(f"Whisper API attempt {n + 1} failed: {e}. Retrying in {wait_time}s...")
        if n < RETRY_LIMIT - 1:
          time.sleep(wait_time)
        else:
          logger.error(f"Whisper transcription failed after {RETRY_LIMIT} attempts.", exc_info=True)
          return {"error": "Whisper transcription failed after multiple retries."}

  # --- 0. Convert to raw bytes ---
  logger.debug(f"Received audio blob of type: {type(audio_blob)}")
  if isinstance(audio_blob, str):
    try:
      audio_bytes = base64.b64decode(audio_blob, validate=True)
    except Exception as e:
      logger.error("Invalid Base-64 audio string received.", exc_info=True)
      return {"error": "Invalid Base-64 audio string."}
  elif hasattr(audio_blob, "get_bytes"):
    audio_bytes = audio_blob.get_bytes()
  elif isinstance(audio_blob, (bytes, bytearray)):
    audio_bytes = bytes(audio_blob)
  else:
    logger.error(f"Unsupported audio blob type: {type(audio_blob)}")
    return {"error": "Unsupported audio blob type."}
  logger.debug(f"Successfully converted audio blob to {len(audio_bytes)} bytes.")

  # --- 1. Load with pydub ---
  def try_load(fmt=None):
    try:
      return AudioSegment.from_file(io.BytesIO(audio_bytes), format=fmt)
    except Exception:
      return None

  audio = None
  header = audio_bytes[:16]
  detected_format = "unknown"
  if header.startswith(WEBM_MAGIC):
    audio = try_load("webm")
    detected_format = "webm"
  elif header.startswith(b"OggS"):
    audio = try_load("ogg")
    detected_format = "ogg"
  elif header.startswith(b"fLaC"):
    audio = try_load("flac")
    detected_format = "flac"
  elif header.startswith(b"RIFF"):
    audio = try_load("wav")
    detected_format = "wav"
  elif header[:3] in (b"\xff\xf1", b"\xff\xf9") or header.startswith(b"ID3"):
    audio = try_load("mp3")
    detected_format = "mp3"
  elif header[4:8] in (b"M4A ", b"MP4 ", b"isom", b"iso2", b"mp42"):
    audio = try_load("mp4")
    detected_format = "mp4/m4a"
  elif header.startswith(b"caff"):
    audio = try_load("caf")
    detected_format = "caf"

  if audio is None:
    logger.warning("Could not detect audio format from header, attempting brute force.")
    for fmt in ["webm", "ogg", "flac", "wav", "mp3", "m4a", "caf", "mp4", "aac"]:
      audio = try_load(fmt)
      if audio:
        detected_format = f"brute-force {fmt}"
        break

  logger.info(f"Detected audio format: {detected_format}")

  if audio is None:
    logger.error("Unsupported audio format. Could not read the file.")
    return {"error": "Unsupported audio format. The file could not be read."}

  # --- 2. Sanity checks and Normalization ---
  logger.debug(f"Audio length: {len(audio)}ms, dBFS: {audio.dBFS:.2f}")
  if len(audio) < 150:
    pad = AudioSegment.silent(duration=300)
    audio = pad + audio + pad
    logger.debug(f"Padded short audio to {len(audio)}ms.")

  if audio.dBFS == float("-inf") or audio.dBFS < -80:
    logger.warning("Audio appears to be silent.")
    return {"error": "The audio is silent. Please record again."}

  audio = audio.set_channels(1).set_frame_rate(16000)
  logger.debug("Normalized audio to mono channel, 16000Hz frame rate.")

  # --- 3. Transcription (with chunking) ---
  if len(audio) <= MAX_SINGLE_CHUNK_MS:
    logger.info("Audio is short enough, transcribing in a single chunk.")
    transcription = whisper_call(audio)
  else:
    logger.info(f"Audio is too long ({len(audio)}ms). Splitting into chunks.")
    parts, p = [], 0
    chunk_count = 0
    while p < len(audio):
      chunk_count += 1
      q = min(p + MAX_SINGLE_CHUNK_MS + OVERLAP_MS, len(audio))
      logger.debug(f"Transcribing chunk {chunk_count}: {p}ms to {q}ms.")
      parts.append(whisper_call(audio[p:q]).strip())
      p += MAX_SINGLE_CHUNK_MS
    transcription = " ".join(parts)
    logger.info(f"Finished transcribing {chunk_count} chunks.")

  logger.info(f"Transcription complete. Result length: {len(transcription)} chars.")
  logger.debug(f"Final Transcription (first 100 chars): {transcription[:100]}")
  return transcription