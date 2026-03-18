from pathlib import Path

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QFileDialog, QWidget

from app.utils.paths import project_root


_LAST_DIRECTORY_KEY = "file_dialogs/last_directory"


def _settings() -> QSettings:
  return QSettings()


def get_last_directory() -> str:
  saved_directory = _settings().value(_LAST_DIRECTORY_KEY, "", type=str)

  if saved_directory and Path(saved_directory).exists():
    return saved_directory

  return str(project_root())


def _store_directory_from_path(path_str: str) -> None:
  if not path_str:
    return

  path = Path(path_str)

  if path.exists() and path.is_dir():
    directory = path
  else:
    directory = path.parent

  _settings().setValue(_LAST_DIRECTORY_KEY, str(directory))


def get_open_file_names(
  parent: QWidget | None,
  title: str,
  file_filter: str,
) -> tuple[list[str], str]:
  file_paths, selected_filter = QFileDialog.getOpenFileNames(
    parent,
    title,
    get_last_directory(),
    file_filter,
  )

  if file_paths:
    _store_directory_from_path(file_paths[0])

  return file_paths, selected_filter


def get_save_file_name(
  parent: QWidget | None,
  title: str,
  suggested_path: str,
  file_filter: str,
) -> tuple[str, str]:
  default_directory = Path(get_last_directory()) / suggested_path

  file_path, selected_filter = QFileDialog.getSaveFileName(
    parent,
    title,
    str(default_directory),
    file_filter,
  )

  if file_path:
    _store_directory_from_path(file_path)

  return file_path, selected_filter