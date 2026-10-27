# -*- coding: utf-8 -*-
{
    "name": "Healia AI Chatbot",
    "version": "15.0.1.0.0",
    "summary": "Intégration de l'agent GraphRAG IA dans Odoo",
    "description": """
        Ce module intègre le chatbot GraphRAG Healia dans Odoo 15.
        Il permet aux utilisateurs de poser des questions en langage naturel
        sur les données de santé stockées dans Neo4j, directement depuis Odoo.

        Fonctionnalités :
        - Menu dédié « Assistant IA Healia »
        - Interface de chat (iframe Next.js ou widget natif)
        - Historique des sessions en base de données Odoo
        - Contrôle d'accès par groupes (utilisateur / administrateur)
        - Proxy sécurisé vers le backend FastAPI
    """,
    "category": "Tools",
    "author": "Healia",
    "website": "",
    "license": "LGPL-3",
    "depends": ["base", "web", "mail"],
    "data": [
        "security/groups.xml",
        "security/ir.model.access.csv",
        "views/healio_config_view.xml",
        "views/healio_chat_view.xml",
        "views/menu.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "healio_chatbot/static/src/css/chatbot.css",
            "healio_chatbot/static/src/js/chatbot_widget.js",
        ],
    },
    "images": ["static/description/icon.png"],
    "installable": True,
    "application": True,
    "auto_install": False,
}
