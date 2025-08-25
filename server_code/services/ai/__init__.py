import anvil.secrets
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
from openai import OpenAI
from pydub import AudioSegment

try:
  openai_key = anvil.secrets.get_secret("OPENAI_API_KEY")
  client = OpenAI(api_key=openai_key)
  print("OpenAI API initialized successfully")
except Exception as e:
  print(f"Error initializing OpenAI API: {str(e)}")
  raise RuntimeError("Failed to initialize OpenAI API")

DEFAULT_MODEL = "chatgpt-4o-latest"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 10000
RETRY_LIMIT = 3


@anvil.server.callable
def initialize_server_environment():
  print("--- SERVER INITIALIZATION CHECK ---")
  try:
    AudioSegment.silent(duration=10)
    print("SUCCESS: FFmpeg dependency is correctly installed and accessible.")
  except Exception as e:
    print("ERROR: FFmpeg dependency check failed.")
    print("   Audio processing will likely fail for non-WAV formats.")
    print(f"   Details: {str(e)}")
  print("-----------------------------------")
  return True
