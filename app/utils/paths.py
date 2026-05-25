from pathlib import Path


def default_user_directory() -> Path:
  """
  Returns a friendly default folder for user file dialogs.
  """
  documents = Path.home() / "Documents"

  if documents.exists():
    return documents

  return Path.home()


def project_root() -> Path:
  """
  Returns the root folder of the project.
  """
  return Path(__file__).resolve().parents[2]
