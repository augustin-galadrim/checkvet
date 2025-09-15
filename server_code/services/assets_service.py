import anvil.server
import anvil.users
from anvil.tables import app_tables
from ..logging_server import get_logger
from datetime import datetime

logger = get_logger(__name__)


@anvil.server.callable(require_user=True)
def upload_asset(file, type, name):
  """
  Handles the upload of any asset (signature, header, footer).
  It ensures that only one asset of a given type is marked as 'default' for an owner.
  """
  user = anvil.users.get_user(allow_remembered=True)
  if not file or not type or not name:
    raise ValueError("File, type, and name are required to upload an asset.")

  owner_user = None
  owner_structure = None

  # Determine the owner based on the asset type
  if type == "signature":
    owner_user = user
  elif type in ["header", "footer"]:
    # Every user is guaranteed to have a structure after our migration.
    owner_structure = user["structure"]
    if not owner_structure:
      logger.error(
        f"Critical error: User '{user['email']}' has no linked structure during asset upload."
      )
      raise Exception("User is not linked to a structure.")
  else:
    raise ValueError(f"Invalid asset type '{type}'.")

    # Domain Logic: When a new asset is uploaded, it becomes the new default.
    # We must find any existing default for this owner and type and unset it.
  existing_defaults = app_tables.assets.search(
    type=type, owner_user=owner_user, owner_structure=owner_structure, is_default=True
  )
  for row in existing_defaults:
    row["is_default"] = False

    # Create the new asset row
  app_tables.assets.add_row(
    name=name,
    type=type,
    file=file,
    owner_user=owner_user,
    owner_structure=owner_structure,
    is_default=True,
    is_archived=False,
    created_date=datetime.now(),
  )
  logger.info(
    f"User '{user['email']}' successfully uploaded asset '{name}' of type '{type}'."
  )
  return True

@anvil.server.callable(require_user=True)
def get_active_assets_for_user_with_ids():
  """
  Fetches the active header, footer, and signature for the user,
  including the asset's row ID and media file for the client.
  """
  user = anvil.users.get_user(allow_remembered=True)

  def get_asset_data(owner_user=None, owner_structure=None, type=None):
    row = app_tables.assets.get(
      owner_user=owner_user,
      owner_structure=owner_structure,
      type=type,
      is_default=True,
      is_archived=False,
    )
    if row:
      return {"id": row.get_id(), "file": row["file"]}
    return None

  structure = user["structure"]

  return {
    "signature": get_asset_data(owner_user=user, type="signature"),
    "header": get_asset_data(owner_structure=structure, type="header")
    if structure
    else None,
    "footer": get_asset_data(owner_structure=structure, type="footer")
    if structure
    else None,
  }


@anvil.server.callable(require_user=True)
def delete_asset(asset_id):
  """
  Deletes an asset, ensuring the user has permission to do so.
  """
  user = anvil.users.get_user(allow_remembered=True)
  asset_row = app_tables.assets.get_by_id(asset_id)

  if not asset_row:
    logger.warning(
      f"User '{user['email']}' attempted to delete non-existent asset ID '{asset_id}'."
    )
    return False

    # Permission Check: User must own the asset or be a supervisor of the structure that owns it.
  is_owner = asset_row["owner_user"] == user
  is_supervisor = (
    user["supervisor"]
    and asset_row["owner_structure"]
    and asset_row["owner_structure"] == user["structure"]
  )

  if is_owner or is_supervisor:
    asset_name = asset_row["name"]
    asset_row.delete()
    logger.info(
      f"User '{user['email']}' successfully deleted asset '{asset_name}' (ID: {asset_id})."
    )
    return True
  else:
    logger.error(
      f"SECURITY: User '{user['email']}' permission denied to delete asset ID '{asset_id}'."
    )
    return False
