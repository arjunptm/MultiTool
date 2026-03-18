from pathlib import Path


def project_root() -> Path:
  """
  Returns the root folder of the project.
  """
  return Path(__file__).resolve().parents[2]