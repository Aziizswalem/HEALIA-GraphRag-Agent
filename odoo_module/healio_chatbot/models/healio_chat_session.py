# -*- coding: utf-8 -*-
"""
Modèle de session de chat Healia.
Chaque session correspond à une conversation entre un utilisateur Odoo
et le chatbot GraphRAG. Les messages sont échangés avec le backend FastAPI.
"""
import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class HealioChatSession(models.Model):
    """Session de conversation avec l'agent GraphRAG Healia."""

    _name = "healio.chat.session"
    _description = "Session de chat IA Healia"
    _order = "create_date desc"
    _rec_name = "display_name"

    # ── Identité ─────────────────────────────────────────────────────────────
    user_id = fields.Many2one(
        "res.users",
        string="Utilisateur",
        default=lambda self: self.env.user,
        required=True,
        ondelete="cascade",
        index=True,
    )
    fastapi_session_id = fields.Char(
        string="ID de session FastAPI",
        readonly=True,
        index=True,
        help="Identifiant de session généré par le backend FastAPI.",
    )
    display_name = fields.Char(
        string="Nom de la session",
        compute="_compute_display_name",
        store=True,
    )

    # ── Statistiques ─────────────────────────────────────────────────────────
    message_count = fields.Integer(
        string="Messages échangés", default=0, readonly=True
    )
    last_message_at = fields.Datetime(string="Dernier message", readonly=True)
    last_question = fields.Text(string="Dernière question", readonly=True)
    last_answer = fields.Text(string="Dernière réponse", readonly=True)

    # ── Historique JSON ───────────────────────────────────────────────────────
    history_json = fields.Text(
        string="Historique JSON",
        default="[]",
        help="Stockage JSON des échanges de la session.",
    )

    @api.depends("user_id", "create_date")
    def _compute_display_name(self):
        for record in self:
            user_name = record.user_id.name or "Inconnu"
            date_str = ""
            if record.create_date:
                date_str = record.create_date.strftime("%d/%m/%Y %H:%M")
            record.display_name = f"[{date_str}] {user_name}"

    # ── Méthodes publiques ────────────────────────────────────────────────────

    @api.model
    def get_or_create_session(self):
        """
        Retourne la session active de l'utilisateur courant,
        ou en crée une nouvelle si aucune n'existe dans les 24 dernières heures.
        """
        from datetime import timedelta

        cutoff = fields.Datetime.now() - timedelta(hours=24)
        existing = self.search(
            [
                ("user_id", "=", self.env.uid),
                ("create_date", ">=", cutoff),
            ],
            limit=1,
        )
        if existing:
            return existing
        return self.create({"user_id": self.env.uid})

    def send_message(self, message: str) -> dict:
        """
        Envoie un message au backend FastAPI et retourne la réponse.
        Met à jour les statistiques de la session.

        :param message: Question en langage naturel de l'utilisateur.
        :returns: dict avec 'answer', 'cypher', 'session_id', 'results', etc.
        :raises UserError: En cas d'erreur de connexion ou de réponse invalide.
        """
        self.ensure_one()
        config = self.env["healio.config"].get_config()

        payload = json.dumps(
            {
                "message": message,
                "session_id": self.fastapi_session_id or None,
            }
        ).encode("utf-8")

        url = f"{config.fastapi_url.rstrip('/')}/chat"
        req = urllib.request.Request(
            url,
            data=payload,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        if config.fastapi_api_key:
            req.add_header("Authorization", f"Bearer {config.fastapi_api_key}")

        try:
            with urllib.request.urlopen(
                req, timeout=config.request_timeout or 60
            ) as resp:
                raw = resp.read().decode("utf-8")
                data = json.loads(raw)
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            _logger.error("FastAPI HTTP error %s: %s", exc.code, error_body)
            raise UserError(
                f"Le backend Healia a retourné une erreur {exc.code}.\n{error_body}"
            ) from exc
        except urllib.error.URLError as exc:
            _logger.error("FastAPI connection error: %s", exc.reason)
            raise UserError(
                f"Impossible de joindre le backend Healia à {url}.\n"
                f"Vérifiez que le serveur FastAPI est démarré et accessible.\n"
                f"Détail : {exc.reason}"
            ) from exc
        except Exception as exc:
            _logger.exception("Unexpected error calling FastAPI")
            raise UserError(f"Erreur inattendue : {exc}") from exc

        # Mettre à jour la session avec l'ID FastAPI si nouveau
        fastapi_sid = data.get("session_id") or self.fastapi_session_id
        answer = data.get("answer") or ""

        # Ajouter l'échange dans l'historique JSON
        history = json.loads(self.history_json or "[]")
        history.append(
            {
                "role": "user",
                "content": message,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
        history.append(
            {
                "role": "assistant",
                "content": answer,
                "cypher": data.get("cypher") or "",
                "results": data.get("results") or [],
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        self.write(
            {
                "fastapi_session_id": fastapi_sid,
                "message_count": self.message_count + 1,
                "last_message_at": fields.Datetime.now(),
                "last_question": message,
                "last_answer": answer,
                "history_json": json.dumps(history, ensure_ascii=False),
            }
        )

        return data

    def get_history(self) -> list:
        """Retourne l'historique de la session sous forme de liste de dicts."""
        self.ensure_one()
        try:
            return json.loads(self.history_json or "[]")
        except json.JSONDecodeError:
            return []

    def action_clear_session(self):
        """Réinitialise la session (efface l'historique local et l'ID FastAPI)."""
        self.ensure_one()
        self.write(
            {
                "fastapi_session_id": False,
                "message_count": 0,
                "last_message_at": False,
                "last_question": False,
                "last_answer": False,
                "history_json": "[]",
            }
        )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Session réinitialisée",
                "message": "L'historique de cette session a été effacé.",
                "type": "info",
            },
        }
