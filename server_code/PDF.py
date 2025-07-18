import anvil.secrets
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
import anvil.media
from .UsersSpecial import get_full_user_info

# If using WeasyPrint:
from weasyprint import HTML
import base64

@anvil.server.callable
def build_report_pdf_base64(placeholders, images):
  """
  1) Retrieves user info (signature, header, footer, template).
  2) Merges placeholders into the template:
     - {{bodyContent}} --> placeholders["bodyContent"]
     - {{signature}}   --> inline base64 <img src="..."/>
     - {{reportHeader}} --> inline base64 <img src="..."/>
     - {{reportFooter}} --> inline base64 <img src="..."/>
  3) Converts the final HTML into a PDF (via WeasyPrint).
  4) Returns the PDF as a *base64 string*, for easy use in custom HTML.
  """
  print("DEBUG: Entering build_report_pdf_base64 server function.")
  print(f"DEBUG: placeholders argument: {placeholders}")
  print(f"DEBUG: images argument: {images}")

  # --------------------------------------------
  # 1) Retrieve full user info
  # --------------------------------------------
  print("DEBUG: Calling get_full_user_info()...")
  user_info = get_full_user_info()  # Make sure you have defined this function
  print(f"DEBUG: user_info retrieved: {user_info}")

  if not user_info:
    print("ERROR: No user found or user record not found!")
    raise anvil.users.AuthenticationFailed(
        "No user is logged in or user record not found."
    )

  # Extract relevant fields with updated column names
  template_content = user_info.get("template_content", "") or ""
  signature_image = user_info.get("signature_image")
  report_header_image = user_info.get("report_header_image")
  report_footer_image = user_info.get("report_footer_image")

  print("DEBUG: Extracted from user_info:")
  print(f"  template_content length: {len(template_content)}")
  print(f"  signature_image: {signature_image}")
  print(f"  report_header_image: {report_header_image}")
  print(f"  report_footer_image: {report_footer_image}")

  # ---------------------------------------------------
  # 2) Convert Media to inline base64 <img> tags
  # ---------------------------------------------------
  def media_to_img_tag(m):
    if m:
      print(f"DEBUG: media_to_img_tag: Converting media {m} to base64 inline data.")
      content_bytes = m.get_bytes()
      base64_data = base64.b64encode(content_bytes).decode('utf-8')
      content_type = m.content_type if m.content_type else "image/png"
      return f'<img src="data:{content_type};base64,{base64_data}" alt="UserImage" style="max-width:100%; height:auto;" />'
    else:
      print("DEBUG: media_to_img_tag: None media, returning empty string.")
      return ""

  signature_tag = media_to_img_tag(signature_image)
  header_tag = media_to_img_tag(report_header_image)
  footer_tag = media_to_img_tag(report_footer_image)

  # ---------------------------------------------------
  # 3) Merge placeholders into the template
  # ---------------------------------------------------
  print("DEBUG: Merging placeholders into template.")
  merged_html = template_content
  editor_content = placeholders.get("bodyContent", "")
  print(f"DEBUG: editor_content from placeholders: {editor_content[:100]}...")

  # Replace placeholders in the template
  merged_html = merged_html.replace("{{bodyContent}}", editor_content)
  merged_html = merged_html.replace("{{signature}}", signature_tag)
  merged_html = merged_html.replace("{{reportHeader}}", header_tag)
  merged_html = merged_html.replace("{{reportFooter}}", footer_tag)

  print("DEBUG: Template merge complete. (Snippet below.)")
  print(merged_html[:300])

  # ---------------------------------------------------
  # 4) Convert final HTML -> PDF (WeasyPrint)
  # ---------------------------------------------------
  try:
    print("DEBUG: Converting merged HTML to PDF via WeasyPrint.")
    pdf_bytes = HTML(string=merged_html).write_pdf()
    print("DEBUG: PDF generation successful. Bytes object returned.")
  except Exception as e:
    print(f"ERROR: Exception during PDF generation: {repr(e)}")
    raise e

  # ---------------------------------------------------
  # 5) Return the PDF as a base64 string
  # ---------------------------------------------------
  print("DEBUG: Converting PDF bytes to base64 for return.")
  pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")
  print("DEBUG: Returning base64-encoded PDF from build_report_pdf_base64.")

  return pdf_base64
