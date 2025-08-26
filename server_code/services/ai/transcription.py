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


