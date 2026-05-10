#!/usr/bin/env bash
# Ejecuta un comando arbitrario dentro del contenedor odoo (doodba).
#
# Uso:
#   docker_exec.sh -- ls /opt/odoo/auto/addons
#   docker_exec.sh -- pip list
#   docker_exec.sh --interactive -- bash    # SHELL interactivo (-t)
set -euo pipefail

if [[ -z "${DOODBA_SSH_HOST:-}" ]]; then
    echo "error: DOODBA_SSH_HOST no esta seteado." >&2
    exit 2
fi
if [[ -z "${DOODBA_PROJECT_DIR:-}" ]]; then
    echo "error: DOODBA_PROJECT_DIR no esta seteado." >&2
    exit 2
fi

INTERACTIVE=""
if [[ "${1:-}" == "--interactive" ]]; then
    INTERACTIVE="-t"
    shift
fi
if [[ "${1:-}" != "--" ]]; then
    echo "uso: $(basename "$0") [--interactive] -- <cmd...>" >&2
    exit 2
fi
shift

SERVICE="${DOODBA_COMPOSE_SERVICE:-odoo}"
REMOTE_CMD="cd $DOODBA_PROJECT_DIR && docker compose exec -T $SERVICE $*"
if [[ -n "$INTERACTIVE" ]]; then
    REMOTE_CMD="cd $DOODBA_PROJECT_DIR && docker compose exec $SERVICE $*"
fi

ssh -o BatchMode=yes $INTERACTIVE "$DOODBA_SSH_HOST" "$REMOTE_CMD"
