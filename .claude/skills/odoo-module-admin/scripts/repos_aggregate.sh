#!/usr/bin/env bash
# Ejecuta `gitaggregate -c custom/src/repos.yaml` en el host doodba.
# Por defecto en modo --dry-run; pasar 'apply' como primer argumento para
# ejecutar de verdad.
#
# Requiere DOODBA_SSH_HOST y DOODBA_PROJECT_DIR.
set -euo pipefail

MODE="${1:-dry-run}"

if [[ -z "${DOODBA_SSH_HOST:-}" ]]; then
    echo "error: DOODBA_SSH_HOST no esta seteado." >&2
    exit 2
fi
if [[ -z "${DOODBA_PROJECT_DIR:-}" ]]; then
    echo "error: DOODBA_PROJECT_DIR no esta seteado." >&2
    exit 2
fi

REPOS_YAML="custom/src/repos.yaml"

case "$MODE" in
    dry-run)
        # Plan: muestra que haria sin tocar (gitaggregate parsea + reporta)
        ssh -o BatchMode=yes "$DOODBA_SSH_HOST" \
            "cd $DOODBA_PROJECT_DIR && \
             gitaggregate -c $REPOS_YAML --show-closed-prs"
        ;;
    apply)
        ssh -o BatchMode=yes "$DOODBA_SSH_HOST" \
            "cd $DOODBA_PROJECT_DIR && \
             gitaggregate -c $REPOS_YAML"
        ;;
    *)
        echo "uso: $(basename "$0") [dry-run|apply]" >&2
        exit 2
        ;;
esac
