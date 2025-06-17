import shlex
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from tabulate import tabulate

from database import ComponentInventoryDB
from models import Component
from logic import can_build_project, get_low_stock_components, get_project_summary
from strings import HELP_TEXT, FIELDS


def handle_command(db: ComponentInventoryDB, command: str):
    try:
        tokens = shlex.split(command)
        if not tokens:
            return

        cmd = tokens[0].lower()

        if cmd in ("help", "h"):
            print(HELP_TEXT)

        elif cmd == "f":
            print("Fields:")
            for field in FIELDS:
                print(f"- {field}")

        elif cmd == "l":
            components = db.search_components()
            if components:
                table = [[c.id, c.type, c.name, c.quantity, c.location, c.comment] for c in components]
                headers = ["ID", "Type", "Name", "Qty", "Location", "Comment"]
                print(tabulate(table, headers=headers, tablefmt="github"))
            else:
                print("No components found.")

        elif cmd == "a":
            comp = Component(
                type=input("Type: "),
                name=input("Name: "),
                quantity=int(input("Quantity: ")),
                location=input("Location: "),
                package=input("Package: "),
                comment=input("Comment: "),
                manufacturer=input("Manufacturer: "),
                store_links=input("Store links: "),
                tags=input("Tags: "),
                projects=input("Projects: ")
            )
            cid = db.add_component(comp)
            print(f"Component added with ID: {cid}")

        elif cmd == "s":
            args = parse_args(tokens[1:])
            field = args.get("-f", "name")
            value = args.get("-v")
            if value:
                components = db.search_components(**{field: value})
                if components:
                    table = [[
                        c.id, c.type, c.name, c.quantity, c.package,
                        c.comment, c.location, c.tags,
                        c.projects
                    ] for c in components]
                    headers = ["ID", "Type", "Name", "Qty", "Package", "Comment", "Location", "Tags", "Projects"]
                    print(tabulate(table, headers=headers, tablefmt="github"))
                else:
                    print("No results.")
            else:
                print("Please specify search value with -v")

        elif cmd == "info":
            args = parse_args(tokens[1:])
            cid = int(args.get("-id"))
            c = db.get_component(cid)
            if c:
                table = [[c.name, c.manufacturer, c.store_links]]
                headers = ["Name", "Manufacturer", "Store Links"]
                print(tabulate(table, headers=headers, tablefmt="github"))
            else:
                print("Component not found.")

        elif cmd == "u":
            args = parse_args(tokens[1:])
            comp_id = int(args.get("-id"))
            field = args.get("-f")
            value = args.get("-v")
            component = db.get_component(comp_id)
            if component and hasattr(component, field):
                setattr(component, field, type(getattr(component, field))(value))
                if db.update_component(component):
                    print("Updated.")
                else:
                    print("Update failed.")
            else:
                print("Invalid ID or field.")

        elif cmd == "d":
            args = parse_args(tokens[1:])
            comp_id = int(args.get("-id"))
            force = "-f" in args
            cursor = db.conn.execute(
                "SELECT p.id, p.name FROM project_components pc JOIN projects p ON "
                "pc.project_id = p.id WHERE pc.component_id = ?",
                (comp_id,))
            used_in = cursor.fetchall()
            if used_in and not force:
                print("Used in:")
                for pid, name in used_in:
                    print(f"- [{pid}] {name}")
                confirm = input("Remove from all and delete? [y/N]: ").strip().lower()
                if confirm != 'y':
                    print("Cancelled.")
                    return
            db.conn.execute("DELETE FROM project_components WHERE component_id = ?", (comp_id,))
            db.conn.execute("UPDATE components SET projects = '' WHERE id = ?", (comp_id,))
            db.conn.commit()
            cursor = db.conn.execute("DELETE FROM components WHERE id = ?", (comp_id,))
            db.conn.commit()
            print("Deleted." if cursor.rowcount else "Not found.")

        elif cmd == "pj":
            cur = db.conn.execute("SELECT id, name, status FROM projects")
            rows = cur.fetchall()
            if rows:
                print(tabulate(rows, headers=["ID", "Name", "Status"], tablefmt="github"))
            else:
                print("No projects found.")

        elif cmd == "np":
            args = parse_args(tokens[1:])
            pid = db.create_project(args.get("-n", "Unnamed"), args.get("-d", ""))
            print(f"Created project ID: {pid}")

        elif cmd == "dp":
            args = parse_args(tokens[1:])
            pid = int(args.get("-id"))
            confirm = input(f"Delete project {pid}? [y/N]: ").strip().lower()
            if confirm == 'y':
                db.conn.execute("DELETE FROM projects WHERE id = ?", (pid,))
                db.conn.commit()
                print("Deleted.")
            else:
                print("Cancelled.")

        elif cmd == "at":
            args = parse_args(tokens[1:])
            db.add_component_to_project(int(args["-p"]), int(args["-c"]), int(args["-q"]))
            print("Added.")

        elif cmd == "rf":
            args = parse_args(tokens[1:])
            db.remove_component_from_project(int(args["-p"]), int(args["-c"]))
            print("Removed.")

        elif cmd == "pc":
            args = parse_args(tokens[1:])
            comps = db.get_project_components(int(args["-p"]))
            if comps:
                table = [[c['id'], c['name'], c['required'], c['available']] for c in comps]
                headers = ["ID", "Component", "Required", "Available"]
                print(tabulate(table, headers=headers, tablefmt="github"))
            else:
                print("No components in project.")

        elif cmd == "cb":
            args = parse_args(tokens[1:])
            ok, missing = can_build_project(db, int(args["-p"]))
            if ok:
                print("Build is possible.")
            else:
                print("Missing:")
                for m in missing:
                    print(f"- {m}")

        elif cmd == "bp":
            args = parse_args(tokens[1:])
            try:
                if db.build_project(int(args["-p"])):
                    print("Built.")
            except ValueError as e:
                print(f"Error: {str(e)}")

        elif cmd == "lw":
            args = parse_args(tokens[1:])
            threshold = int(args.get("-t", 5))
            components = get_low_stock_components(db, threshold)
            if components:
                table = [[
                    c['id'], c['type'], c['name'], c['quantity'], c['location'], c['comment']
                ] for c in components]
                headers = ["ID", "Type", "Name", "Qty", "Location", "Comment"]
                print(tabulate(table, headers=headers, tablefmt="github"))
            else:
                print("No low-stock components found.")

        elif cmd == "sm":
            args = parse_args(tokens[1:])
            summary = get_project_summary(db, int(args["-p"]))
            if summary:
                print(f"Project: {summary['name']} | Status: {summary['status']}")
                for c in summary['components']:
                    print(f"- {c['name']} ({c['required']} req, {c['available']} in stock)")

        elif cmd == "x":
            print("Exiting.")
            return "exit"

        else:
            print("Unknown command. Type 'h' for help.")

    except Exception as e:
        print(f"Error: {str(e)}")


def parse_args(tokens: list) -> dict:
    args = {}
    i = 0
    while i < len(tokens):
        if tokens[i].startswith("-") and not tokens[i].startswith("--") and i + 1 < len(tokens):
            args[tokens[i]] = tokens[i + 1]
            i += 2
        else:
            args[tokens[i]] = True
            i += 1
    return args


def repl():
    session = PromptSession(history=InMemoryHistory())
    print("Component Inventory Shell. Type 'h' for help.")
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
