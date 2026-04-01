"""
Router scan — QR code pour scanner des documents depuis le telephone du pro.

POST   /scan/{dossier_id}/token         Generer un token de scan temporaire
GET    /scan/{token}                     Page mobile de scan (HTML)
POST   /scan/{token}/upload              Upload photo depuis le telephone
GET    /scan/{token}/status              Statut du token (pour polling desktop)
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.base import get_db
from api.models.dossier import DossierDB

logger = logging.getLogger(__name__)

router = APIRouter()

# Tokens temporaires en memoire (en production → Redis)
# {token: {dossier_id, created_at, expires_at, uploads: [doc_ids]}}
_scan_tokens: dict[str, dict] = {}


@router.post("/{dossier_id}/token")
async def create_scan_token(dossier_id: UUID, db: AsyncSession = Depends(get_db)):
    """Genere un token temporaire pour scanner depuis le telephone."""
    dossier = await db.get(DossierDB, dossier_id)
    if not dossier:
        raise HTTPException(404, "Dossier non trouve")

    token = str(uuid4())[:8]
    _scan_tokens[token] = {
        "dossier_id": str(dossier_id),
        "created_at": datetime.utcnow().isoformat(),
        "expires_at": (datetime.utcnow() + timedelta(minutes=10)).isoformat(),
        "uploads": [],
    }

    return {
        "token": token,
        "expires_in": 600,
        "scan_url": f"/scan/{token}",
    }


@router.get("/{token}", response_class=HTMLResponse)
async def scan_page(token: str):
    """Page mobile de scan — ouvre la camera du telephone."""
    info = _scan_tokens.get(token)
    if not info:
        return HTMLResponse("<h2>Lien expire ou invalide</h2>", status_code=404)

    if datetime.utcnow() > datetime.fromisoformat(info["expires_at"]):
        del _scan_tokens[token]
        return HTMLResponse("<h2>Lien expire</h2>", status_code=410)

    return HTMLResponse(f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AutoDoc Pro — Scanner</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, sans-serif; background: #0f172a; color: white; min-height: 100vh; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 24px; }}
        h1 {{ font-size: 1.3rem; margin-bottom: 8px; }}
        p {{ font-size: 0.85rem; color: #94a3b8; margin-bottom: 24px; text-align: center; }}
        .btn {{ display: block; width: 100%; max-width: 300px; padding: 16px; border-radius: 12px; font-size: 1rem; font-weight: 600; border: none; cursor: pointer; margin-bottom: 12px; text-align: center; }}
        .btn-photo {{ background: #059669; color: white; }}
        .btn-file {{ background: #1e40af; color: white; }}
        .msg {{ margin-top: 16px; padding: 12px; border-radius: 8px; font-size: 0.85rem; text-align: center; max-width: 300px; }}
        .msg-ok {{ background: #d1fae5; color: #065f46; }}
        .msg-err {{ background: #fee2e2; color: #991b1b; }}
        .msg-wait {{ background: #1e293b; color: #94a3b8; }}
        input[type=file] {{ display: none; }}
    </style>
</head>
<body>
    <h1>Scanner un document</h1>
    <p>Prenez en photo ou selectionnez le document a deposer dans le dossier.</p>

    <label class="btn btn-photo" for="camera">Prendre une photo</label>
    <input type="file" id="camera" accept="image/*" capture="environment" />

    <label class="btn btn-file" for="fichier">Choisir un fichier</label>
    <input type="file" id="fichier" accept="image/*,application/pdf" />

    <div id="status"></div>

    <script>
        const token = "{token}";
        const API = window.location.origin;

        async function upload(file) {{
            const status = document.getElementById('status');
            status.innerHTML = '<div class="msg msg-wait">Analyse en cours...</div>';

            const form = new FormData();
            form.append('file', file);

            try {{
                const res = await fetch(API + '/scan/' + token + '/upload', {{ method: 'POST', body: form }});
                const data = await res.json();
                if (res.ok) {{
                    status.innerHTML = '<div class="msg msg-ok">' + (data.type || 'Document') + ' — recu et analyse. Vous pouvez scanner un autre document ou fermer cette page.</div>';
                }} else {{
                    status.innerHTML = '<div class="msg msg-err">' + (data.detail || 'Erreur') + '</div>';
                }}
            }} catch(e) {{
                status.innerHTML = '<div class="msg msg-err">Erreur de connexion</div>';
            }}
        }}

        document.getElementById('camera').addEventListener('change', e => e.target.files[0] && upload(e.target.files[0]));
        document.getElementById('fichier').addEventListener('change', e => e.target.files[0] && upload(e.target.files[0]));
    </script>
</body>
</html>""")


@router.post("/{token}/upload")
async def scan_upload(token: str, file: UploadFile, db: AsyncSession = Depends(get_db)):
    """Upload photo depuis le telephone — passe dans le meme pipeline."""
    info = _scan_tokens.get(token)
    if not info:
        raise HTTPException(404, "Token invalide ou expire")

    if datetime.utcnow() > datetime.fromisoformat(info["expires_at"]):
        del _scan_tokens[token]
        raise HTTPException(410, "Token expire")

    # Appeler le meme endpoint d'upload que d'habitude
    from api.routers.documents import upload_document

    result = await upload_document(
        dossier_id=UUID(info["dossier_id"]),
        file=file,
        source="vendeur",
        captured_by_camera=True,
        db=db,
    )

    info["uploads"].append(result.get("document_id"))

    return {
        "status": "ok",
        "type": result.get("type"),
        "quality": result.get("quality", {}).get("status"),
        "message": result.get("quality", {}).get("message"),
    }


@router.get("/{token}/status")
async def scan_status(token: str):
    """Polling par le desktop pour savoir si des docs ont ete scannes."""
    info = _scan_tokens.get(token)
    if not info:
        return {"active": False, "uploads": []}

    expired = datetime.utcnow() > datetime.fromisoformat(info["expires_at"])
    return {
        "active": not expired,
        "uploads": info.get("uploads", []),
        "count": len(info.get("uploads", [])),
    }
