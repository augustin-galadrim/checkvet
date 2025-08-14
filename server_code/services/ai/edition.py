import anvil.secrets
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
from . import (
  client,
  RETRY_LIMIT,
  DEFAULT_MODEL,
  DEFAULT_TEMPERATURE,
  DEFAULT_MAX_TOKENS,
)
from ..prompts_service import get_prompt


@anvil.server.callable
def edit_report(transcription, report, language):
  """
  Processes transcribed voice commands to edit a veterinary report.

  Args:
      transcription (str): The transcribed voice command with editing instructions
      report (str): The current report content to be edited

  Returns:
      str: The edited report content
  """
  edition_prompt = get_prompt("edition", language)

  try:
    system_prompt = edition_prompt
    user_prompt = f"Report: {report}\nTranscription: {transcription}"

    messages = [
      {"role": "system", "content": system_prompt},
      {"role": "user", "content": user_prompt},
    ]

    response = client.chat.completions.create(
      model=DEFAULT_MODEL,
      messages=messages,
      temperature=DEFAULT_TEMPERATURE,
      max_tokens=DEFAULT_MAX_TOKENS,
    )

    print("Edited report generated successfully")
    return response.choices[0].message.content
  except Exception as e:
    print(f"GPT-4 API error: {str(e)}")
    raise Exception(f"Error editing report: {str(e)}")
