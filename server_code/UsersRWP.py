import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server

@anvil.server.callable
def read_user():
  print("DEBUG: Entering read_user function.")
  current_user = anvil.users.get_user()
  print(f"DEBUG: Current user: {current_user}")
  if current_user is None:
    print("DEBUG: No user is logged in.")
    return None

  try:
    user_row = app_tables.users.get(email=current_user['email'])
    #print(f"DEBUG: Retrieved user_row: {user_row}")
    if user_row is None:
      print("DEBUG: No user row found for the current user.")
      return None

    #print(f"DEBUG: User row as dict: {dict(user_row)}")

    # Create user data dictionary with direct access
    user_data = {
        'email': user_row['email'],
        'enabled': user_row['enabled'],
        'last_login': user_row['last_login'],
        'n_password_failures': user_row['n_password_failures'],
        'confirmed_email': user_row['confirmed_email'],
        'signed_up': user_row['signed_up'],
        'supervisor': user_row['supervisor'],
        'structure': user_row['structure']['name'] if user_row['structure'] else None,
        'signature_image': user_row['signature_image'],
        'report_header_image': user_row['report_header_image'],
        'report_footer_image': user_row['report_footer_image'],
        'phone': user_row['phone'] or '',
        'name': user_row['name'] or '',
        'specialite': user_row['specialite'] or '',
        'additional_info': user_row['additional_info'] or '',
        'favorite_language': user_row['favorite_language'] or '',
        'mobile_installation': user_row['mobile_installation'] or ''
    }

    print(f"DEBUG: Returning user data: {user_data}")
    return user_data

  except Exception as e:
    print(f"ERROR: Unexpected error in read_user: {str(e)}")
    return None

@anvil.server.callable
def write_user(enabled=None, n_password_failures=None, confirmed_email=None,
               remembered_logins=None, supervisor=None, structure=None,
               signature_image=None, report_header_image=None, report_footer_image=None, phone=None, name=None, additional_info=None, specialite=None, favorite_language=None, mobile_installation=None):
  print("DEBUG: Entering write_user function.")
  current_user = anvil.users.get_user()
  print(f"DEBUG: Current user: {current_user}")
  if current_user is None:
    print("DEBUG: No user is logged in.")
    return False

  user_row = app_tables.users.get(email=current_user['email'])
  print(f"DEBUG: Retrieved user_row: {user_row}")
  if user_row is None:
    print("DEBUG: No user row found for the current user.")
    return False

  try:
    if enabled is not None:
      user_row['enabled'] = enabled
      print(f"DEBUG: Updated enabled to {enabled}.")
    if n_password_failures is not None:
      user_row['n_password_failures'] = n_password_failures
      print(f"DEBUG: Updated n_password_failures to {n_password_failures}.")
    if confirmed_email is not None:
      user_row['confirmed_email'] = confirmed_email
      print(f"DEBUG: Updated confirmed_email to {confirmed_email}.")
    if remembered_logins is not None:
      user_row['remembered_logins'] = remembered_logins
      #print(f"DEBUG: Updated remembered_logins to {remembered_logins}.")
    if supervisor is not None:
      user_row['supervisor'] = supervisor
      print(f"DEBUG: Updated supervisor to {supervisor}.")
    if structure and structure.strip():  # Only process non-empty structure values
      print(f"DEBUG: Looking for structure with name: {structure}")
      structure_row = app_tables.structures.get(name=structure)
      if structure_row:
        user_row['structure'] = structure_row
        print(f"DEBUG: Updated structure to: {structure}")
      else:
        error_message = f"ERROR: No structure found with name '{structure}' in table structures."
        print(error_message)
        raise ValueError(error_message)
    if signature_image is not None:
      user_row['signature_image'] = signature_image
      print(f"DEBUG: Updated signature_image to {signature_image}.")
    if report_header_image is not None:
      user_row['report_header_image'] = report_header_image
      print(f"DEBUG: Updated report_header_image to {report_header_image}.")
    if report_footer_image is not None:
      user_row['report_footer_image'] = report_footer_image
      print(f"DEBUG: Updated report_footer_image to {report_footer_image}.")
    if phone is not None:
      user_row['phone'] = phone
      print(f"DEBUG: Updated telephone to {phone}.")
    if name is not None:
      user_row['name'] = name
      print(f"DEBUG: Updated name to {name}.")
    if specialite is not None:
      user_row['specialite'] = specialite
      print(f"DEBUG: Updated name to {specialite}.")
    if additional_info is not None:
      user_row['additional_info'] = additional_info
      print(f"DEBUG: Updated additional_info to {additional_info}.")
    if favorite_language is not None:
      user_row['favorite_language'] = favorite_language
      print(f"DEBUG: Updated favorite_language to {favorite_language}.")
    if mobile_installation is not None:
      user_row['mobile_installation'] = mobile_installation
      print(f"DEBUG: Updated mobile_installation to {mobile_installation}.")

    print("DEBUG: Successfully updated user.")
    return True

  except Exception as e:
    print(f"ERROR: Unexpected error in write_user: {str(e)}")
    return False

@anvil.server.callable
def pick_user_info(header):
  print("DEBUG: Entering pick_user_info function.")
  print(f"DEBUG: Requested header: {header}")
  current_user = anvil.users.get_user()
  print(f"DEBUG: Current user: {current_user}")
  if current_user is None:
    print("DEBUG: No user is logged in.")
    return None

  user_row = app_tables.users.get(email=current_user['email'])
  print(f"DEBUG: Retrieved user_row: {user_row}")
  if user_row is None:
    print("DEBUG: No user row found for the current user.")
    return None

  if header == 'structure':
    structure_row = user_row['structure']
    if structure_row:
      try:
        structure_name = structure_row['name']
        print(f"DEBUG: Retrieved structure_name: {structure_name}")
        return structure_name
      except KeyError:
        print("ERROR: 'structure' column is missing in table structures")
        return None
    else:
      print("DEBUG: No structure_row linked to this user.")
      return None

  #print(f"DEBUG: Retrieved value for header '{header}': {user_row.get(header)}")
  return user_row['additional_info']

@anvil.server.callable
def pick_user_info2(header):
  print("DEBUG: Entering pick_user_info function.")
  print(f"DEBUG: Requested header: {header}")
  current_user = anvil.users.get_user()
  print(f"DEBUG: Current user: {current_user}")
  if current_user is None:
    print("DEBUG: No user is logged in.")
    return None

  user_row = app_tables.users.get(email=current_user['email'])
  print(f"DEBUG: Retrieved user_row: {user_row}")
  if user_row is None:
    print("DEBUG: No user row found for the current user.")
    return None

  if header == 'structure':
    structure_row = user_row['structure']
    if structure_row:
      try:
        structure_name = structure_row['name']
        print(f"DEBUG: Retrieved structure_name: {structure_name}")
        return structure_name
      except KeyError:
        print("ERROR: 'structure' column is missing in table structures")
        return None
    else:
      print("DEBUG: No structure_row linked to this user.")
      return None

  #print(f"DEBUG: Retrieved value for header '{header}': {user_row.get(header)}")
  return user_row['mobile_installation']


@anvil.server.callable
def pick_user_favorite_language():
  print("DEBUG: Entering pick_user_info function.")
  current_user = anvil.users.get_user()
  print(f"DEBUG: Current user: {current_user}")
  if current_user is None:
    print("DEBUG: No user is logged in.")
    return None

  user_row = app_tables.users.get(email=current_user['email'])
  print(f"DEBUG: Retrieved user_row: {user_row}")
  if user_row is None:
    print("DEBUG: No user row found for the current user.")
    return None

  #print(f"DEBUG: Retrieved value for header '{header}': {user_row.get(header)}")
  return user_row['favorite_language']

"""
# To read the current user's information
user_info = anvil.server.call('read_user')

# To update the user's information
success = anvil.server.call('write_user', structure='New Clinic Name', supervisor=True)

# To get a specific piece of information about the user
email_signature = anvil.server.call('pick_user_info', 'email_signature')
"""


@anvil.server.callable
def pick_user_structure():
  print("DEBUG: Entering pick_user_info function.")

  current_user = anvil.users.get_user()
  print(f"DEBUG: Current user: {current_user}")
  if current_user is None:
    print("DEBUG: No user is logged in.")
    return None

  user_row = app_tables.users.get(email=current_user['email'])
  print(f"DEBUG: Retrieved user_row: {user_row}")
  if user_row is None:
    print("DEBUG: No user row found for the current user.")
    return None


  structure_row = user_row['structure']
  if structure_row:
    try:
      structure_name = structure_row['name']
      print(f"DEBUG: Retrieved structure_name: {structure_name}")
      return structure_name
    except KeyError:
      print("ERROR: 'structure' column is missing in table structures")
      return None
  else:
    print("DEBUG: No structure_row linked to this user.")
    return None

  #print(f"DEBUG: Retrieved value for header '{header}': {user_row.get(header)}")
  return structure_name
