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

    messages = [{"role": "system", "content": formatted_prompt}]

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

    messages = [{"role": "system", "content": formatted_prompt}]

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
