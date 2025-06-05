import sqlite3
from typing import List, Dict, Optional, Any

from models import Component, Project


class ComponentInventoryDB:
    """
    SQLite database handler for electronic components inventory with project management.

    Provides full CRUD operations for both components and projects,
    including project assembly functionality that automatically updates inventory.
    """

    def __init__(self, db_path: str = "inventory.db"):
        """
        Initialize database connection and create tables if they don't exist.

        Args:
            db_path: Path to SQLite database file
        """
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign key constraints
        self._create_tables()

    def _create_tables(self) -> None:
        """Create all required tables with proper schema and constraints."""
        # Components table
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS components (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            name TEXT NOT NULL,
            quantity INTEGER NOT NULL CHECK(quantity >= 0),
            package TEXT DEFAULT '',
            comment TEXT DEFAULT '',
            manufacturer TEXT DEFAULT '',
            store_links TEXT DEFAULT '',
            location TEXT NOT NULL,
            tags TEXT DEFAULT '',
            projects TEXT DEFAULT '',
            UNIQUE(type, name, package)
        )
        """)

        # Projects table
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'active' CHECK(status IN ('active', 'completed', 'archived'))
            )
        """)

        # Project-components junction table
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS project_components (
            project_id INTEGER NOT NULL,
            component_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL CHECK(quantity > 0),
            PRIMARY KEY (project_id, component_id),
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
            FOREIGN KEY (component_id) REFERENCES components(id) ON DELETE RESTRICT
        )
        """)

        # Create indexes for better performance
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_components_type ON components(type)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_components_location ON components(location)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_project_components ON project_components(project_id)")

        self.conn.commit()

    # ===== COMPONENT OPERATIONS =====
    def add_component(self, component: Component) -> int:
        """
        Add a new component to inventory, or update quantity if duplicate.

        Args:
            component: Component object to add

        Returns:
            ID of the existing or newly inserted component
        """
        cursor = self.conn.cursor()

        # Check for existing component with same type, name, package
        cursor.execute(
            "SELECT id, quantity FROM components WHERE type = ? AND name = ? AND package = ?",
            (component.type, component.name, component.package)
        )
        existing = cursor.fetchone()

        if existing:
            # Update quantity instead of inserting duplicate
            existing_id, existing_qty = existing
            new_qty = existing_qty + component.quantity
            cursor.execute(
                "UPDATE components SET quantity = ? WHERE id = ?",
                (new_qty, existing_id)
            )
            self.conn.commit()
            return existing_id
        else:
            # Safe to insert new component
            query = """
            INSERT INTO components (
                type, name, quantity, package, comment, 
                manufacturer, store_links, location, tags, projects
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            params = (
                component.type, component.name, component.quantity, component.package,
                component.comment, component.manufacturer, component.store_links,
                component.location, component.tags, component.projects
            )
            cursor.execute(query, params)
            self.conn.commit()
            return cursor.lastrowid

    def get_component(self, component_id: int) -> Optional[Component]:
        """Retrieve a component by its ID."""
        cursor = self.conn.execute("SELECT * FROM components WHERE id = ?", (component_id,))
        row = cursor.fetchone()
        return Component(*row) if row else None

    def update_component(self, component: Component) -> bool:
        """
        Update an existing component.

        Args:
            component: Component with updated values (must have valid id)

        Returns:
            True if update was successful, False if component not found
        """
        query = """
        UPDATE components SET 
            type = ?, name = ?, quantity = ?, package = ?, comment = ?,
            manufacturer = ?, store_links = ?, location = ?, tags = ?, projects = ?
        WHERE id = ?
        """
        params = (
            component.type, component.name, component.quantity, component.package,
            component.comment, component.manufacturer, component.store_links,
            component.location, component.tags, component.projects, component.id
        )
        cursor = self.conn.execute(query, params)
        self.conn.commit()
        return cursor.rowcount > 0

    def delete_component(self, component_id: int) -> bool:
        """
        Delete a component only if it's not used in any project.

        Returns:
            True if deleted, False if used or not found
        """
        cursor = self.conn.cursor()

        # Check if component is used
        cursor.execute("SELECT 1 FROM project_components WHERE component_id = ? LIMIT 1", (component_id,))
        if cursor.fetchone():
            raise ValueError("Component is used in a project and cannot be deleted.")

        cursor.execute("DELETE FROM components WHERE id = ?", (component_id,))
        self.conn.commit()

        return cursor.rowcount > 0

    def search_components(self, **filters) -> List[Component]:
        """
        Search components with flexible filtering.

        Args:
            filters: Key-value pairs for filtering (e.g., type='MCU', quantity=10)

        Returns:
            List of matching Component objects
        """
        if not filters:
            query = "SELECT * FROM components"
            params = ()
        else:
            conditions = []
            params = []
            for field, value in filters.items():
                if field == 'tags' or field == 'projects':
                    conditions.append(f"{field} LIKE ?")
                    params.append(f"%{value}%")
                elif isinstance(value, str):
                    conditions.append(f"{field} LIKE ?")
                    params.append(f"%{value}%")
                else:
                    conditions.append(f"{field} = ?")
                    params.append(value)
            query = f"SELECT * FROM components WHERE {' AND '.join(conditions)}"

        cursor = self.conn.execute(query, params)
        return [Component(*row) for row in cursor.fetchall()]

    # ===== PROJECT OPERATIONS =====
    def create_project(self, name: str, description: str = "") -> int:
        """
        Create a new project. If project with the same name exists, return its ID.

        Args:
            name: Project name (must be unique)
            description: Optional project description

        Returns:
            ID of the created or existing project
        """
        cursor = self.conn.cursor()

        # Check for existing project
        cursor.execute("SELECT id FROM projects WHERE name = ?", (name,))
        existing = cursor.fetchone()
        if existing:
            return existing[0]  # Return existing project ID

        # Insert new project
        cursor.execute(
            "INSERT INTO projects (name, description) VALUES (?, ?)",
            (name, description)
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_project(self, project_id: int) -> Optional[Project]:
        """Retrieve a project by its ID."""
        cursor = self.conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        row = cursor.fetchone()
        return Project(*row) if row else None

    def add_component_to_project(self, project_id: int, component_id: int, quantity: int) -> bool:
        """
        Add a component to a project with specified quantity.

        Args:
            project_id: Target project ID
            component_id: Component to add
            quantity: Required quantity

        Returns:
            True if successful, False if component already exists in project

        Raises:
            ValueError: If component doesn't exist or quantity is invalid
        """
        # Verify component exists
        if not self.get_component(component_id):
            raise ValueError(f"Component ID {component_id} doesn't exist")

        if quantity <= 0:
            raise ValueError("Quantity must be positive")

        try:
            # Add or update component in project
            cursor = self.conn.cursor()
            cursor.execute(
                """INSERT OR REPLACE INTO project_components 
                (project_id, component_id, quantity) 
                VALUES (?, ?, ?)""",
                (project_id, component_id, quantity)
            )

            # Add project tag to component if not already present
            project_tag = f"proj_{project_id}"
            cursor.execute(
                """UPDATE components 
                SET projects = TRIM(COALESCE(projects, '') || ' ' || ?)
                WHERE id = ? AND COALESCE(projects, '') NOT LIKE '%' || ? || '%'""",
                (project_tag, component_id, project_tag)
            )

            self.conn.commit()
            return True

        except sqlite3.IntegrityError:
            self.conn.rollback()
            return False

    def remove_component_from_project(self, project_id: int, component_id: int) -> bool:
        """
        Remove a component from a project.

        Args:
            project_id: Project ID
            component_id: Component to remove

        Returns:
            True if removed, False if component wasn't in project
        """
        cursor = self.conn.cursor()

        # First remove the project tag from component
        project_tag = f"proj_{project_id}"
        cursor.execute(
            """UPDATE components 
            SET projects = TRIM(REPLACE(' ' || COALESCE(projects, '') || ' ', ' ' || ? || ' ', ' '))
            WHERE id = ? AND COALESCE(projects, '') LIKE '%' || ? || '%'""",
            (project_tag, component_id, project_tag)
        )

        # Then delete from project_components
        cursor.execute(
            "DELETE FROM project_components WHERE project_id = ? AND component_id = ?",
            (project_id, component_id)
        )

        self.conn.commit()
        return cursor.rowcount > 0

    def get_project_components(self, project_id: int) -> List[Dict[str, Any]]:
        """
        Get all components in a project with detailed information.

        Args:
            project_id: Project ID

        Returns:
            List of dictionaries with component details and project-specific quantity
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """SELECT c.id, c.type, c.name, pc.quantity as required, 
            c.quantity as available, c.package, c.location
            FROM project_components pc
            JOIN components c ON pc.component_id = c.id
            WHERE pc.project_id = ?""",
            (project_id,)
        )

        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def build_project(self, project_id: int) -> bool:
        """
        Finalize project by deducting used components from inventory.

        Args:
            project_id: Project to build

        Returns:
            True if successful, False if project doesn't exist

        Raises:
            ValueError: If insufficient components available
        """
        # Verify project exists
        if not self.get_project(project_id):
            return False

        try:
            cursor = self.conn.cursor()

            # 1. Check all components have sufficient quantity
            components = self.get_project_components(project_id)
            for comp in components:
                if comp['available'] < comp['required']:
                    raise ValueError(
                        f"Insufficient quantity for {comp['name']} "
                        f"(needed: {comp['required']}, available: {comp['available']})"
                    )

            # 2. Deduct quantities
            for comp in components:
                cursor.execute(
                    "UPDATE components SET quantity = quantity - ? WHERE id = ?",
                    (comp['required'], comp['id'])
                )

            # 3. Mark project as completed
            cursor.execute(
                "UPDATE projects SET status = 'completed' WHERE id = ?",
                (project_id,)
            )

            self.conn.commit()
            return True

        except sqlite3.Error:
            self.conn.rollback()
            raise

    def close(self) -> None:
        """Close the database connection."""
        self.conn.close()

    def __enter__(self):
        """Support context manager protocol."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Ensure connection is closed when exiting context."""
        self.close()
