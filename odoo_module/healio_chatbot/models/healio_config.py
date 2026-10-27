# -*- coding: utf-8 -*-
"""
Modèle de configuration du chatbot Healia.
Stocke l'URL du backend FastAPI et les paramètres de connexion.
Ce modèle est un singleton (un seul enregistrement par instance Odoo).
"""
import logging

from odoo import api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class HealioConfig(models.Model):
    """Configuration globale de l'intégration Healia FastAPI."""

    _name = "healio.config"
    _description = "Configuration du chatbot IA Healia"
    _rec_name = "fastapi_url"

    # ── Connexion FastAPI ────────────────────────────────────────────────────
    fastapi_url = fields.Char(
        string="URL du backend FastAPI",
        required=True,
        default="http://localhost:8000",
        help="URL de base du serveur FastAPI Healia (ex : http://192.168.1.10:8000).",
    )
    fastapi_api_key = fields.Char(
        string="Clé API (optionnel)",
        help="Si ton FastAPI exige un header Authorization, renseigne-le ici.",
    )
    request_timeout = fields.Integer(
        string="Timeout (secondes)",
        default=60,
        help="Délai maximum d'attente pour une réponse du backend.",
    )

    # ── Interface ────────────────────────────────────────────────────────────
    frontend_url = fields.Char(
        string="URL du frontend Next.js (optionnel)",
        help=(
            "Si renseignée, l'interface principale affichera cette URL dans une iframe. "
            "Ex : http://192.168.1.10:3000"
        ),
    )
    use_iframe = fields.Boolean(
        string="Utiliser l'iframe Next.js",
        default=False,
        help="Cochez pour intégrer ton frontend Next.js au lieu du widget Odoo natif.",
    )

    # ── Statut ───────────────────────────────────────────────────────────────
    last_health_check = fields.Datetime(
        string="Dernier test de connexion", readonly=True
    )
    health_status = fields.Selection(
        selection=[("ok", "✅ Connecté"), ("error", "❌ Erreur"), ("unknown", "⚠️ Inconnu")],
        string="État",
        default="unknown",
        readonly=True,
    )

    @api.constrains("fastapi_url")
    def _check_fastapi_url(self):
        for record in self:
            url = (record.fastapi_url or "").strip()
            if not url.startswith(("http://", "https://")):
                raise ValidationError(
                    "L'URL du backend FastAPI doit commencer par http:// ou https://"
                )

    def action_test_connection(self):
        """Teste la connexion vers le FastAPI via /health."""
        import urllib.request
        import urllib.error

        self.ensure_one()
        url = f"{self.fastapi_url.rstrip('/')}/health"
        try:
            req = urllib.request.Request(url, method="GET")
            if self.fastapi_api_key:
                req.add_header("Authorization", f"Bearer {self.fastapi_api_key}")
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    self.write(
                        {
                            "health_status": "ok",
                            "last_health_check": fields.Datetime.now(),
                        }
                    )
                    return {
                        "type": "ir.actions.client",
                        "tag": "display_notification",
                        "params": {
                            "title": "Connexion réussie",
                            "message": f"Le backend Healia répond sur {url}.",
                            "type": "success",
                        },
                    }
        except Exception as exc:
            _logger.warning("Healia health check failed: %s", exc)
            self.write(
                {
                    "health_status": "error",
                    "last_health_check": fields.Datetime.now(),
                }
            )
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Connexion échouée",
                    "message": f"Impossible de joindre {url} : {exc}",
                    "type": "danger",
                },
            }

    @api.model
    def get_config(self):
        """Retourne le premier enregistrement de configuration (singleton)."""
        config = self.search([], limit=1)
        if not config:
            config = self.create({"fastapi_url": "http://localhost:8000"})
        return config
