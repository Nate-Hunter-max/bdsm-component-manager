HELP_TEXT = '''
==================== HELP =====================
Basic Commands:
  l                            List components (short table)
  a                            Add new component (interactive)
  s [-f FIELD] -v VAL          Search components (default field: name)
  u -id ID -f FIELD -v VAL     Update field of component by ID
  d -id ID [-f]                Delete component by ID (with optional force)

Project Management:
  pj                           List all projects
  np -n NAME -d DESC           Create new project
  dp -id ID                    Delete project by ID
  at -p PID -c CID -q QTY      Add component to project
  rf -p PID -c CID             Remove component from project
  pc -p PID                    View components in project
  cb -p PID                    Check if project can be built
  bp -p PID                    Build project (deduct inventory)

Reports & Utilities:
  lw [-t N]                    List low-stock components (default threshold = 5)
  sm -p PID                    Show project summary
  f                            List all valid component fields
  info -id ID                  Show name, manufacturer, store link for component
  x                            Exit program
==============================================='''

FIELDS = [
    "id", "type", "name", "quantity", "package",
    "comment", "manufacturer", "store_links", "location",
    "tags", "projects"
]
