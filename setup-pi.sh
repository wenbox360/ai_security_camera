#!/usr/bin/env bash

# Configure a Pi device without writing credentials into tracked source files.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/pi/.env"
DEFAULT_API_URL="http://localhost:8000"

if command -v jq >/dev/null 2>&1 && [[ -f "$SCRIPT_DIR/cloud/aws-config.json" ]]; then
  ALB_DNS="$(jq -r '.alb_dns // empty' "$SCRIPT_DIR/cloud/aws-config.json")"
  if [[ -n "$ALB_DNS" ]]; then
    DEFAULT_API_URL="http://$ALB_DNS"
  fi
fi

echo "Configure edge-to-cloud communication"
read -r -p "Cloud API URL [$DEFAULT_API_URL]: " CLOUD_API_URL
CLOUD_API_URL="${CLOUD_API_URL:-$DEFAULT_API_URL}"

read -r -p "Device ID [pi_device_001]: " DEVICE_ID
DEVICE_ID="${DEVICE_ID:-pi_device_001}"

read -r -s -p "Device API key: " DEVICE_API_KEY
echo
if [[ -z "$DEVICE_API_KEY" ]]; then
  echo "Device API key is required." >&2
  exit 1
fi

umask 077
{
  printf 'CLOUD_API_URL=%s\n' "$CLOUD_API_URL"
  printf 'DEVICE_ID=%s\n' "$DEVICE_ID"
  printf 'DEVICE_API_KEY=%s\n' "$DEVICE_API_KEY"
} > "$ENV_FILE"
chmod 600 "$ENV_FILE"

echo "Wrote private configuration to pi/.env."
echo "Run: python3 -m pi.setup_cloud --test"
