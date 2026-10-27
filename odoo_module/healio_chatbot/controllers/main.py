# -*- coding: utf-8 -*-
"""
Contrôleurs HTTP Odoo pour le chatbot Healia.

Routes exposées :
  POST /healio/chat              → proxy vers FastAPI /chat
  GET  /healio/sessions          → proxy vers FastAPI /sessions/
  GET  /healio/sessions/{id}     → proxy vers FastAPI /sessions/{id}
  GET  /healio/session           → récupère ou crée la session de l'utilisateur courant
  GET  /healio/config/ui         → retourne la config UI (URL iframe, session_id, etc.)
  GET  /healio/health            → transmet le résultat du /health FastAPI
"""
import json
import logging
import urllib.error
import urllib.request

from odoo import http
from odoo.http import request, Response

_logger = logging.getLogger(__name__)


def _require_auth():
    """Retourne l'utilisateur courant ou lève une 401."""
    if not request.session or not request.session.uid:
        return None, Response(
            json.dumps({"error": "Authentification Odoo requise."}),
            status=401,
            content_type="application/json",
        )
    return request.env.user, None


def _json_response(data, status=200):
    return Response(
        json.dumps(data, default=str, ensure_ascii=False),
        status=status,
        content_type="application/json",
    )


def _proxy_get(path, config):
    """
    Effectue une requête GET vers le FastAPI à travers le proxy Odoo.
    Retourne (data_dict, status_code).
    """
    url = f"{config.fastapi_url.rstrip('/')}{path}"
    try:
        req = urllib.request.Request(url, method="GET")
        if config.fastapi_api_key:
            req.add_header("Authorization", f"Bearer {config.fastapi_api_key}")
        with urllib.request.urlopen(req, timeout=config.request_timeout or 30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return body, resp.status
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        _logger.error("FastAPI HTTP error %s: %s", exc.code, error_body)
        return {"error": error_body}, exc.code
    except urllib.error.URLError as exc:
        _logger.error("FastAPI connection error: %s", exc.reason)
        return {"error": f"Impossible de joindre le backend: {exc.reason}"}, 502


class HealioController(http.Controller):

    # ── Proxy chat ────────────────────────────────────────────────────────────

    @http.route("/healio/chat", type="http", auth="user", methods=["POST"], csrf=False)
    def chat(self, **kwargs):
        """
        Point d'entrée proxy pour le chat.
        Reçoit un JSON {'message': '...', 'session_id': '...'} depuis le frontend Odoo,
        le transmet au FastAPI, et retourne la réponse.
        """
        user, err = _require_auth()
        if err:
            return err

        try:
            body = json.loads(request.httprequest.data or "{}")
        except Exception:
            return _json_response({"error": "Corps JSON invalide."}, status=400)

        message = (body.get("message") or "").strip()
        if not message:
            return _json_response({"error": "Le champ 'message' est requis."}, status=400)

        # Récupérer ou créer la session Odoo de l'utilisateur
        session_model = request.env["healio.chat.session"]
        session = session_model.get_or_create_session()

        try:
            data = session.send_message(message)
        except Exception as exc:
            _logger.exception("Healia proxy error")
            return _json_response({"error": str(exc)}, status=502)

        return _json_response(data)

    # ── Infos de session ──────────────────────────────────────────────────────

    @http.route("/healio/session", type="http", auth="user", methods=["GET"], csrf=False)
    def get_session(self, **kwargs):
        """Retourne les métadonnées de la session active de l'utilisateur."""
        user, err = _require_auth()
        if err:
            return err

        session = request.env["healio.chat.session"].get_or_create_session()
        return _json_response(
            {
                "odoo_session_id": session.id,
                "fastapi_session_id": session.fastapi_session_id or None,
                "message_count": session.message_count,
                "last_message_at": session.last_message_at,
                "history": session.get_history(),
            }
        )

    # ── Proxy sessions (liste + détail) ──────────────────────────────────────

    @http.route("/healio/sessions", type="http", auth="user", methods=["GET"], csrf=False)
    def list_sessions(self, **kwargs):
        """Proxy GET /sessions/ vers le FastAPI."""
        user, err = _require_auth()
        if err:
            return err
        config = request.env["healio.config"].get_config()
        data, status = _proxy_get("/sessions/", config)
        return _json_response(data, status)

    @http.route("/healio/sessions/<path:session_id>", type="http", auth="user", methods=["GET"], csrf=False)
    def get_session_detail(self, session_id, **kwargs):
        """Proxy GET /sessions/{id} vers le FastAPI."""
        user, err = _require_auth()
        if err:
            return err
        config = request.env["healio.config"].get_config()
        data, status = _proxy_get(f"/sessions/{session_id}", config)
        return _json_response(data, status)

    # ── Configuration UI ─────────────────────────────────────────────────────

    @http.route("/healio/session/link", type="http", auth="user", methods=["POST"], csrf=False)
    def link_session(self, **kwargs):
        """Lie un fastapi_session_id à la session Odoo de l'utilisateur courant."""
        user, err = _require_auth()
        if err:
            return err
        try:
            body = json.loads(request.httprequest.data or "{}")
        except Exception:
            return _json_response({"error": "Corps JSON invalide."}, status=400)
        fastapi_session_id = (body.get("fastapi_session_id") or "").strip()
        if not fastapi_session_id:
            return _json_response({"error": "fastapi_session_id requis."}, status=400)
        odoo_session = request.env["healio.chat.session"].get_or_create_session()
        odoo_session.write({"fastapi_session_id": fastapi_session_id})
        return _json_response({"status": "ok", "odoo_session_id": odoo_session.id})

    @http.route("/healio/config/ui", type="http", auth="user", methods=["GET"], csrf=False)
    def get_ui_config(self, **kwargs):
        """
        Retourne la configuration nécessaire au widget JS Odoo :
        URL iframe (si activée), session_id actif, URL du proxy, statut de connexion.
        """
        user, err = _require_auth()
        if err:
            return err

        config = request.env["healio.config"].get_config()

        # Récupérer la session active de l'utilisateur Odoo
        odoo_session = request.env["healio.chat.session"].get_or_create_session()

        is_admin = request.env.user.has_group("healio_chatbot.group_healio_admin")

        return _json_response(
            {
                "use_iframe": config.use_iframe,
                "frontend_url": config.frontend_url or None,
                "fastapi_url": config.fastapi_url,
                "active_session_id": odoo_session.fastapi_session_id or None,
                "health_status": config.health_status,
                "is_admin": is_admin,
                "user_name": request.env.user.name or "",
                "user_email": request.env.user.partner_id.email or "",
                "user_id": str(request.env.uid) or "",
            }
        )

    # ── Health check passthrough ──────────────────────────────────────────────

    @http.route("/healio/health", type="http", auth="user", methods=["GET"], csrf=False)
    def health(self, **kwargs):
        """Teste la connexion vers le backend FastAPI et retourne son statut."""
        user, err = _require_auth()
        if err:
            return err

        config = request.env["healio.config"].get_config()

        import urllib.request as ureq
        import urllib.error as uerr

        url = f"{config.fastapi_url.rstrip('/')}/health"
        try:
            req = ureq.Request(url, method="GET")
            if config.fastapi_api_key:
                req.add_header("Authorization", f"Bearer {config.fastapi_api_key}")
            with ureq.urlopen(req, timeout=10) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                return _json_response({"status": "ok", "backend": body})
        except uerr.HTTPError as exc:
            return _json_response(
                {"status": "error", "code": exc.code, "reason": str(exc.reason)},
                status=502,
            )
        except Exception as exc:
            return _json_response(
                {"status": "error", "reason": str(exc)},
                status=502,
            )
