# Guide d'installation — Module Healio Chatbot pour Odoo 15

## Prérequis

- Odoo 15 installé et fonctionnel
- Ton backend FastAPI `STAGEE` accessible sur le réseau
- Python 3.8+ dans l'environnement Odoo

---

## Configuration locale validée

Pour ton setup actuel, garde seulement ces ports :

| Service | URL à ouvrir/configurer | Rôle |
|---------|--------------------------|------|
| Odoo Docker | `http://127.0.0.1:8069` | Interface Odoo dans le navigateur |
| FastAPI STAGEE | `http://127.0.0.1:8000` | Backend lancé sur Windows |
| FastAPI vu depuis Odoo Docker | `http://192.168.1.32:8000` | URL à mettre dans la configuration Odoo |
| Ollama GPU via tunnel SSH | `http://127.0.0.1:11435` | Qwen3 Coder appelé par FastAPI |

Ne configure pas `localhost:3000`, `host.docker.internal:8000`, ni l'Ollama local
`127.0.0.1:11434` pour ce setup : ton LLM est sur l'instance GPU via le tunnel SSH.

---

## Étape 1 — Préparer le backend FastAPI

### 1.1 Mettre à jour le CORS dans ton `.env`

Ouvre `STAGEE/.env` et ajoute l'URL de ton Odoo dans `API_CORS_ORIGINS` :

```
API_CORS_ORIGINS=http://localhost:8069,http://127.0.0.1:8069
```

### 1.2 Connecter Ollama sur l'instance GPU

Ouvre un tunnel SSH depuis ta machine locale vers l'instance GPU :

```powershell
ssh -L 11435:127.0.0.1:11434 ubuntu@141.94.168.93
```

Garde cette fenêtre ouverte pendant tes tests. Ensuite, configure `STAGEE/.env` :

```env
LLM_PROVIDER=openai_compatible
OPENAI_BASE_URL=http://127.0.0.1:11435/v1
OPENAI_API_KEY=ollama
OPENAI_CHAT_MODEL=qwen3-coder-next:q8_0
```

Remplace `OPENAI_CHAT_MODEL` par le nom exact retourné par :

```powershell
curl http://127.0.0.1:11435/api/tags
```

### 1.3 Démarrer le FastAPI

```powershell
# Dans le dossier STAGEE
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

> ⚠️ Utilise `--host 0.0.0.0` pour que le FastAPI soit accessible depuis Odoo
> si les deux ne sont pas sur le même processus.

### 1.4 Vérifier que l'API répond

```powershell
curl http://localhost:8000/health
# Doit retourner : {"status": "ok", ...}
```

---

## Étape 2 — Installer le module Odoo

### 2.1 Copier le module dans les addons Odoo

Copie le dossier `STAGEE/odoo_module/healio_chatbot/` dans ton dossier `addons` Odoo.

**Exemples selon ton installation :**

```powershell
# Windows (Odoo installé dans C:\odoo15)
Copy-Item -Recurse "C:\Users\swale\OneDrive\Desktop\STAGEE\odoo_module\healio_chatbot" "C:\odoo15\addons\"

# Linux / Mac
cp -r /chemin/vers/STAGEE/odoo_module/healio_chatbot /opt/odoo/addons/
```

Résultat attendu :

```
C:\odoo15\addons\healio_chatbot\
├── __manifest__.py
├── __init__.py
├── controllers/
├── models/
├── security/
├── static/
└── views/
```

### 2.2 Mettre à jour la liste des addons dans Odoo

1. Connecte-toi à Odoo en tant qu'administrateur
2. Va dans **Paramètres** → active le **mode développeur** (URL : `/web?debug=1`)
3. Dans le menu **Paramètres** → **Apps** → **Mettre à jour la liste des apps**
4. Recherche **"Healio"** dans la liste des apps
5. Clique sur **Installer**

### 2.3 (Alternatif) Installer via la ligne de commande

```bash
# Linux
python odoo-bin -d nom_de_ta_base -i healio_chatbot --stop-after-init

# Windows
python odoo-bin -d nom_de_ta_base -i healio_chatbot --stop-after-init
```

---

## Étape 3 — Configurer le module dans Odoo

1. Dans Odoo, va dans **Assistant IA Healio** → **⚙️ Configuration**
2. Renseigne :
   - **URL du backend FastAPI** : `http://192.168.1.32:8000`
   - **Clé API** : laisse vide si tu n'en as pas configuré
   - **Timeout** : 60 secondes (par défaut)
3. Laisse **Utiliser l'iframe Next.js** décoché pour utiliser le widget Odoo natif.
4. Clique sur **🔌 Tester la connexion** pour vérifier

---

## Étape 4 — Gérer les droits d'accès

### Groupes disponibles

| Groupe | Permissions |
|--------|-------------|
| **Utilisateur Chatbot** | Peut poser des questions, voir ses propres sessions |
| **Administrateur Chatbot** | Tout ce qui précède + configuration, historique complet |

### Ajouter un utilisateur à un groupe

1. **Paramètres** → **Utilisateurs et entreprises** → **Utilisateurs**
2. Cliquer sur un utilisateur
3. Dans l'onglet **Accès** → section **Healio** → choisir le rôle

---

## Étape 5 — Vérification

1. **Menu visible** : dans Odoo, le menu **Assistant IA Healio** apparaît
2. **Chat fonctionnel** : poser "Combien de patients ?" → réponse reçue
3. **Cypher visible** : cliquer sur "🔍 Requête Cypher générée" sous la réponse
4. **Résultats** : cliquer sur "📊 Résultats bruts" pour voir les données Neo4j
5. **Historique** : menu **📋 Historique des sessions** → la session est sauvegardée
6. **Restriction rôles** : un utilisateur sans groupe ne voit pas le menu

---

## Structure du module

```
healio_chatbot/
├── __manifest__.py              Déclaration Odoo (nom, version, dépendances)
├── __init__.py                  Import Python
├── controllers/
│   └── main.py                  Routes HTTP Odoo :
│                                  POST /healio/chat    → proxy FastAPI
│                                  GET  /healio/session → session active
│                                  GET  /healio/config/ui → config UI
│                                  GET  /healio/health  → test connexion
├── models/
│   ├── healio_config.py         Modèle config (URL, clé API, timeout)
│   └── healio_chat_session.py   Modèle session (historique JSON, stats)
├── security/
│   ├── groups.xml               Groupes : user / admin
│   └── ir.model.access.csv      Droits lecture/écriture par groupe
├── static/src/
│   ├── js/chatbot_widget.js     Widget OWL : iframe ou chat natif
│   └── css/chatbot.css          Styles du chatbot
└── views/
    ├── menu.xml                 Structure des menus
    ├── healio_config_view.xml   Formulaire de configuration
    └── healio_chat_view.xml     Vue chat + historique + recherche
```

---

## Dépannage

### Le menu n'apparaît pas
→ Vérifie que l'utilisateur appartient au groupe **Utilisateur Chatbot**

### "Impossible de joindre le backend"
→ Vérifie que le FastAPI est démarré avec `--host 0.0.0.0`
→ Vérifie l'URL dans la configuration Odoo
→ Vérifie que le port 8000 n'est pas bloqué par un firewall

### Erreur CORS dans la console navigateur
→ Ajoute l'URL de ton Odoo dans `API_CORS_ORIGINS` dans le `.env` FastAPI
→ Redémarre le FastAPI après modification

### Le module ne s'installe pas
→ Vérifie que le dossier est bien dans le chemin `addons_path` de Odoo
→ Consulte les logs Odoo : `odoo.log` ou la console
