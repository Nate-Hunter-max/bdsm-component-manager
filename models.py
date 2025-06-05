from dataclasses import dataclass


@dataclass
class Component:
    """
    Dataclass representing an electronic component in inventory.

    Attributes:
        id: Unique identifier (auto-incremented)
        type: Component category (e.g., 'MCU', 'Resistor')
        name: Component name (e.g., 'STM32F401RET6')
        quantity: Current stock count
        package: Physical package (e.g., 'LQFP-64')
        comment: Optional notes
        manufacturer: Optional manufacturer name
        store_links: Optional purchase URLs
        location: Storage location
        tags: Optional comma-separated tags
        projects: Optional associated project tags
    """
    id: int = None
    type: str = ""
    name: str = ""
    quantity: int = 0
    package: str = ""
    comment: str = ""
    manufacturer: str = ""
    store_links: str = ""
    location: str = ""
    tags: str = ""
    projects: str = ""


@dataclass
class Project:
    """
    Dataclass representing a project that uses components.

    Attributes:
        id: Unique identifier
        name: Project name
        description: Project description
        created_at: Timestamp of creation
        status: Project status ('active', 'completed', 'archived')
    """
    id: int = None
    name: str = ""
    description: str = ""
    created_at: str = ""
    status: str = "active"
