# **********************************************************************************************************************
#   FileName:
#       path.py
#
#   Description:
#       Utilities for interacting with paths
#
#   4/16/21 | Brandon Braun | brandonbraun653@gmail.com
# **********************************************************************************************************************

from pathlib import Path


def find_parent_path(current: Path, parent: str) -> Path:
    """
    Recursively finds the desired root path

    Args:
      current (Path): Starting path to search from
      parent (str): Stem inside the path

    Returns:
      Path: The found path or the system drive mount point
    """
    if current.stem == parent or current.is_mount():
        return current
    else:
        return find_parent_path(current.parent, parent)
