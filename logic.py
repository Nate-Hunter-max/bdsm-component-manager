from typing import List, Tuple, Dict
from database import ComponentInventoryDB


def can_build_project(db: ComponentInventoryDB, project_id: int) -> Tuple[bool, List[str]]:
    """
    Check if the project can be assembled with current inventory.

    Args:
        db: Instance of ComponentInventoryDB
        project_id: ID of the project to check

    Returns:
        Tuple where:
            - First value is True if all components are sufficient, False otherwise
            - Second value is a list of missing components or empty if all are available
    """
    missing = []
    components = db.get_project_components(project_id)

    for comp in components:
        if comp['available'] < comp['required']:
            missing.append(
                f"{comp['name']} (needed: {comp['required']}, available: {comp['available']})"
            )

    return len(missing) == 0, missing


def get_low_stock_components(db: ComponentInventoryDB, threshold: int = 5) -> List[Dict[str, any]]:
    """
    Retrieve a list of components that are below the stock threshold.

    Args:
        db: Instance of ComponentInventoryDB
        threshold: Minimum quantity to consider as low stock

    Returns:
        List of dictionaries representing components with low stock
    """
    components = db.search_components()
    return [comp.__dict__ for comp in components if comp.quantity < threshold]


def get_project_summary(db: ComponentInventoryDB, project_id: int) -> Dict[str, any]:
    """
    Generate a summary of a project: name, status, and components involved.

    Args:
        db: Instance of ComponentInventoryDB
        project_id: ID of the project

    Returns:
        Dictionary with project info and component breakdown
    """
    project = db.get_project(project_id)
    if not project:
        return {}

    components = db.get_project_components(project_id)
    return {
        "id": project.id,
        "name": project.name,
        "status": project.status,
        "components": components
    }
