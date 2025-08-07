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


def strip_leading_bullet(line):
  """
  Removes a leading bullet character sequence (e.g. "- ", "* ", "• ")
  from the line if present.
  """
  stripped_line = line.strip()
  for bullet_char in ("- ", "* ", "• "):
    if stripped_line.startswith(bullet_char):
      stripped_line = stripped_line[len(bullet_char) :]
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
