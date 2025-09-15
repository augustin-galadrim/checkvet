import anvil.server
from anvil.tables import app_tables
from ..logging_server import get_logger
import io
import base64
from datetime import datetime

try:
  from weasyprint import HTML, CSS
except ImportError:
  raise ImportError(
    "The 'weasyprint' library is not installed in the server environment."
  )

logger = get_logger(__name__)


def _convert_media_to_data_uri(media_object):
  """
  Helper function to convert any Anvil Media object into a Base64 Data URI.
  Returns None if the media_object is invalid.
  """
  if media_object:
    content_type = media_object.get_content_type()
    base64_data = base64.b64encode(media_object.get_bytes()).decode("ascii")
    return f"data:{content_type};base64,{base64_data}"
  return None


@anvil.server.callable(require_user=True)
def generate_pdf_from_html(html_content):
  """
  Generates a PDF from HTML, dynamically fetching the correct header, footer,
  and signature for the user from the new asset_service.
  """
  logger.info("Starting PDF generation using the new asset service.")

  try:
    # --- Step 1: Fetch all required assets via the new service ---
    active_assets = anvil.server.call("get_active_assets_for_user_with_ids")

    header_data_uri = _convert_media_to_data_uri(
      active_assets.get("header").get("file")
      if active_assets.get("header") is not None
      else None
    )
    footer_data_uri = _convert_media_to_data_uri(
      active_assets.get("footer").get("file")
      if active_assets.get("footer") is not None
      else None
    )
    signature_data_uri = _convert_media_to_data_uri(
      active_assets.get("signature").get("file")
      if active_assets.get("signature") is not None
      else None
    )

    # --- Step 2: Build HTML blocks ---
    header_html = (
      f'<div id="header"><img src="{header_data_uri}"></div>' if header_data_uri else ""
    )
    footer_html = (
      f'<div id="footer"><img src="{footer_data_uri}"></div>' if footer_data_uri else ""
    )
    signature_html = (
      f'<div class="signature-section"><img src="{signature_data_uri}" alt="Signature"></div>'
      if signature_data_uri
      else ""
    )

    # --- Step 3: Combine everything into a single, structured HTML document ---
    full_html_document = f"""
            <!DOCTYPE html>
            <html>
            <head><meta charset="UTF-8"></head>
            <body>
                {header_html}
                {footer_html}
                <div class="main-content">
                    {html_content}
                    {signature_html}
                </div>
            </body>
            </html>
            """

    # --- Step 4: Define the stylesheet ---
    css = CSS(
      string="""
            @page {
                size: A4; margin: 3.5cm 2cm 3.5cm 2cm;
                @top-center { content: element(header); }
                @bottom-center { content: element(footer); }
            }
            #header, #footer {
                position: running(header); height: 2.5cm; width: 100%; text-align: center;
            }
            #footer { position: running(footer); }
            #header img, #footer img {
                max-height: 100%; max-width: 100%; object-fit: contain;
            }
            body { font-family: 'Helvetica', 'Arial', sans-serif; font-size: 11pt; line-height: 1.4; color: #333333; }
            h1, h2, h3, p, ul, li { margin: 0; padding: 0; font-weight: normal; }
            h1 { font-size: 1.6em; text-align: center; margin-bottom: 25px; color: #111111; font-weight: bold; }
            h2 { font-size: 1.3em; margin-top: 25px; padding-bottom: 6px; border-bottom: 1px solid #cccccc; color: #111111; font-weight: bold; }
            h3 { font-size: 1.1em; margin-top: 20px; margin-left: 5px; color: #222222; font-weight: bold; }
            p { margin-top: 8px; margin-left: 10px; }
            .signature-section { margin-top: 50px; padding-top: 15px; page-break-inside: avoid; text-align: left; }
            .signature-section img { max-width: 200px; height: auto; }
        """
    )

    # --- Step 5: Render and Return ---
    pdf_buffer = io.BytesIO()
    html = HTML(string=full_html_document)
    html.write_pdf(pdf_buffer, stylesheets=[css])
    pdf_bytes = pdf_buffer.getvalue()
    pdf_media = anvil.BlobMedia(
      content_type="application/pdf", content=pdf_bytes, name="report.pdf"
    )

    logger.info("PDF generation with dynamic assets successful.")
    return pdf_media

  except Exception as e:
    logger.error(f"Failed to generate PDF with WeasyPrint: {e}", exc_info=True)
    raise Exception(f"PDF generation failed on the server: {e}")
