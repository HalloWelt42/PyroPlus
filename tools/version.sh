#!/usr/bin/env bash
# Zentrale Versionierung: version.json ist die einzige Quelle.
# Aufruf: tools/version.sh [patch|minor|major|id|check|show]
#   patch  : 5.0.0 -> 5.0.1, neue Build-Kennung
#   minor  : 5.0.1 -> 5.1.0, neue Build-Kennung
#   major  : 5.1.0 -> 6.0.0, neue Build-Kennung
#   id     : nur neue Build-Kennung
#   check  : prüft, ob die Spiegel (frontend/package.json) der Quelle entsprechen
#   show   : gibt die volle Version aus
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
QUELLE="$ROOT/version.json"
SPIEGEL_PAKET="$ROOT/frontend/package.json"

lese_version() { python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['version'])" "$QUELLE"; }
lese_paket_version() { python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['version'])" "$SPIEGEL_PAKET"; }

neue_id() { openssl rand -hex 3; }

schreibe() {
  local version="$1" kennung="$2"
  python3 - "$QUELLE" "$version" "$kennung" <<'PY'
import json, sys
pfad, version, kennung = sys.argv[1:4]
json.dump({"version": version, "id": kennung, "voll": f"v{version}-{kennung}"},
          open(pfad, "w"), indent=2)
open(pfad, "a").write("\n")
PY
  python3 - "$SPIEGEL_PAKET" "$version" <<'PY'
import json, sys
pfad, version = sys.argv[1:3]
daten = json.load(open(pfad))
daten["version"] = version
json.dump(daten, open(pfad, "w"), indent=2, ensure_ascii=False)
open(pfad, "a").write("\n")
PY
}

erhoehe() {
  local art="$1" aktuell major minor patch
  aktuell="$(lese_version)"
  IFS=. read -r major minor patch <<<"$aktuell"
  case "$art" in
    patch) patch=$((patch + 1)) ;;
    minor) minor=$((minor + 1)); patch=0 ;;
    major) major=$((major + 1)); minor=0; patch=0 ;;
    *) echo "Unbekannte Art: $art" >&2; exit 2 ;;
  esac
  echo "$major.$minor.$patch"
}

case "${1:-show}" in
  patch|minor|major)
    neu="$(erhoehe "$1")"
    schreibe "$neu" "$(neue_id)"
    echo "Version: $(lese_version) ($(python3 -c "import json;print(json.load(open('$QUELLE'))['voll'])"))"
    ;;
  id)
    schreibe "$(lese_version)" "$(neue_id)"
    echo "Neue Kennung: $(python3 -c "import json;print(json.load(open('$QUELLE'))['voll'])")"
    ;;
  check)
    q="$(lese_version)"; p="$(lese_paket_version)"
    if [ "$q" != "$p" ]; then
      echo "Versionsdrift: version.json=$q, frontend/package.json=$p" >&2
      exit 1
    fi
    echo "Version konsistent: $q"
    ;;
  show)
    python3 -c "import json;print(json.load(open('$QUELLE'))['voll'])"
    ;;
  *)
    echo "Aufruf: $0 [patch|minor|major|id|check|show]" >&2
    exit 2
    ;;
esac
