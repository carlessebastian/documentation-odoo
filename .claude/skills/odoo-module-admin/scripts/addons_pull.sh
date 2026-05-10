#!/usr/bin/env bash
# Reconstruye la imagen Odoo y los symlinks auto/addons (doodba).
# Tras `gitaggregate`, hay que regenerar para que los nuevos modulos
# aparezcan dentro del contenedor.
#
# Equivalente a `invoke img-build` desde el host.
set -euo pipefail

if [[ -z "${DOODBA_SSH_HOST:-}" ]]; then
    echo "error: DOODBA_SSH_HOST no esta seteado." >&2
    exit 2
fi
if [[ -z "${DOODBA_PROJECT_DIR:-}" ]]; then
    echo "error: DOODBA_PROJECT_DIR no esta seteado." >&2
    exit 2
fi

ssh -o BatchMode=yes "$DOODBA_SSH_HOST" \
    "cd $DOODBA_PROJECT_DIR && \
     (invoke img-build || docker compose build odoo)"
