import anvil.secrets
import base64
import io
import json
import os
import re
import time
from datetime import datetime

import anvil.tables as tables
import anvil.tables.query as q
import anvil.users
import anvil.server
import markdown
import PyPDF2
from anvil.tables import app_tables
from openai import OpenAI
from pydub import AudioSegment

########################################### SETTINGS ###################################################

# Initialize OpenAI client with hardcoded key (for testing only)
try:
  openai_key = anvil.secrets.get_secret("OPENAI_API_KEY")
  client = OpenAI(api_key=openai_key)
  print("OpenAI API initialized successfully")
except Exception as e:
  print(f"Error initializing OpenAI API: {str(e)}")
  raise RuntimeError("Failed to initialize OpenAI API")

# Set default parameters
DEFAULT_MODEL = "chatgpt-4o-latest"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 1500

@anvil.server.callable
def check_ffmpeg_dependency():
  try:
    from pydub import AudioSegment
    # Cette ligne simple va échouer si ffmpeg n'est pas trouvé
    AudioSegment.silent(duration=10) 
    return "SUCCESS: FFmpeg seems to be installed and accessible by pydub."
  except Exception as e:
    return f"ERROR: FFmpeg dependency check failed. Details: {str(e)}"

########################################### AUDIO SECTION ###################################################


RETRY_LIMIT         = 3
MAX_SINGLE_CHUNK_MS = 60_000
OVERLAP_MS          = 10_000
WEBM_MAGIC          = b'\x1A\x45\xDF\xA3'

# ------------------------------------------------------------------
# Public entry point (same name & args as before)
# ------------------------------------------------------------------
# ───────────────────────────────────────────────────────────────────
# ENTRY POINT (same name & args)  → returns a BACKGROUND-TASK ID
# ───────────────────────────────────────────────────────────────────
@anvil.server.callable
def process_audio_whisper(audio_blob):
  # just return the Task object
  return anvil.server.launch_background_task(
    'bg_process_audio_whisper', audio_blob
  )

@anvil.server.callable
def EN_process_audio_whisper(audio_blob):
  # just return the Task object
  return anvil.server.launch_background_task(
    'EN_bg_process_audio_whisper', audio_blob
  )

@anvil.server.background_task
def bg_process_audio_whisper(audio_blob):
  """
  Normalise incoming audio (bytes, base-64 string or BlobMedia),
  down-sample to 16 kHz mono and feed it to Whisper-1.
  Returns the transcription text or raises an Exception.
  """
  # ── helpers ──────────────────────────────────────────────────────────
  def export_as_wav(seg):
    buf = io.BytesIO()
    seg.export(buf, format="wav", parameters=["-ar", "16000", "-ac", "1"])
    buf.seek(0)
    buf.name = "audio.wav"
    return buf

  def whisper_call(seg):
    for n in range(RETRY_LIMIT):
      try:
        return client.audio.transcriptions.create(
          model="whisper-1",
          file=export_as_wav(seg),
          language="fr"
        ).text
      except Exception as e:
        if n < RETRY_LIMIT - 1:
          time.sleep(2 ** n)  # 1 s, 2 s, 4 s …
          print(f"[WARN] Whisper retry {n+1}/{RETRY_LIMIT}: {e}")
        else:
          raise Exception("Whisper transcription failed after several retries")

  # ── 0. convert to raw bytes ─────────────────────────────────────────
  if isinstance(audio_blob, str):
    try:
      audio_bytes = base64.b64decode(audio_blob, validate=True)
    except Exception:
      raise Exception("Invalid Base-64 audio string")
  elif hasattr(audio_blob, "get_bytes"):            # BlobMedia / StreamingMedia
    audio_bytes = audio_blob.get_bytes()
  elif isinstance(audio_blob, (bytes, bytearray)):
    audio_bytes = bytes(audio_blob)
  else:
    raise Exception("Unsupported audio_blob type")

  header = audio_bytes[:16]

  # ── 1. load with pydub ──────────────────────────────────────────────
  def try_load(fmt=None):
    try:
      return AudioSegment.from_file(io.BytesIO(audio_bytes), format=fmt)
    except Exception:
      return None

  audio = None
  if header.startswith(WEBM_MAGIC):
    audio = try_load("webm")
  elif header.startswith(b"OggS"):
    audio = try_load("ogg")
  elif header.startswith(b"fLaC"):
    audio = try_load("flac")
  elif header.startswith(b"RIFF"):
    audio = try_load("wav")
  elif header[:3] in (b"\xFF\xF1", b"\xFF\xF9") or header.startswith(b"ID3"):
    audio = try_load("mp3")
  elif header[4:8] in (b"M4A ", b"MP4 ", b"isom", b"iso2", b"mp42"):
    audio = try_load("mp4")
  elif header.startswith(b"caff"):
    audio = try_load("caf")

  if audio is None:                                       # brute force
    for fmt in ["webm", "ogg", "flac", "wav", "mp3", "m4a", "caf", "mp4", "aac"]:
      audio = try_load(fmt)
      if audio:
        break

  if audio is None:
    raise Exception("Unrecognised audio format")

  # ── 2. sanity checks ────────────────────────────────────────────────
  if len(audio) < 150:                                    # < 0.15 s
    pad = AudioSegment.silent(300)
    audio = pad + audio + pad

  if audio.dBFS == float("-inf") or audio.dBFS < -80:
    raise Exception("Audio is silent – please record again")

    if audio.frame_rate > 16000:
      audio = audio.set_frame_rate(16000)

  audio = audio.set_channels(1)

  # ── 3. transcription ───────────────────────────────────────────────
  if len(audio) <= MAX_SINGLE_CHUNK_MS:
    transcription = whisper_call(audio)
  else:
    parts, p = [], 0
    while p < len(audio):
      q = min(p + MAX_SINGLE_CHUNK_MS + OVERLAP_MS, len(audio))
      parts.append(whisper_call(audio[p:q]).strip())
      p += MAX_SINGLE_CHUNK_MS
      transcription = " ".join(parts)

  print("[DEBUG] Transcription OK")
  return transcription



################ EN


@anvil.server.background_task
def EN_bg_process_audio_whisper(audio_blob):
  """
  Normalise incoming audio (bytes, base-64 string or BlobMedia),
  down-sample to 16 kHz mono and feed it to Whisper-1.
  Returns the transcription text or raises an Exception.
  """
  # ── helpers ──────────────────────────────────────────────────────────
  def export_as_wav(seg):
    buf = io.BytesIO()
    seg.export(buf, format="wav", parameters=["-ar", "16000", "-ac", "1"])
    buf.seek(0)
    buf.name = "audio.wav"
    return buf

  def whisper_call(seg):
    for n in range(RETRY_LIMIT):
      try:
        return client.audio.transcriptions.create(
          model="whisper-1",
          file=export_as_wav(seg),
          language="en"
        ).text
      except Exception as e:
        if n < RETRY_LIMIT - 1:
          time.sleep(2 ** n)  # 1 s, 2 s, 4 s …
          print(f"[WARN] Whisper retry {n+1}/{RETRY_LIMIT}: {e}")
        else:
          raise Exception("Whisper transcription failed after several retries")

  # ── 0. convert to raw bytes ─────────────────────────────────────────
  if isinstance(audio_blob, str):
    try:
      audio_bytes = base64.b64decode(audio_blob, validate=True)
    except Exception:
      raise Exception("Invalid Base-64 audio string")
  elif hasattr(audio_blob, "get_bytes"):            # BlobMedia / StreamingMedia
    audio_bytes = audio_blob.get_bytes()
  elif isinstance(audio_blob, (bytes, bytearray)):
    audio_bytes = bytes(audio_blob)
  else:
    raise Exception("Unsupported audio_blob type")

  header = audio_bytes[:16]

  # ── 1. load with pydub ──────────────────────────────────────────────
  def try_load(fmt=None):
    try:
      return AudioSegment.from_file(io.BytesIO(audio_bytes), format=fmt)
    except Exception:
      return None

  audio = None
  if header.startswith(WEBM_MAGIC):
    audio = try_load("webm")
  elif header.startswith(b"OggS"):
    audio = try_load("ogg")
  elif header.startswith(b"fLaC"):
    audio = try_load("flac")
  elif header.startswith(b"RIFF"):
    audio = try_load("wav")
  elif header[:3] in (b"\xFF\xF1", b"\xFF\xF9") or header.startswith(b"ID3"):
    audio = try_load("mp3")
  elif header[4:8] in (b"M4A ", b"MP4 ", b"isom", b"iso2", b"mp42"):
    audio = try_load("mp4")
  elif header.startswith(b"caff"):
    audio = try_load("caf")

    if audio is None:                                       # brute force
      for fmt in ["webm", "ogg", "flac", "wav", "mp3", "m4a", "caf", "mp4", "aac"]:
        audio = try_load(fmt)
        if audio:
          break

  if audio is None:
    raise Exception("Unrecognised audio format")

    # ── 2. sanity checks ────────────────────────────────────────────────
    if len(audio) < 150:                                    # < 0.15 s
      pad = AudioSegment.silent(300)
      audio = pad + audio + pad

  if audio.dBFS == float("-inf") or audio.dBFS < -80:
    raise Exception("Audio is silent – please record again")

    if audio.frame_rate > 16000:
      audio = audio.set_frame_rate(16000)

    audio = audio.set_channels(1)

  # ── 3. transcription ───────────────────────────────────────────────
  if len(audio) <= MAX_SINGLE_CHUNK_MS:
    transcription = whisper_call(audio)
  else:
    parts, p = [], 0
    while p < len(audio):
      q = min(p + MAX_SINGLE_CHUNK_MS + OVERLAP_MS, len(audio))
      parts.append(whisper_call(audio[p:q]).strip())
      p += MAX_SINGLE_CHUNK_MS
      transcription = " ".join(parts)

  print("[DEBUG] Transcription OK")
  return transcription






########################################### REPORT GENERATION SECTION ###################################################
@anvil.server.callable
def generate_report(prompt, transcription):
  """
  Generate report using GPT-4.
  Includes retry mechanism with exponential backoff for API failures.
  """
  def _gpt4_generate(prompt_text, transcription_text):
    """Call GPT-4 API with retries and back-off."""
    for attempt in range(RETRY_LIMIT):
      try:
        messages = [
            {"role": "system", "content": prompt_text},
            {"role": "user", "content": transcription_text}
        ]

        response = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=messages,
            temperature=DEFAULT_TEMPERATURE,
            max_tokens=DEFAULT_MAX_TOKENS
        )

        return response.choices[0].message.content
      except Exception as e:
        wait = 2 ** attempt
        print(f"[WARN] GPT-4 attempt {attempt+1}/{RETRY_LIMIT} failed: {e}. "
              f"Retrying in {wait}s...")
        if attempt < RETRY_LIMIT - 1:
          time.sleep(wait)
    # If we get here, all retries failed
    raise Exception("GPT-4 report generation failed after multiple attempts")

  try:
    # Call the GPT-4 API with retry mechanism
    result = _gpt4_generate(prompt, transcription)
    print("[DEBUG] Report generation done")
    return result

  except Exception as e:
    print(f"[ERROR] generate_report: {e}")
    raise Exception(f"Error generating report: {e}")


@anvil.server.callable
def generate_report_leg(prompt, transcription):
  """Generate report using GPT-4"""
  try:
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": transcription}
    ]

    response = client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=messages,
        temperature=DEFAULT_TEMPERATURE,
        max_tokens=DEFAULT_MAX_TOKENS
    )

    return response.choices[0].message.content
  except Exception as e:
    print(f"GPT-4 API error: {str(e)}")
    raise Exception("Error generating report")



########################################### FORMAT SECTION ###################################################
# 1. Probabilistic

@anvil.server.callable
def format_report(transcription):
  """Generate report using GPT-4"""

  prompt = """
Rôle :
Tu es un convertisseur de rapports vétérinaires en HTML5.

Tâche :
Transformer un rapport d'entrée (TXT, Markdown, texte enrichi ou HTML) en un document HTML5 valide. Le document doit :

  Commencer par <!DOCTYPE html>.
  Contenir une balise <html lang="..."> avec la langue appropriée.
  Avoir une section <head> définissant <meta charset="UTF-8"> et intégrant un CSS minimal pour assurer une présentation cohérente.
  Structurer le contenu dans la balise <body> en utilisant des listes imbriquées (<ul>) pour organiser les sections et sous-sections.
  Afficher la totalité du rapport d'origine sans rien omettre.

examples d'output:

exemple output 1:
 <!DOCTYPE html>
  <html lang="fr">
  <head>
      <meta charset="UTF-8">
      <style>
          body {
              font-family: Arial, sans-serif;
              line-height: 1.6;
              margin: 20px;
          }
          ul {
              list-style-type: disc;
              margin-left: 20px;
          }
          ul ul {
              list-style-type: circle;
          }
          ul ul ul {
              list-style-type: square;
          }
      </style>
  </head>
  <body>
      <ul>
          <li><strong>Cheval</strong> : Max</li>
          <li><strong>Propriétaire</strong> : Mme Lambert</li>
          <li><strong>Date de l'examen</strong> : 10 mars 2025</li>
          <li><strong>Histoire</strong> : Présenté pour une toux chronique non productive depuis 2 semaines.</li>
          <li><strong>Examen</strong> :
              <ul>
                  <li><strong>Examen clinique</strong> :
                      <ul>
                          <li>Légère tachypnée.</li>
                          <li>Auscultation : Bruits bronchiques accentués dans les lobes crâniens.</li>
                      </ul>
                  </li>
              </ul>
          </li>
          <li><strong>Tests diagnostiques</strong> :
              <ul>
                  <li><strong>Radiographie thoracique</strong> : Opacification modérée des lobes crâniens.</li>
                  <li><strong>Analyse sanguine</strong> : Pas d'anomalies majeures détectées.</li>
              </ul>
          </li>
          <li><strong>Traitement</strong> :
              <ul>
                  <li>Prescrire un antibiotique (doxycycline) pour 10 jours.</li>
                  <li>Limiter les activités physiques pendant la durée du traitement.</li>
                  <li>Nébulisation avec une solution saline 2 fois par jour.</li>
              </ul>
          </li>
          <li><strong>Recommandations</strong> :
              <ul>
                  <li>Revoir si la toux persiste ou si de nouveaux symptômes apparaissent.</li>
                  <li>Contrôle dans 2 semaines pour évaluer la réponse au traitement.</li>
              </ul>
          </li>
          <li><strong>Sincères salutations distinguées.</strong></li>
      </ul>
  </body>
  </html>

example output 2:
  <!DOCTYPE html>
  <html lang="fr">
  <head>
      <meta charset="UTF-8">
      <style>
          body {
              font-family: Arial, sans-serif;
              line-height: 1.6;
              margin: 20px;
          }
          ul {
              list-style-type: disc;
              margin-left: 20px;
          }
          ul ul {
              list-style-type: circle;
          }
          ul ul ul {
              list-style-type: square;
          }
      </style>
  </head>
  <body>
      <ul>
          <li><strong>Cheval</strong> : Bella</li>
          <li><strong>Propriétaire</strong> : M. Dupont</li>
          <li><strong>Date de l'examen</strong> : 15 janvier 2025</li>
          <li><strong>Histoire</strong> : Vomissements intermittents depuis 3 jours. Aucune diarrhée signalée.</li>
          <li><strong>Examen</strong> :
              <ul>
                  <li><strong>Examen clinique</strong> :
                      <ul>
                          <li>Déshydratation légère (5%).</li>
                          <li>Douleur abdominale modérée à la palpation.</li>
                      </ul>
                  </li>
              </ul>
          </li>
          <li><strong>Tests diagnostiques</strong> :
              <ul>
                  <li><strong>Analyse sanguine</strong> : Léger déséquilibre électrolytique.</li>
                  <li><strong>Radiographie abdominale</strong> : Présence de gaz dans les intestins, absence de corps étranger visible.</li>
              </ul>
          </li>
          <li><strong>Traitement</strong> :
              <ul>
                  <li>Réhydratation par voie sous-cutanée (500 ml Ringer lactate).</li>
                  <li>Alimentation à base de régime gastro-intestinal faible en graisses pour 5 jours.</li>
                  <li>Prescription de maropitant (Cerenia) pour les vomissements.</li>
              </ul>
          </li>
          <li><strong>Recommandations</strong> :
              <ul>
                  <li>Surveiller les signes de douleurs persistantes ou de vomissements.</li>
                  <li>Revenir pour un contrôle si aucun progrès en 48 heures.</li>
              </ul>
          </li>
          <li><strong>Sincères salutations distinguées.</strong></li>
      </ul>
  </body>
  </html>

exemple output 3:
  <!DOCTYPE html>
  <html lang="fr">
  <head>
      <meta charset="UTF-8">
      <style>
          body {
              font-family: Arial, sans-serif;
              line-height: 1.6;
              margin: 20px;
          }
          ul {
              list-style-type: disc;
              margin-left: 20px;
          }
          ul ul {
              list-style-type: circle;
          }
          ul ul ul {
              list-style-type: square;
          }
      </style>
  </head>
  <body>
      <ul>
          <li><strong>Cheval</strong> : Fernando</li>
          <li><strong>Propriétaire</strong> : Non spécifié</li>
          <li><strong>Date de l'examen</strong> : Non spécifiée</li>
          <li><strong>Histoire</strong> : Présenté pour une boiterie de l'antérieur droit (AD).</li>
          <li><strong>Examen</strong> :
              <ul>
                  <li><strong>Examen statique</strong> :
                      <ul>
                          <li>Épaississement de la gaine du tendon du suspenseur de l'antérieur droit (AD).</li>
                      </ul>
                  </li>
                  <li><strong>Examen dynamique</strong> :
                      <ul>
                          <li>Boiterie de grade 1/5 sur le cercle à main droite sur sol dur.</li>
                          <li>Aucune boiterie à main gauche.</li>
                          <li>Boiterie de grade 2/5 sur le cercle sur sol souple.</li>
                      </ul>
                  </li>
              </ul>
          </li>
          <li><strong>Procédures diagnostiques spécifiques</strong> :
              <ul>
                  <li><strong>Examen échographique</strong> : Confirmation d'un épaississement de la gaine du tendon du suspenseur.</li>
              </ul>
          </li>
          <li><strong>Traitement</strong> :
              <ul>
                  <li>Injection de la gaine du tendon avec du PRP (plasma riche en plaquettes).</li>
                  <li>Marcher au pas en main pendant 2 jours.</li>
                  <li>Marcher au pas monté pendant 15 jours autant que possible.</li>
                  <li>Surveiller la température.</li>
                  <li>Informer le vétérinaire des progrès.</li>
              </ul>
          </li>
          <li><strong>Sincères salutations distinguées.</strong></li>
      </ul>
  </body>
  </html>

exemple output 1:
 <!DOCTYPE html>
  <html lang="fr">
  <head>
      <meta charset="UTF-8">
      <style>
          body {
              font-family: Arial, sans-serif;
              line-height: 1.6;
              margin: 20px;
          }
          ul {
              list-style-type: disc;
              margin-left: 20px;
          }
          ul ul {
              list-style-type: circle;
          }
          ul ul ul {
              list-style-type: square;
          }
      </style>
  </head>
  <body>
      <ul>
          <li><strong>Cheval</strong> : Max</li>
          <li><strong>Propriétaire</strong> : Mme Lambert</li>
          <li><strong>Date de l'examen</strong> : 10 mars 2025</li>
          <li><strong>Histoire</strong> : Présenté pour une toux chronique non productive depuis 2 semaines.</li>
          <li><strong>Examen</strong> :
              <ul>
                  <li><strong>Examen clinique</strong> :
                      <ul>
                          <li>Légère tachypnée.</li>
                          <li>Auscultation : Bruits bronchiques accentués dans les lobes crâniens.</li>
                      </ul>
                  </li>
              </ul>
          </li>
          <li><strong>Tests diagnostiques</strong> :
              <ul>
                  <li><strong>Radiographie thoracique</strong> : Opacification modérée des lobes crâniens.</li>
                  <li><strong>Analyse sanguine</strong> : Pas d'anomalies majeures détectées.</li>
              </ul>
          </li>
          <li><strong>Traitement</strong> :
              <ul>
                  <li>Prescrire un antibiotique (doxycycline) pour 10 jours.</li>
                  <li>Limiter les activités physiques pendant la durée du traitement.</li>
                  <li>Nébulisation avec une solution saline 2 fois par jour.</li>
              </ul>
          </li>
          <li><strong>Recommandations</strong> :
              <ul>
                  <li>Revoir si la toux persiste ou si de nouveaux symptômes apparaissent.</li>
                  <li>Contrôle dans 2 semaines pour évaluer la réponse au traitement.</li>
              </ul>
          </li>
          <li><strong>Sincères salutations distinguées.</strong></li>
      </ul>
  </body>
  </html>

example output 2:
  <!DOCTYPE html>
  <html lang="fr">
  <head>
      <meta charset="UTF-8">
      <style>
          body {
              font-family: Arial, sans-serif;
              line-height: 1.6;
              margin: 20px;
          }
          ul {
              list-style-type: disc;
              margin-left: 20px;
          }
          ul ul {
              list-style-type: circle;
          }
          ul ul ul {
              list-style-type: square;
          }
      </style>
  </head>
  <body>
      <ul>
          <li><strong>Cheval</strong> : Bella</li>
          <li><strong>Propriétaire</strong> : M. Dupont</li>
          <li><strong>Date de l'examen</strong> : 15 janvier 2025</li>
          <li><strong>Histoire</strong> : Vomissements intermittents depuis 3 jours. Aucune diarrhée signalée.</li>
          <li><strong>Examen</strong> :
              <ul>
                  <li><strong>Examen clinique</strong> :
                      <ul>
                          <li>Déshydratation légère (5%).</li>
                          <li>Douleur abdominale modérée à la palpation.</li>
                      </ul>
                  </li>
              </ul>
          </li>
          <li><strong>Tests diagnostiques</strong> :
              <ul>
                  <li><strong>Analyse sanguine</strong> : Léger déséquilibre électrolytique.</li>
                  <li><strong>Radiographie abdominale</strong> : Présence de gaz dans les intestins, absence de corps étranger visible.</li>
              </ul>
          </li>
          <li><strong>Traitement</strong> :
              <ul>
                  <li>Réhydratation par voie sous-cutanée (500 ml Ringer lactate).</li>
                  <li>Alimentation à base de régime gastro-intestinal faible en graisses pour 5 jours.</li>
                  <li>Prescription de maropitant (Cerenia) pour les vomissements.</li>
              </ul>
          </li>
          <li><strong>Recommandations</strong> :
              <ul>
                  <li>Surveiller les signes de douleurs persistantes ou de vomissements.</li>
                  <li>Revenir pour un contrôle si aucun progrès en 48 heures.</li>
              </ul>
          </li>
          <li><strong>Sincères salutations distinguées.</strong></li>
      </ul>
  </body>
  </html>

Important :
Ne fais que du formatage sans modifier ou interpréter le contenu. Utilise toujours ce même formatage. Préserve toujours l'intégralité du contenu.
Ne commance jamais ta réponse par ```html et ne finis jamais ta réponse par ```.
  """
  try:
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": transcription}
    ]

    response = client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=messages,
        temperature=DEFAULT_TEMPERATURE,
        max_tokens=DEFAULT_MAX_TOKENS
    )
    print(response.choices[0].message.content)
    return response.choices[0].message.content
  except Exception as e:
    print(f"GPT-4 API error: {str(e)}")
    raise Exception("Error generating report")




@anvil.server.callable
def EN_format_report(transcription):
  """Generate report using GPT-4"""

  prompt = """
Role:
You are a veterinary report converter to HTML5.

Task:
Transform an input report (TXT, Markdown, rich text, or HTML) into a valid HTML5 document. The document must:
- Start with <!DOCTYPE html>
- Contain an <html lang="..."> tag with the appropriate language
- Have a <head> section defining <meta charset="UTF-8"> and incorporating minimal CSS to ensure consistent presentation
- Structure the content in the <body> tag using nested lists (<ul>) to organize sections and subsections
- Display the entire original report without omitting anything

Output Example 1:
<!DOCTYPE html>
<html lang="en">
  <head>
      <meta charset="UTF-8">
      <style>
          body {
              font-family: Arial, sans-serif;
              line-height: 1.6;
              margin: 20px;
          }
          ul {
              list-style-type: disc;
              margin-left: 20px;
          }
          ul ul {
              list-style-type: circle;
          }
          ul ul ul {
              list-style-type: square;
          }
      </style>
  </head>
  <body>
      <ul>
          <li><strong>Horse</strong>: Max</li>
          <li><strong>Owner</strong>: Mrs. Lambert</li>
          <li><strong>Examination Date</strong>: March 10, 2025</li>
          <li><strong>History</strong>: Presented for chronic non-productive cough for 2 weeks.</li>
          <li><strong>Examination</strong>:
              <ul>
                  <li><strong>Clinical Examination</strong>:
                      <ul>
                          <li>Mild tachypnea.</li>
                          <li>Auscultation: Accentuated bronchial sounds in cranial lobes.</li>
                      </ul>
                  </li>
              </ul>
          </li>
          <li><strong>Diagnostic Tests</strong>:
              <ul>
                  <li><strong>Thoracic Radiography</strong>: Moderate opacification of cranial lobes.</li>
                  <li><strong>Blood Analysis</strong>: No major abnormalities detected.</li>
              </ul>
          </li>
          <li><strong>Treatment</strong>:
              <ul>
                  <li>Prescribe antibiotic (doxycycline) for 10 days.</li>
                  <li>Limit physical activities during treatment.</li>
                  <li>Nebulization with saline solution twice daily.</li>
              </ul>
          </li>
          <li><strong>Recommendations</strong>:
              <ul>
                  <li>Review if cough persists or if new symptoms appear.</li>
                  <li>Follow-up in 2 weeks to evaluate response to treatment.</li>
              </ul>
          </li>
          <li><strong>Best regards.</strong></li>
      </ul>
  </body>
</html>

Output Example 2:
<!DOCTYPE html>
<html lang="en">
  <head>
      <meta charset="UTF-8">
      <style>
          body {
              font-family: Arial, sans-serif;
              line-height: 1.6;
              margin: 20px;
          }
          ul {
              list-style-type: disc;
              margin-left: 20px;
          }
          ul ul {
              list-style-type: circle;
          }
          ul ul ul {
              list-style-type: square;
          }
      </style>
  </head>
  <body>
      <ul>
          <li><strong>Horse</strong>: Bella</li>
          <li><strong>Owner</strong>: Mr. Dupont</li>
          <li><strong>Examination Date</strong>: January 15, 2025</li>
          <li><strong>History</strong>: Intermittent vomiting for 3 days. No diarrhea reported.</li>
          <li><strong>Examination</strong>:
              <ul>
                  <li><strong>Clinical Examination</strong>:
                      <ul>
                          <li>Mild dehydration (5%).</li>
                          <li>Moderate abdominal pain on palpation.</li>
                      </ul>
                  </li>
              </ul>
          </li>
          <li><strong>Diagnostic Tests</strong>:
              <ul>
                  <li><strong>Blood Analysis</strong>: Slight electrolyte imbalance.</li>
                  <li><strong>Abdominal Radiography</strong>: Gas present in intestines, no visible foreign body.</li>
              </ul>
          </li>
          <li><strong>Treatment</strong>:
              <ul>
                  <li>Subcutaneous rehydration (500 ml Lactated Ringer's).</li>
                  <li>Low-fat gastrointestinal diet for 5 days.</li>
                  <li>Prescription of maropitant (Cerenia) for vomiting.</li>
              </ul>
          </li>
          <li><strong>Recommendations</strong>:
              <ul>
                  <li>Monitor for signs of persistent pain or vomiting.</li>
                  <li>Return for check-up if no progress in 48 hours.</li>
              </ul>
          </li>
          <li><strong>Best regards.</strong></li>
      </ul>
  </body>
</html>

Output Example 3:
<!DOCTYPE html>
<html lang="en">
  <head>
      <meta charset="UTF-8">
      <style>
          body {
              font-family: Arial, sans-serif;
              line-height: 1.6;
              margin: 20px;
          }
          ul {
              list-style-type: disc;
              margin-left: 20px;
          }
          ul ul {
              list-style-type: circle;
          }
          ul ul ul {
              list-style-type: square;
          }
      </style>
  </head>
  <body>
      <ul>
          <li><strong>Horse</strong>: Fernando</li>
          <li><strong>Owner</strong>: Not specified</li>
          <li><strong>Examination Date</strong>: Not specified</li>
          <li><strong>History</strong>: Presented for lameness in right forelimb (RF).</li>
          <li><strong>Examination</strong>:
              <ul>
                  <li><strong>Static Examination</strong>:
                      <ul>
                          <li>Thickening of the suspensory ligament sheath of the right forelimb (RF).</li>
                      </ul>
                  </li>
                  <li><strong>Dynamic Examination</strong>:
                      <ul>
                          <li>Grade 1/5 lameness on the right circle on hard ground.</li>
                          <li>No lameness on left circle.</li>
                          <li>Grade 2/5 lameness on circle on soft ground.</li>
                      </ul>
                  </li>
              </ul>
          </li>
          <li><strong>Specific Diagnostic Procedures</strong>:
              <ul>
                  <li><strong>Ultrasound Examination</strong>: Confirmation of suspensory ligament sheath thickening.</li>
              </ul>
          </li>
          <li><strong>Treatment</strong>:
              <ul>
                  <li>Injection of the tendon sheath with PRP (platelet-rich plasma).</li>
                  <li>Hand walk for 2 days.</li>
                  <li>Ridden walk for 15 days as much as possible.</li>
                  <li>Monitor temperature.</li>
                  <li>Inform veterinarian of progress.</li>
              </ul>
          </li>
          <li><strong>Best regards.</strong></li>
      </ul>
  </body>
</html>

Important:
- Only format without modifying or interpreting the content
- Always use this same formatting
- Always preserve the entirety of the content
- Never start your response with ```html and never end your response with ```
  """
  try:
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": transcription}
    ]

    response = client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=messages,
        temperature=DEFAULT_TEMPERATURE,
        max_tokens=DEFAULT_MAX_TOKENS
    )
    print(response.choices[0].message.content)
    return response.choices[0].message.content
  except Exception as e:
    print(f"GPT-4 API error: {str(e)}")
    raise Exception("Error generating report")







# 2. deterministic

def strip_leading_bullet(line):
  """
  Removes a leading bullet character sequence (e.g. "- ", "* ", "• ")
  from the line if present.
  """
  stripped_line = line.strip()
  for bullet_char in ("- ", "* ", "• "):
    if stripped_line.startswith(bullet_char):
      stripped_line = stripped_line[len(bullet_char):]
      break
  return stripped_line

def detect_heading(line):
  """
  Determines if a line is a 'heading line.'
  This code handles both simple cases (e.g. "Examen clinique :")
  and bold-wrapped cases (e.g. "**Examen clinique :**").

  Steps:
    1) Trim whitespace.
    2) Strip leading bullet if present.
    3) If the line is wrapped in '** ... **', remove the wrapping so we can see
       if it ends with a colon.
    4) Check if the text ends with ':'.
  Returns:
    (is_heading, cleaned_text)
    - is_heading: boolean
    - cleaned_text: the heading text minus bold markers (and trailing colon if needed)
  """
  # First, strip leading bullet and spaces
  stripped = strip_leading_bullet(line.strip())

  # If line is wrapped in "**...**", remove those wrapping asterisks for checking
  if stripped.startswith("**") and stripped.endswith("**") and len(stripped) > 4:
    # remove outer "**"
    no_bold = stripped[2:-2].strip()
  else:
    no_bold = stripped

  # Now check if the text ends with ":"
  # We do a quick test: if there's a colon near the end ignoring possible final bold "**"
  # Example: "**Examen clinique :**" => after removing wrapping "**", we get "Examen clinique :"
  # ends with ":" => heading
  if no_bold.endswith(":"):
    return True, stripped
  return False, stripped

def markdown_to_inline(text):
  """
  Converts a single line of Markdown to 'inline' HTML.
  Strips the <p> tags if Markdown wrapped them with <p>...</p>.
  """
  converted = markdown.markdown(text, extensions=[], output_format="html").strip()
  if converted.startswith("<p>") and converted.endswith("</p>"):
    converted = converted[3:-4]
  return converted

def convert_markdown_custom(report, lang="fr"):
  """
  Convertit un rapport au format Markdown en une structure HTML organisée par sections.

  Règles :
    - Une ligne considérée comme un 'heading' (ex: "Examen clinique :") sera mise en <p> (gras).
      *On insère un <br> avant le heading si ce n'est pas le premier.*
    - Les lignes qui ne sont pas des headings sont considérées comme des items <li> dans la section courante.
    - On conserve la mise en forme inline (gras, italique, etc.) en utilisant markdown_to_inline().
    - Au final, on renvoie la totalité du document au format HTML (sections).
  """
  lines = report.splitlines()
  sections = []
  current_header = None
  current_items = []

  for line in lines:
    # Ignore empty lines
    if not line.strip():
      continue

    # Détecter si c'est un heading
    is_heading, cleaned_text = detect_heading(line)

    if is_heading:
      # On sauvegarde la section précédente si elle existe
      if current_header is not None or current_items:
        sections.append((current_header, current_items))

      # Définir un nouveau heading
      current_header = markdown_to_inline(cleaned_text)
      current_items = []
    else:
      # Sinon, c'est un item
      current_items.append(markdown_to_inline(strip_leading_bullet(line.strip())))

  # Ajouter la dernière section
  if current_header is not None or current_items:
    sections.append((current_header, current_items))

  # Construire le HTML
  html_parts = []

  for idx, (header, items) in enumerate(sections):
    # Avant chaque heading (sauf le premier), on met une ligne vide
    if header:
      if idx > 0:
        html_parts.append("<br>")
      # Mettre le heading dans un <p> (fortement stylé dans CSS)
      html_parts.append(f"<p>{header}</p>")

      # Les items du heading
      if items:
        html_parts.append("<ul>")
        for item in items:
          html_parts.append(f"  <li>{item}</li>")
        html_parts.append("</ul>")
    else:
      # S'il n'y a pas de heading, on liste simplement
      if items:
        html_parts.append("<ul>")
        for item in items:
          html_parts.append(f"  <li>{item}</li>")
        html_parts.append("</ul>")

  return "\n".join(html_parts)

@anvil.server.callable
def format_report_deterministic(transcription):
  """
  Transforme un rapport vétérinaire au format Markdown en un document HTML5 valide.

  Le document généré :
    - Commence par <!DOCTYPE html>.
    - Utilise <html lang="fr">, une section <head> avec <meta charset="UTF-8"> et un CSS minimal intégré.
    - Le contenu final est ajouté dans <body>.

    - Les headings (lignes terminées par ':' ou du genre "**Examen clinique :**")
      sont affichés dans un paragraphe (<p>) en gras (géré via CSS).
    - Les lignes suivantes sont mises dans des <li> à puce, avec indentation.
    - On insère une ligne vide (<br>) avant chaque heading (sauf le premier).
  """
  try:
    html_body = convert_markdown_custom(transcription, lang="fr")
    html_template = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<style>
    body {{
        font-family: Arial, sans-serif;
        line-height: 1.6;
        margin: 20px;
    }}
    p {{
        font-weight: bold;
        margin: 0.8em 0 0.3em; /* plus d'espace avant pour isoler le titre */
    }}
    ul {{
        list-style-type: disc;
        margin-left: 40px; /* indentation plus prononcée */
        margin-bottom: 1.2em; /* espace sous la liste */
    }}
    ul ul {{
        list-style-type: circle;
        margin-left: 40px;
    }}
    ul ul ul {{
        list-style-type: square;
        margin-left: 40px;
    }}
</style>
</head>
<body>
{html_body}
</body>
</html>"""
    return html_template
  except Exception as e:
    print(f"Erreur lors du formatage du rapport : {str(e)}")
    raise Exception("Error generating report")







################################### PDF TO TEMPLATE SECTION ##########################################

@anvil.server.callable
def process_pdf(prompt, pdf_file):
  """
  Convert PDF to text, then process it using GPT-4 text endpoint.
  """

  try:
    # Get PDF bytes
    pdf_bytes = pdf_file.get_bytes()
    pdf_stream = io.BytesIO(pdf_bytes)

    # Extract text using PyPDF2
    reader = PyPDF2.PdfReader(pdf_stream)

    # Collect text from all pages
    pdf_text = ""
    for page in reader.pages:
      pdf_text += page.extract_text() or ""

    # Build messages for standard GPT-4
    # We'll chunk the text if it's too large, or just show a simple prompt
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": f"{prompt}\n\nPDF Content:\n{pdf_text}"}
    ]

    # Make the API call to GPT-4 (text-based)
    response = client.chat.completions.create(
        model=DEFAULT_MODEL,  # standard GPT-4, not the vision preview
        messages=messages,
        max_tokens=DEFAULT_MAX_TOKENS,
        temperature=DEFAULT_TEMPERATURE
    )

    # Return the model's output
    return response.choices[0].message.content

  except Exception as e:
    print(f"Error processing PDF: {str(e)}")
    raise Exception(f"Error processing PDF: {str(e)}")


"""
Usage examples:
pdf_file = anvil.file_picker.pick_file(file_types=['application/pdf'])
summary = anvil.server.call('process_pdf', pdf_file)
"""


@anvil.server.callable
def reprocess_output_with_prompt(first_output, second_prompt):
  """
  Takes the first model output and a second prompt,
  then calls the GPT-4 endpoint again for a refined output.
  """
  try:
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": first_output},
        {"role": "user", "content": second_prompt},
    ]

    response = client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=messages,
        max_tokens=DEFAULT_MAX_TOKENS
    )

    return response.choices[0].message.content

  except Exception as e:
    print(f"Error in reprocess_output_with_prompt: {str(e)}")
    raise Exception(f"Error in reprocess_output_with_prompt: {str(e)}")


@anvil.server.callable
def store_final_output_in_db(final_output, template_name):
  """
  Logs the final output in the customtemplatestable under header "prompt",
  sets the owner to the current user, sets templateName, and sets systemPrompt to True.
  """
  user = anvil.users.get_user()
  if not user:
    raise Exception("No user is currently logged in.")

  # Add row in your customtemplatestable
  app_tables.custom_templates.add_row(
      prompt=final_output,
      owner=user,
      template_name=template_name,
  )








"""
Usage example:
prompt = anvil.server.call('get_prompt', 'desired_prompt_name')
"""



######################################### EDITION SECTION ######################################

@anvil.server.callable
def edit_report(transcription, report):
  """
  Processes transcribed voice commands to edit a veterinary report.

  Args:
      transcription (str): The transcribed voice command with editing instructions
      report (str): The current report content to be edited

  Returns:
      str: The edited report content
  """
  prompt = """
Tu es un assistant IA expert dans l'édition de rapports vétérinaires selon les commandes orales du vétérinaire utilisateur.
Accomplis la demande du vétérinaire utilisateur en respectant la précision de la médecine vétérinaire et l'orthographe des termes techniques. Assure-toi que ton output inclue toujours l'intégralité du rapport.

Exemples:
- Si le vétérinaire demande des ajouts, renvoie le compte rendu entier avec les ajouts
- Si le vétérinaire demande des modifications, renvoie le compte rendu entier avec les modifications
- Si le vétérinaire demande des suppressions, renvoie le compte rendu entier sans les éléments à supprimer

Voici le rapport actuel:
{report}

Instruction du vétérinaire pour éditer ce rapport:
{transcription}
  """

  try:
    formatted_prompt = prompt.format(report=report, transcription=transcription)

    messages = [
        {"role": "system", "content": formatted_prompt}
    ]

    response = client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=messages,
        temperature=DEFAULT_TEMPERATURE,
        max_tokens=DEFAULT_MAX_TOKENS
    )

    print("Edited report generated successfully")
    return response.choices[0].message.content
  except Exception as e:
    print(f"GPT-4 API error: {str(e)}")
    raise Exception(f"Error editing report: {str(e)}")



@anvil.server.callable
def EN_edit_report(transcription, report):
  """
  Processes transcribed voice commands to edit a veterinary report.

  Args:
      transcription (str): The transcribed voice command with editing instructions
      report (str): The current report content to be edited

  Returns:
      str: The edited report content
  """
  prompt = """
You are an AI assistant specialized in editing veterinary reports according to the verbal commands of the veterinary user.
Complete the veterinary user's request while maintaining accuracy in veterinary medicine and correct spelling of technical terms. Make sure your output always includes the entire report.
Examples:

If the veterinarian requests additions, return the entire report with the additions
If the veterinarian requests modifications, return the entire report with the modifications
If the veterinarian requests deletions, return the entire report without the elements to be deleted
Here is the current report:
{report}
Veterinarian's instruction to edit this report:
{transcription}
  """

  try:
    formatted_prompt = prompt.format(report=report, transcription=transcription)

    messages = [
        {"role": "system", "content": formatted_prompt}
    ]

    response = client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=messages,
        temperature=DEFAULT_TEMPERATURE,
        max_tokens=DEFAULT_MAX_TOKENS
    )

    print("Edited report generated successfully")
    return response.choices[0].message.content
  except Exception as e:
    print(f"GPT-4 API error: {str(e)}")
    raise Exception(f"Error editing report: {str(e)}")
