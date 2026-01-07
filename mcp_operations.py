"""
Project operations for MCP Server Manager.
Handles moving, consolidating, and organizing projects.
"""

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple


@dataclass
class MoveResult:
    """Result of a project move operation."""
    success: bool
    source: str
    destination: str
    error: Optional[str] = None


@dataclass
class ProjectConflict:
    """Information about a naming conflict."""
    source: str
    conflicting_name: str
    suggested_name: str


def check_move_conflicts(
    projects: List[str],
    target_dir: str
) -> Tuple[List[str], List[ProjectConflict]]:
    """
    Check which projects can be moved without conflicts.

    Args:
        projects: List of project paths to move
        target_dir: Destination directory

    Returns:
        Tuple of (safe_to_move, conflicts)
    """
    target_dir = os.path.expanduser(target_dir)
    target_dir = os.path.abspath(target_dir)

    safe = []
    conflicts = []

    # Get existing names in target
    existing_names = set()
    if os.path.isdir(target_dir):
        existing_names = set(os.listdir(target_dir))

    # Track names we're planning to use
    planned_names = set()

    for project_path in projects:
        project_path = os.path.abspath(project_path)
        project_name = os.path.basename(project_path)

        # Skip if already in target
        if os.path.dirname(project_path) == target_dir:
            continue

        # Check for conflict
        if project_name in existing_names or project_name in planned_names:
            # Generate unique name
            suggested = _generate_unique_name(
                project_name,
                existing_names | planned_names
            )
            conflicts.append(ProjectConflict(
                source=project_path,
                conflicting_name=project_name,
                suggested_name=suggested
            ))
        else:
            safe.append(project_path)
            planned_names.add(project_name)

    return safe, conflicts


def _generate_unique_name(name: str, existing: set) -> str:
    """Generate a unique project name by appending a number."""
    counter = 2
    base_name = name

    while name in existing:
        name = f"{base_name}-{counter}"
        counter += 1

    return name


def move_project(
    source: str,
    target_dir: str,
    new_name: Optional[str] = None
) -> MoveResult:
    """
    Move a project to a new location.

    Args:
        source: Source project path
        target_dir: Target directory
        new_name: Optional new name for the project

    Returns:
        MoveResult with success/failure info
    """
    source = os.path.abspath(os.path.expanduser(source))
    target_dir = os.path.abspath(os.path.expanduser(target_dir))

    if not os.path.isdir(source):
        return MoveResult(
            success=False,
            source=source,
            destination="",
            error=f"Source does not exist: {source}"
        )

    # Determine destination
    project_name = new_name or os.path.basename(source)
    destination = os.path.join(target_dir, project_name)

    # Check if destination exists
    if os.path.exists(destination):
        return MoveResult(
            success=False,
            source=source,
            destination=destination,
            error=f"Destination already exists: {destination}"
        )

    # Ensure target directory exists
    os.makedirs(target_dir, exist_ok=True)

    try:
        # Use shutil.move for cross-filesystem support
        shutil.move(source, destination)
        return MoveResult(
            success=True,
            source=source,
            destination=destination
        )
    except Exception as e:
        return MoveResult(
            success=False,
            source=source,
            destination=destination,
            error=str(e)
        )


def move_projects_batch(
    projects: List[str],
    target_dir: str,
    rename_map: Optional[dict] = None
) -> List[MoveResult]:
    """
    Move multiple projects to a target directory.

    Args:
        projects: List of project paths to move
        target_dir: Destination directory
        rename_map: Optional dict mapping source paths to new names

    Returns:
        List of MoveResult for each project
    """
    results = []
    rename_map = rename_map or {}

    for project in projects:
        new_name = rename_map.get(project)
        result = move_project(project, target_dir, new_name)
        results.append(result)

    return results


def consolidate_projects(
    discovered_projects: List[str],
    target_dir: str,
    exclude_dirs: List[str] = None
) -> Tuple[List[str], List[str], List[ProjectConflict]]:
    """
    Consolidate discovered projects into a single directory.

    Args:
        discovered_projects: List of project paths from discovery
        target_dir: Where to consolidate projects
        exclude_dirs: Directories to exclude (e.g., already in target)

    Returns:
        Tuple of (projects_to_move, already_in_target, conflicts)
    """
    target_dir = os.path.abspath(os.path.expanduser(target_dir))
    exclude_dirs = [os.path.abspath(os.path.expanduser(d)) for d in (exclude_dirs or [])]

    # Include target_dir in exclusions
    exclude_dirs.append(target_dir)

    to_move = []
    already_there = []

    for project in discovered_projects:
        project = os.path.abspath(project)
        project_parent = os.path.dirname(project)

        # Check if already in target or excluded
        if project_parent == target_dir:
            already_there.append(project)
        elif any(project.startswith(exc) for exc in exclude_dirs):
            already_there.append(project)
        else:
            to_move.append(project)

    # Check for conflicts among projects to move
    safe, conflicts = check_move_conflicts(to_move, target_dir)

    return safe, already_there, conflicts


def get_project_size(path: str) -> int:
    """Get total size of a project directory in bytes."""
    total = 0
    path = Path(path)

    try:
        for item in path.rglob('*'):
            if item.is_file():
                try:
                    total += item.stat().st_size
                except (OSError, PermissionError):
                    pass
    except (OSError, PermissionError):
        pass

    return total


def format_size(bytes_size: int) -> str:
    """Format bytes as human-readable size."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024
    return f"{bytes_size:.1f} TB"
