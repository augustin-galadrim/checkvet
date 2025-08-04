import anvil.secrets
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
import io
import PyPDF2
from . import (
  client,
  RETRY_LIMIT,
  DEFAULT_MODEL,
  DEFAULT_TEMPERATURE,
  DEFAULT_MAX_TOKENS,
)


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
      {"role": "user", "content": f"{prompt}\n\nPDF Content:\n{pdf_text}"},
    ]

    # Make the API call to GPT-4 (text-based)
    response = client.chat.completions.create(
      model=DEFAULT_MODEL,  # standard GPT-4, not the vision preview
      messages=messages,
      max_tokens=DEFAULT_MAX_TOKENS,
      temperature=DEFAULT_TEMPERATURE,
    )

    # Return the model's output
    return response.choices[0].message.content

  except Exception as e:
    print(f"Error processing PDF: {str(e)}")
    raise Exception(f"Error processing PDF: {str(e)}")


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
      model=DEFAULT_MODEL, messages=messages, max_tokens=DEFAULT_MAX_TOKENS
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
