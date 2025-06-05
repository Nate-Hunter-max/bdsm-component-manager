import shlex
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from database import ComponentInventoryDB
from models import Component
from logic import can_build_project, get_low_stock_components, get_project_summary

# Available component fields
COMPONENT_FIELDS = [
    "id", "type", "name", "quantity", "package",
    "comment", "manufacturer", "store_links", "location",
    "tags", "projects"
]


def handle_command(db: ComponentInventoryDB, command: str):
    try:
        tokens = shlex.split(command)
        if not tokens:
            return

        cmd = tokens[0].lower()

        if cmd in ("help", "h"):
            print("""Available commands:
  list
  add --type TYPE --name NAME --quantity QTY --location LOC [...]
  search --field FIELD --value VALUE
  update --id CID --field FIELD --value VALUE
  delete --id CID [--force]
  projects
  new-project --name NAME --desc DESC
  del-project --id PID
  add-to --project PID --component CID --qty QTY
  remove-from --project PID --component CID
  components --project PID
  check --project PID
  build --project PID
  low [--threshold N]
  summary --project PID
  fields - show valid component fields
  exit""")

        elif cmd == "fields":
            print("Available component fields:")
            for field in COMPONENT_FIELDS:
                print(f"- {field}")

        elif cmd == "list":
            for c in db.search_components():
                print(f"[{c.id}] {c.name} | {c.type} | Qty: {c.quantity} | Loc: {c.location}")

        elif cmd == "add":
            args = parse_args(tokens[1:])
            comp = Component(
                type=args.get("--type", ""),
                name=args.get("--name", ""),
                quantity=int(args.get("--quantity", 0)),
                package=args.get("--package", ""),
                comment=args.get("--comment", ""),
                manufacturer=args.get("--manufacturer", ""),
                store_links=args.get("--store_links", ""),
                location=args.get("--location", ""),
                tags=args.get("--tags", ""),
                projects=args.get("--projects", "")
            )
            cid = db.add_component(comp)
            print(f"Component added with ID: {cid}")

        elif cmd == "search":
            args = parse_args(tokens[1:])
            field = args.get("--field")
            value = args.get("--value")
            if field and value:
                for c in db.search_components(**{field: value}):
                    print(f"[{c.id}] {c.name} | {c.type} | Qty: {c.quantity} | Loc: {c.location}")

        elif cmd == "update":
            args = parse_args(tokens[1:])
            comp_id = int(args.get("--id"))
            field = args.get("--field")
            value = args.get("--value")
            component = db.get_component(comp_id)
            if component and hasattr(component, field):
                attr_type = type(getattr(component, field))
                setattr(component, field, attr_type(value))
                if db.update_component(component):
                    print("Component updated.")
                else:
                    print("Update failed.")
            else:
                print("Invalid component ID or field.")

        elif cmd == "delete":
            args = parse_args(tokens[1:])
            comp_id = int(args.get("--id"))
            force = "--force" in args
            cursor = db.conn.execute(
                "SELECT p.id, p.name FROM project_components pc JOIN projects p ON pc.project_id = p.id WHERE pc.component_id = ?",
                (comp_id,))
            used_in = cursor.fetchall()
            if used_in and not force:
                print("Component is used in the following projects:")
                for pid, name in used_in:
                    print(f"- [{pid}] {name}")
                confirm = input("Remove component from all projects and delete it? [y/N]: ").strip().lower()
                if confirm != 'y':
                    print("Cancelled.")
                    return
            db.conn.execute("DELETE FROM project_components WHERE component_id = ?", (comp_id,))
            db.conn.execute("UPDATE components SET projects = '' WHERE id = ?", (comp_id,))
            db.conn.commit()
            cursor = db.conn.execute("DELETE FROM components WHERE id = ?", (comp_id,))
            db.conn.commit()
            if cursor.rowcount > 0:
                print("Component deleted.")
            else:
                print("Component not found.")

        elif cmd == "projects":
            cur = db.conn.execute("SELECT id, name, status FROM projects")
            for row in cur.fetchall():
                print(f"[{row[0]}] {row[1]} | Status: {row[2]}")

        elif cmd == "new-project":
            args = parse_args(tokens[1:])
            pid = db.create_project(args.get("--name", "Unnamed"), args.get("--desc", ""))
            print(f"Project created with ID: {pid}")

        elif cmd == "del-project":
            args = parse_args(tokens[1:])
            project_id = int(args.get("--id"))
            confirm = input(f"Are you sure you want to delete project {project_id}? [y/N]: ").strip().lower()
            if confirm == 'y':
                db.conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
                db.conn.commit()
                print("Project deleted.")
            else:
                print("Cancelled.")

        elif cmd == "add-to":
            args = parse_args(tokens[1:])
            db.add_component_to_project(int(args["--project"]), int(args["--component"]), int(args["--qty"]))
            print("Component added to project.")

        elif cmd == "remove-from":
            args = parse_args(tokens[1:])
            db.remove_component_from_project(int(args["--project"]), int(args["--component"]))
            print("Component removed from project.")

        elif cmd == "components":
            args = parse_args(tokens[1:])
            comps = db.get_project_components(int(args["--project"]))
            for c in comps:
                print(f"{c['name']} | Required: {c['required']} | Available: {c['available']}")

        elif cmd == "check":
            args = parse_args(tokens[1:])
            can_build, missing = can_build_project(db, int(args["--project"]))
            if can_build:
                print("Build possible: all components are available.")
            else:
                print("Missing components:")
                for m in missing:
                    print(f"- {m}")

        elif cmd == "build":
            args = parse_args(tokens[1:])
            try:
                if db.build_project(int(args["--project"])):
                    print("Project built successfully.")
            except ValueError as e:
                print(f"Error: {str(e)}")

        elif cmd == "low":
            args = parse_args(tokens[1:])
            threshold = int(args.get("--threshold", 5))
            for c in get_low_stock_components(db, threshold):
                print(f"{c['name']} | Qty: {c['quantity']} | Type: {c['type']}")

        elif cmd == "summary":
            args = parse_args(tokens[1:])
            summary = get_project_summary(db, int(args["--project"]))
            if summary:
                print(f"Project: {summary['name']} | Status: {summary['status']}")
                for c in summary['components']:
                    print(f"- {c['name']} ({c['required']} req, {c['available']} in stock)")

        elif cmd == "exit":
            print("Exiting.")
            return "exit"

        else:
            print("Unknown command. Type 'help' for list of commands.")

    except Exception as e:
        print(f"Error: {str(e)}")


def parse_args(tokens: list) -> dict:
    args = {}
    i = 0
    while i < len(tokens):
        if tokens[i].startswith("--") and i + 1 < len(tokens):
            args[tokens[i]] = tokens[i + 1]
            i += 2
        else:
            args[tokens[i]] = True
            i += 1
    return args


def repl():
    session = PromptSession(history=InMemoryHistory())
    print("Component Inventory Command Shell. Type 'help' to begin.")
    with ComponentInventoryDB() as db:
        while True:
            try:
                lines = session.prompt(">>> ").strip().splitlines()
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    if handle_command(db, line) == "exit":
                        return
            except KeyboardInterrupt:
                continue
            except EOFError:
                break


if __name__ == "__main__":
    repl()
