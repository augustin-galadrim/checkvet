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
def format_report(transcription, language):
  """Generate report using GPT-4"""

  formatting_prompt_template = get_prompt("formatting", language)
  try:
    messages = [
      {"role": "system", "content": formatting_prompt_template},
      {"role": "user", "content": transcription},
    ]

    response = client.chat.completions.create(
      model=DEFAULT_MODEL,
      messages=messages,
      temperature=DEFAULT_TEMPERATURE,
      max_tokens=DEFAULT_MAX_TOKENS,
    )
    print(response.choices[0].message.content)
    return response.choices[0].message.content
  except Exception as e:
    print(f"GPT-4 API error: {str(e)}")
    raise Exception("Error generating report")
