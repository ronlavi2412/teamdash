Publish an obfuscated version of the dashboard to GitHub Pages. Engineer names are replaced with Ninja Turtles aliases to protect privacy.

IMPORTANT: Never modify `data.json` or `config.json` — work only on copies.

## Alias list

These fictional aliases are assigned to engineers by index (engineer[0] gets alias[0], etc.):

| Index | Alias | Username |
|-------|-------|----------|
| 0 | Leonardo | leo_katana |
| 1 | Donatello | donnie_bo |
| 2 | Raphael | raph_sai |
| 3 | Michelangelo | mikey_chuck |
| 4 | Splinter | splinter_sensei |
| 5 | April O'Neil | april_reporter |
| 6 | Casey Jones | casey_bat |

If the team has more than 7 engineers, extend with: Bebop, Rocksteady, Shredder, Krang, Baxter Stockman, Leatherhead, Slash (with matching themed usernames).

## Step 1: Copy data

```
cp data.json data-obfuscated.json
```

If `data.json` doesn't exist, tell the user to run `/generate` first and stop.

## Step 2: Obfuscate names

Run the following Python script. It reads `config.json` to discover real names/usernames and builds the replacement mapping dynamically:

```python
python3 << 'PYEOF'
import json

ALIASES = [
    {"name": "Leonardo", "username": "leo_katana"},
    {"name": "Donatello", "username": "donnie_bo"},
    {"name": "Raphael", "username": "raph_sai"},
    {"name": "Michelangelo", "username": "mikey_chuck"},
    {"name": "Splinter", "username": "splinter_sensei"},
    {"name": "April O'Neil", "username": "april_reporter"},
    {"name": "Casey Jones", "username": "casey_bat"},
    {"name": "Bebop", "username": "bebop_warthog"},
    {"name": "Rocksteady", "username": "rocksteady_rhino"},
    {"name": "Shredder", "username": "shredder_blade"},
]

with open('config.json') as f:
    config = json.load(f)

engineers = config['engineers']
if len(engineers) > len(ALIASES):
    raise ValueError(f"Too many engineers ({len(engineers)}) for available aliases ({len(ALIASES)})")

# Build replacement maps from config
name_map = {}
first_name_map = {}
username_map = {}

for i, eng in enumerate(engineers):
    alias = ALIASES[i]
    real_name = eng['name']
    name_map[real_name] = alias['name']
    first_name = real_name.split()[0]
    alias_first = alias['name'].split()[0]
    first_name_map[first_name] = alias_first
    if 'github' in eng:
        username_map[eng['github']] = alias['username']
    if 'gitlab' in eng:
        username_map[eng['gitlab']] = alias['username']

with open('data-obfuscated.json') as f:
    raw = f.read()

# Replace full names first (before first names to avoid partial matches)
for real, turtle in name_map.items():
    raw = raw.replace(real, turtle)

for real, turtle in first_name_map.items():
    raw = raw.replace(real, turtle)

for real, obf in username_map.items():
    raw = raw.replace(real, obf)

with open('data-obfuscated.json', 'w') as f:
    f.write(raw)

print("Obfuscation complete")
PYEOF
```

## Step 3: Generate obfuscated dashboard

```
python3 -m teamdash generate data-obfuscated.json -o dashboard-obfuscated.html
```

## Step 4: Verify no leaks

Build a grep pattern dynamically from `config.json` and check both output files:

```python
python3 << 'PYEOF'
import json, subprocess

with open('config.json') as f:
    config = json.load(f)

tokens = set()
for eng in config['engineers']:
    for part in eng['name'].split():
        tokens.add(part)
    if 'github' in eng:
        tokens.add(eng['github'])
    if 'gitlab' in eng:
        tokens.add(eng['gitlab'])

pattern = r'\|'.join(sorted(tokens, key=len, reverse=True))
result = subprocess.run(
    ['grep', '-c', pattern, 'dashboard-obfuscated.html', 'data-obfuscated.json'],
    capture_output=True, text=True
)
print(result.stdout)
lines = result.stdout.strip().split('\n')
all_zero = all(line.endswith(':0') for line in lines if line)
print('LEAK CHECK: PASS' if all_zero else 'LEAK CHECK: FAIL — investigate before publishing')
PYEOF
```

If the check fails, investigate and fix before publishing.

## Step 5: Publish to gh-pages

```bash
git worktree add /tmp/teamdash-ghpages gh-pages
cp dashboard-obfuscated.html /tmp/teamdash-ghpages/index.html
cd /tmp/teamdash-ghpages && git add index.html && git commit -m "Update obfuscated dashboard"
cd /tmp/teamdash-ghpages && git push origin gh-pages
```

Then clean up:

```bash
git worktree remove /tmp/teamdash-ghpages
```

## Step 6: Done

Tell the user the obfuscated dashboard is published at https://ronlavi2412.github.io/teamdash/

The artifacts `data-obfuscated.json` and `dashboard-obfuscated.html` are kept locally for inspection.
