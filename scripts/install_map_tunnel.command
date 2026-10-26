#!/bin/zsh
# The end user downloads ngrok directly; no agent, token or account is redistributed.
set -eu
APP_PATH="${1:-${0:A:h}/Native Adventure Map.app}"
# Reviewed official stable arm64 download: ngrok 3.39.13, 2026-10-26.
EXPECTED_SHA=686c32f1d6aff864eb2f221dedc97302d7b1cf863c6b71e57eb8010d65284321
DOWNLOAD_URL=https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-darwin-arm64.zip
if [[ ! -d "$APP_PATH" || "$(/usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' "$APP_PATH/Contents/Info.plist")" != local.totk.native-map ]]; then
  print -u2 'Place this script beside Native Adventure Map.app, or pass the App path.'
  exit 1
fi
TARGET="$APP_PATH/Contents/Resources/tunnel-agent/ngrok"
if [[ -e "$TARGET" ]]; then
  if [[ "$(/usr/bin/shasum -a 256 "$TARGET" | /usr/bin/awk '{print $1}')" == "$EXPECTED_SHA" ]]; then
    print 'The pinned agent is already installed.'
    exit 0
  fi
  print -u2 'An unrecognized agent already exists; nothing was overwritten.'
  exit 1
fi
TASK_DIR="$(/usr/bin/mktemp -d "${TMPDIR:-/private/tmp}/nak-tunnel.XXXXXX")"
trap '/bin/rm -rf "$TASK_DIR"' EXIT
/usr/bin/curl --fail --location --proto '=https' --tlsv1.2 "$DOWNLOAD_URL" --output "$TASK_DIR/agent.zip"
/usr/bin/unzip -p "$TASK_DIR/agent.zip" ngrok > "$TASK_DIR/ngrok"
if [[ "$(/usr/bin/shasum -a 256 "$TASK_DIR/ngrok" | /usr/bin/awk '{print $1}')" != "$EXPECTED_SHA" ]]; then
  print -u2 'Official download differs from the pinned version. Installation stopped; request a reviewed update.'
  exit 1
fi
/bin/mkdir -p "${TARGET:h}"
/usr/bin/install -m 755 "$TASK_DIR/ngrok" "$TARGET"
"$TARGET" credits > "${TARGET:h}/CREDITS.txt"
/usr/bin/codesign --force --deep --sign - "$APP_PATH"
/usr/bin/codesign --verify --deep --strict "$APP_PATH"
print 'Installed and locally signed. No tunnel was started; enter your own account in the App.'
