#!/usr/bin/env bash
# Reinicia el servicio odoo del compose (doodba).
# Pide confirmacion textual antes de actuar; pasar --yes para skipear.
set -euo pipefail

if [[ -z "${DOODBA_SSH_HOST:-}" ]]; then
    echo "error: DOODBA_SSH_HOST no esta seteado." >&2
    exit 2
fi
if [[ -z "${DOODBA_PROJECT_DIR:-}" ]]; then
    echo "error: DOODBA_PROJECT_DIR no esta seteado." >&2
    exit 2
fi

SERVICE="${DOODBA_COMPOSE_SERVICE:-odoo}"

if [[ "${1:-}" != "--yes" ]]; then
    echo "Vas a reiniciar el servicio '$SERVICE' en $DOODBA_SSH_HOST."
    echo "Esto interrumpe sesiones HTTP activas durante ~5-15 segundos."
    read -p "Continuar? (escribe 'yes'): " resp
    [[ "$resp" == "yes" ]] || { echo "abortado." >&2; exit 1; }
fi

ssh -o BatchMode=yes "$DOODBA_SSH_HOST" \
    "cd $DOODBA_PROJECT_DIR && docker compose restart $SERVICE"
