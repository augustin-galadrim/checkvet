from ._anvil_designer import TemplatesTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import base64

class Templates(TemplatesTemplate):
  def __init__(self, **properties):
    print("Initialisation du formulaire Templates...")
    # Initialiser les composants du formulaire
    self.init_components(**properties)
    print("Composants du formulaire initialisés.")

    # Attacher le gestionnaire d'événement "show"
    self.add_event_handler("show", self.form_show)

  def form_show(self, **event_args):
    """Une fois le formulaire affiché, lire les modèles depuis le serveur et remplir la liste HTML."""
    print("Déclenchement de form_show du formulaire Templates.")
    templates = anvil.server.call("read_templates")
    print(f"Le serveur a renvoyé {len(templates)} modèles.")
    # Pousser la liste des modèles dans le code JavaScript
    self.call_js("populateTemplates", templates)

  def refresh_session_relay(self, **event_args):
    """Relay method for refreshing the session when called from JS"""
    try:
      return anvil.server.call("check_and_refresh_session")
    except Exception as e:
      print(f"[DEBUG] Error in refresh_session_relay: {str(e)}")
      return False

  # ----------------------
  # Méthodes de navigation
  # ----------------------
  def open_production_form(self, **event_args):
    """Ouvrir le formulaire AudioManager depuis l'onglet 'Production'."""
    open_form("AudioManager")

  def open_archives_form(self, **event_args):
    """Ouvrir le formulaire Archives depuis l'onglet 'Archives'."""
    current_user = anvil.users.get_user()
    if current_user['supervisor']:
      open_form("ArchivesSecretariat")
    else:
      open_form("Archives")

  def open_settings_form(self, **event_args):
    """Ouvrir le formulaire Settings depuis l'onglet 'Paramètres'."""
    open_form("Settings")

  def open_create_form(self, **event_args):
    """
    Ancienne méthode qui ouvrait AudioManager,
    mais nous ne l'utiliserons plus maintenant que nous avons un modal personnalisé.
    (Conservée à titre de référence.)
    """
    open_form("AudioManager")

  # --------------------
  # Ouverture de l'éditeur de template
  # --------------------
  def open_template_editor(self, template_id=None, **event_args):
    """
    Ouvre le formulaire TemplateEditor avec les paramètres appropriés.
    Si template_id est fourni, cherche le template correspondant par son nom.
    Sinon, crée un nouveau template.
    """
    print(f"open_template_editor appelé avec template_id={template_id}")

    if template_id:
      # Mode édition - Rechercher le template par nom
      templates = anvil.server.call("read_templates")
      found_template = None

      # template_id contient en fait le nom du template dans notre cas
      template_name = template_id

      for template in templates:
        if template.get("template_name") == template_name:
          found_template = template
          break

      if not found_template:
        alert(f"Template avec ID {template_id} introuvable.")
        return

      print(f"Ouverture de l'éditeur de template pour éditer: {found_template['template_name']}")
      open_form("TemplateEditor", template=found_template)
    else:
      # Mode création
      print("Ouverture de l'éditeur de template pour créer un nouveau template")
      open_form("TemplateEditor")

  # --------------------------------------
  # Logique du modal pour "Créer" => Transformation PDF en template
  # --------------------------------------
  def show_pdf_modal(self, **event_args):
    """
    Appelé depuis JS lors du clic sur le bouton "+ Créer".
    Affiche le modal de téléchargement PDF.
    """
    print("Affichage du modal PDF...")
    self.call_js("openPdfModal")

  def transform_pdf_to_template(self, base64_pdf, template_name, **event_args):
    """
    1) Convertir base64_pdf en anvil.BlobMedia
    2) Traiter le PDF avec un premier prompt puis retraiter avec un second prompt
    3) Enregistrer le résultat final dans la base de données
    4) Afficher une bannière de succès
    """
    print(f"Appel de transform_pdf_to_template avec template_name={template_name}")

    # 1) Convertir la chaîne Base64 en BlobMedia PDF
    pdf_bytes = base64.b64decode(base64_pdf)
    pdf_file = anvil.BlobMedia(content_type="application/pdf", content=pdf_bytes, name="uploaded.pdf")

    # 2) Définir les prompts
    first_prompt = """
Rôle

Vous êtes un expert en analyse de documents structurés, spécialisé dans l'extraction de la structure et de l'organisation des informations dans des rapports techniques et médicaux. Votre mission est de décortiquer et de restituer la structure détaillée d'un rapport vétérinaire en identifiant ses sections, titres et la manière dont les informations sont organisées, sans inclure de détails spécifiques au cas traité.
Tâche

    Identification des sections principales : Repérer et nommer les grandes parties du rapport (ex. : Introduction, Examen clinique, Diagnostic, etc.).
    Analyse de l'organisation interne : Déterminer la hiérarchie des informations dans chaque section (ex. : sous-titres, paragraphes, tableaux).
    Définition des catégories d'informations : Classifier les données contenues dans chaque section (ex. : informations administratives, symptômes observés, traitements prescrits).
    Restitution sous forme de structure : Fournir une vue claire et organisée du rapport en listant ses sections et leur contenu attendu, sans divulguer de données spécifiques.

Contexte

L'analyse de la structure d'un rapport vétérinaire est essentielle pour garantir une compréhension rapide et efficace des informations qu'il contient. Ce travail est réalisé avec la plus grande rigueur et une expertise reconnue, en respectant les standards de documentation vétérinaire. Il permet d'assurer une organisation logique et fluide des données, facilitant ainsi leur utilisation par les professionnels du domaine. Cette analyse est utile pour améliorer la standardisation des rapports médicaux et optimiser leur lisibilité.
Exemples

Voici trois structures types de rapports vétérinaires qui pourraient correspondre à votre demande :
Exemple 1 : Structure d'un rapport vétérinaire général

    Informations générales (Nom du patient, espèce, race, âge, propriétaire)
    Motif de consultation
    Antécédents médicaux
    Examen clinique (Observations générales, constantes physiologiques, examen des organes)
    Examens complémentaires (Analyses sanguines, imagerie, tests spécifiques)
    Diagnostic
    Plan de traitement (Médicaments, recommandations, interventions nécessaires)
    Pronostic
    Conclusions et suivi

Exemple 2 : Structure d'un rapport d'urgence vétérinaire

    Identification du patient et du propriétaire
    Nature de l'urgence et circonstances
    Évaluation initiale (signes vitaux, état général)
    Actions immédiates effectuées
    Examens complémentaires réalisés
    Diagnostic provisoire
    Traitement administré
    Recommandations de suivi

Exemple 3 : Structure d'un rapport de chirurgie vétérinaire

    Informations administratives
    Motif de l'intervention
    Examen pré-opératoire
    Détails de l'anesthésie utilisée
    Description de l'intervention chirurgicale
    Résultats immédiats et complications éventuelles
    Soins post-opératoires recommandés
    Suivi et recommandations
      """
    second_prompt = """
# Role
Tu es un expert de premier plan en rédaction de *system prompts* spécialisés, chargé de structurer des directives précises et optimisées pour une IA transformant la transcription d'un examen vétérinaire en un rapport détaillé. Ton expertise te permet de produire des *system prompts* clairs, rigoureux et adaptés au format fourni, garantissant une restitution fluide et professionnelle des informations médicales.

# Task
Ta mission est de rédiger un *system prompt* qui guidera une IA dans la conversion d'une transcription brute d'examen vétérinaire en un rapport structuré conforme au modèle spécifié. Pour cela, tu devras :
1. **Analyser la structure attendue du rapport** pour en extraire les sections clés.
2. **Identifier les éléments pertinents dans la transcription** et préciser comment les organiser.
3. **Rédiger un *system prompt* clair et détaillé** qui impose le respect du format, du ton et des exigences médicales.
4. **Inclure des consignes strictes sur le traitement des données médicales**, garantissant précision et exhaustivité.
5. **Exiger une sortie conforme au modèle fourni**, sans ajout d'informations superflues ni omission d'éléments critiques.

# Context
Le traitement des examens vétérinaires exige une rigueur scientifique absolue. L'objectif est de transformer des notes parfois désorganisées ou dictées à la volée en un document final professionnel, exploitable par des cliniciens, des propriétaires d'animaux ou des institutions vétérinaires. Ce travail requiert une précision terminologique, une logique structurée et une parfaite compréhension du format attendu. Ton *system prompt* doit garantir que l'IA restitue un rapport fidèle aux observations médicales, organisé et rédigé de manière impeccable.

# Examples
*(Si un modèle de rapport a été fourni, s'y référer pour adapter le *system prompt*.)*
Voici trois exemples de sections qui pourraient être demandées dans le *system prompt* :

1. **Introduction et identification**
   - Nom de l'animal, espèce, race, âge, sexe
   - Propriétaire : nom et coordonnées
   - Motif de consultation

2. **Examen clinique**
   - Température, poids, fréquence cardiaque et respiratoire
   - État général (muqueuses, hydratation, comportement)
   - Système nerveux, digestif, locomoteur, etc.

3. **Conclusion et recommandations**
   - Diagnostic ou hypothèses diagnostiques
   - Traitement proposé
   - Suivi recommandé

# Important details
- Le *system prompt* doit être **formulé de manière prescriptive et non ambiguë**.
- Il doit exiger une **organisation logique et standardisée** du rapport.
- L'IA doit respecter scrupuleusement la terminologie vétérinaire et éviter toute interprétation erronée.
- La sortie générée doit **être conforme au modèle fourni**, sans ajout ni omission d'informations essentielles.
- **Le ton doit être professionnel, clair et précis**, sans formulation inutilement complexe.
- Tu ne dois faire **aucune autre tâche que l'écriture de ce *system prompt***.
      """
    try:
      # Traiter le texte du PDF avec le premier prompt
      initial_result = anvil.server.call("process_pdf", first_prompt, pdf_file)
      print("Résultat du premier traitement (tronqué) :", initial_result[:100])

      # Retraiter avec le second prompt
      final_result = anvil.server.call("reprocess_output_with_prompt", initial_result, second_prompt)

      # 3) Enregistrer le résultat final dans la base de données
      anvil.server.call("store_final_output_in_db", final_result, template_name)
    except Exception as e:
      print("Erreur lors de la transformation du PDF en template :", e)
      alert(f"Erreur : {str(e)}")
      return

    # 4) Afficher la bannière de succès dans le modal
    self.call_js("showSuccessBanner")

  # ----------------------
  # Nouveau : Gestion de la priorité
  # ----------------------
  def set_priority(self, template_name, new_priority, **event_args):
    """
    Appelé depuis JavaScript lors du clic sur l'icône étoile d'un template.
    Cette méthode met à jour la priorité du template dans la base de données.
    """
    print(f"Mise à jour de la priorité du template {template_name} vers {new_priority}")
    try:
      anvil.server.call("set_priority", template_name, new_priority)
      print("Priorité mise à jour avec succès sur le serveur.")
    except Exception as e:
      print("Erreur lors de la mise à jour de la priorité :", e)
      alert(f"Erreur lors de la mise à jour de la priorité : {str(e)}")

  # ----------------------
  # Nouveau : Fonctionnalité de recherche
  # ----------------------
  def search_templates_client(self, query, **event_args):
    print(f"search_templates_client() appelé avec la requête : {query}")
    if not query:
      print("Requête vide ; renvoi des modèles initiaux.")
      templates = anvil.server.call("read_templates")
      self.call_js("populateTemplates", templates)
      return
    try:
      results = anvil.server.call("search_templates", query)
      print(f"La recherche a renvoyé {len(results)} résultats.")
      self.call_js("populateTemplates", results)
    except Exception as e:
      print("Échec de la recherche :", e)
