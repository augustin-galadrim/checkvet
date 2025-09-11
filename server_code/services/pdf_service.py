import anvil.server
from anvil.tables import app_tables
from ..logging_server import get_logger
import io
import base64

try:
  from weasyprint import HTML, CSS
except ImportError:
  raise ImportError(
    "The 'weasyprint' library is not installed in the server environment."
  )

logger = get_logger(__name__)


def _get_image_data_uri(asset_name):
  """
  Helper function to fetch an image from the app_assets table and convert it to a Data URI.
  Returns None if the asset is not found.
  """
  asset_row = app_tables.assets.get(name=asset_name)
  if asset_row and asset_row["file"]:
    media = asset_row["file"]
    content_type = media.get_content_type()
    base64_data = base64.b64encode(media.get_bytes()).decode("ascii")
    return f"data:{content_type};base64,{base64_data}"
  logger.warning(f"Asset '{asset_name}' not found in 'app_assets' table.")
  return None


@anvil.server.callable(require_user=True)
def generate_pdf_from_html(html_content):
  """
  Generates a PDF from HTML, with a correctly scaled header/footer on every page,
  and a signature at the end of the document body.
  """
  logger.info("Starting PDF generation with the definitive header/footer method.")

  try:
    # --- Step 1: Fetch all required assets ---
    header_data_uri = _get_image_data_uri("default_header")
    footer_data_uri = _get_image_data_uri("default_footer")
    signature_data_uri = _get_image_data_uri("default_signature")

    # --- Step 2: Build HTML blocks for header, footer, and signature ---
    header_html = ""
    if header_data_uri:
      # This div will be captured by CSS and placed in the page header
      header_html = f'<div id="header"><img src="{header_data_uri}"></div>'

    footer_html = ""
    if footer_data_uri:
      # This div will be captured by CSS and placed in the page footer
      footer_html = f'<div id="footer"><img src="{footer_data_uri}"></div>'

    signature_html = ""
    if signature_data_uri:
      signature_html = f"""
            <div class="signature-section">
                <img src="{signature_data_uri}" alt="Signature">
                <p class="signature-line">Signature</p>
            </div>
            """

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

    # --- Step 4: Define the final, robust stylesheet ---
    css = CSS(
      string="""
            /* --- 1. PAGE SETUP & RUNNING ELEMENTS --- */
            @page {
                size: A4;
                margin: 3.5cm 2cm 3cm 2cm; /* Top, Right, Bottom, Left */

                /* Place the captured 'header' and 'footer' elements into the margin boxes */
                @top-center {
                    content: element(header);
                }
                @bottom-center {
                    content: element(footer);
                }
            }

            /* --- 2. CAPTURE & STYLE HEADER/FOOTER --- */
            #header {
                position: running(header); /* Capture this div as a named element */
            }
            #footer {
                position: running(footer); /* Capture this div as a named element */
            }

            /* THIS IS THE KEY: Style the images INSIDE the captured divs */
            #header img, #footer img {
                max-height: 2.5cm; /* Set a maximum height to prevent overflow */
                width: 100%;       /* Allow the width to fill the content area */
                object-fit: contain; /* Scale the image to fit INSIDE the max-height, preserving aspect ratio */
            }

            /* --- 3. BODY & CONTENT STYLING --- */
            body { font-family: 'Helvetica', 'Arial', sans-serif; font-size: 11pt; line-height: 1.4; color: #333333; }
            h1, h2, h3, p, ul, li { margin: 0; padding: 0; font-weight: normal; }
            h1 { font-size: 1.6em; text-align: center; margin-bottom: 25px; color: #111111; font-weight: bold; }
            h2 { font-size: 1.3em; margin-top: 25px; padding-bottom: 6px; border-bottom: 1px solid #cccccc; color: #111111; font-weight: bold; }
            h3 { font-size: 1.1em; margin-top: 20px; margin-left: 5px; color: #222222; font-weight: bold; }
            p { margin-top: 8px; margin-left: 10px; }
            .signature-section { margin-top: 50px; padding-top: 15px; page-break-inside: avoid; text-align: left; }
            .signature-section img { max-width: 200px; height: auto; }
            .signature-section p.signature-line { margin-top: 5px; border-top: 1px solid #333; padding-top: 5px; font-size: 10pt; text-align: center; width: 200px; }
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

    logger.info("PDF generation with running elements successful.")
    return pdf_media

  except Exception as e:
    logger.error(f"Failed to generate PDF with WeasyPrint: {e}", exc_info=True)
    raise Exception(f"PDF generation failed on the server: {e}")
