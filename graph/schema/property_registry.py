"""
graph/schema/property_registry.py — Semantic annotations for every node property.

NODE_PROPERTY_REGISTRY maps each Neo4j node label to its properties with
business-meaning descriptions.  Used by format_property_registry() to inject
a compact semantic block into the Cypher prompt, eliminating LLM hallucinations
about property placement.

See also:
  - format_property_registry() — renders the registry as a prompt block
  - static_schema.py — DOMAIN_TOPOLOGY, FULL_SCHEMA
"""
from __future__ import annotations


NODE_PROPERTY_REGISTRY: dict[str, dict] = {
    "Assure": {
        "desc": "Assuré (personne couverte par le contrat)",
        "props": {
            "id":                "INTEGER — Identifiant interne",
            "first_name":        "STRING — Prénom de l'assuré",
            "last_name":         "STRING — Nom de famille de l'assuré",
            "gender":            "STRING — Genre : 'female' ou 'male'",
            "num_famille":       "STRING — Numéro de famille",
            "date_radiation":    "DATE — Date de radiation (null si actif)",
            "situation":         "STRING — Situation familiale : 'M' (marié) ou 'C' (célibataire)",
            "handicape":       "BOOLEAN — Personne handicapée",
            "malade_chron":      "BOOLEAN — Malade chronique",
            "malade_grave":      "BOOLEAN — Malade grave",
            "is_carence":        "BOOLEAN — Soumis à délai de carence",
            "is_circoncision":   "BOOLEAN — Circoncision prise en charge",
            "is_couple":         "BOOLEAN — Couvert en tant que couple",
            "is_had_activ_contra": "BOOLEAN — Activité contraceptive",
            "is_radiated":       "BOOLEAN — Radié (true = plus actif)",
        },
    },
    "Assureur": {
        "desc": "Compagnie d'assurance (ex: Star, BH, Maghrebia, COMAR, El Amana Takaful)",
        "props": {
            "id":                  "INTEGER — Identifiant interne",
            "name":                "STRING — Nom commercial — utiliser toLower + CONTAINS pour filtrer",
            "email":               "STRING — Email de contact",
            "phone":               "STRING — Numéro de téléphone",
            "phone_sanitized":     "STRING — Téléphone nettoyé (format international)",
            "city":                "STRING — Ville du siège",
            "street":              "STRING — Adresse du siège",
            "street2":             "STRING — Complément d'adresse",
            "zip":                 "STRING — Code postal",
            "state_id":            "INTEGER — ID état/gouvernorat (FK)",
            "societe_id":          "INTEGER — ID société (FK)",
            "has_carte_soins_virt":"BOOLEAN — Carte de soins virtuelle active",
        },
    },
    "Beneficiaire": {
        "desc": "Bénéficiaire / ayant-droit (personne à charge de l'assuré : enfant ou conjoint)",
        "props": {
            "id":                "INTEGER — Identifiant interne",
            "first_name":        "STRING — Prénom du bénéficiaire",
            "last_name":         "STRING — Nom du bénéficiaire",
            "gender":            "STRING — Genre : 'male' ou 'female'",
            "lien":              "STRING — Lien avec l'assuré : 'child' (enfant) ou 'conjoint'",
            "date_naissance":    "DATE — Date de naissance",
            "date_mariage":      "DATE — Date de mariage (si conjoint)",
            "num_famille":       "STRING — Numéro de famille",
            "active":            "BOOLEAN — Actif (true) ou radié (false)",
            "handicaperé":       "BOOLEAN — Personne handicapée",
            "chomage":           "BOOLEAN — Au chômage",
            "malade_chron":      "BOOLEAN — Malade chronique",
            "malade_grave":      "BOOLEAN — Malade grave",
            "is_carence":        "BOOLEAN — Soumis à délai de carence",
            "is_circoncision":   "BOOLEAN — Circoncision prise en charge",
            "is_radiated":       "BOOLEAN — Radié (true = plus actif)",
            "assure_id":         "INTEGER — ID de l'assuré principal (FK)",
            "partner_id":        "INTEGER — ID partenaire (FK)",
            "company_partner_id":"INTEGER — ID partenaire entreprise (FK)",
        },
    },
    "Bordereau": {
        "desc": "Bordereau d'envoi (lot de BS transmis à l'assureur)",
        "props": {
            "id":             "STRING — Identifiant unique du bordereau (ex: 'STD_840')",
            "name":           "STRING — Nom / référence complète",
            "type":           "STRING — Type de bordereau (ex: 'STD')",
            "sequence":       "STRING — Séquence / numéro de lot",
            "year":           "INTEGER — Année du bordereau",
            "date_bordereau": "DATE — Date d'émission du bordereau",
            "date_limit_cv":  "INTEGER — Date limite de contrôle de validation (0 = pas de limite)",
            "active":         "BOOLEAN — Bordereau actif",
            "is_bord_client": "BOOLEAN — Bordereau créé par le client",
            "reject_day":     "INTEGER — Nombre de jours de rejet",
            "offer_id":       "INTEGER — ID de l'offre associée (FK)",
            "company_id":     "INTEGER — ID de l'entreprise cliente (FK)",
        },
    },
    "BulletinSoin": {
        "desc": "FEUILLE DE SOIN — acte médical déposé par l'assuré (noeud central des requêtes)",
        "props": {
            "id":               "INTEGER — Identifiant interne",
            "num_bs":           "STRING — Numéro unique du bulletin de soin",
            "state":            "STRING — État : 'refunded' (remboursé), 'draft', 'validated', 'paid', 'rejected'",
            "total_dep":        "FLOAT — MONTANT TOTAL DÉCLARÉ — utiliser pour 'montant', 'dépense', 'déclaré'",
            "total_pec":        "FLOAT — MONTANT TOTAL PRIS EN CHARGE — utiliser pour 'PEC', 'prise en charge'",
            "total_cnam":       "FLOAT — Part remboursée par la CNAM (sécurité sociale)",
            "validation_date":  "DATE — Date de validation du BS",
            "prestataire":      "STRING — Nom du prestataire de soin",
            "malade_id":        "INTEGER — ID du patient (FK)",
            "offer_id":         "INTEGER — ID de l'offre (FK)",
            "gestionnaire_id":  "INTEGER — ID du gestionnaire (FK)",
            "is_bs_client":     "BOOLEAN — BS créé par le client",
            "is_bs_update":     "BOOLEAN — BS mis à jour",
            "is_cv":            "BOOLEAN — Soumis à contrôle de validation",
            "is_cv_confirm":    "BOOLEAN — CV confirmé",
            "is_from_network":  "BOOLEAN — Provient du réseau de soin",
            "is_from_portail":  "BOOLEAN — Déclaré via le portail",
        },
    },
    "BulletinSoinPrestation": {
        "desc": "PRESTATION — ligne d'acte dans un BS (une consultation/examen = une prestation)",
        "props": {
            "id":               "INTEGER — Identifiant interne",
            "date_prestation":  "DATE — Date de la prestation / acte",
            "discipline":       "STRING — Discipline médicale : 'labo', 'doc', 'pharma', 'radio'",
            "montant_depense":  "FLOAT — Montant dépensé pour cette prestation (utiliser sur BSP, PAS sur BS)",
            "montant_pec":      "FLOAT — Montant pris en charge pour cette prestation",
            "part_patient":     "FLOAT — Part restant à charge du patient",
            "reste_plafond_b":  "FLOAT — Reste à charge plafond prestation (technique)",
            "prestation_tpa":   "INTEGER — Type de prestation TPA (0 = non TPA)",
            "state_prestation": "STRING — État : 'draft' (brouillon), 'validated', 'paid'",
            "active":           "BOOLEAN — Prestation active",
            "is_prest_network": "BOOLEAN — Prestation issue du réseau de soin",
            "is_prest_tpa":     "BOOLEAN — Prestation traitée via TPA",
            "bs_id":            "INTEGER — ID du BS parent (FK)",
        },
    },
    "BulletinSoinPrestationDetail": {
        "desc": "DÉTAIL DE PRESTATION — ligne de remboursement unitaire (produit, acte, médicament, soin)",
        "props": {
            "id":                "INTEGER — Identifiant interne",
            "date_creation":     "DATETIME — Date de création de la ligne",
            "discipline":        "STRING — Discipline : 'doc', 'dent', 'pharma', 'opt', 'labo', 'radio'",
            "type_chap":         "STRING — Type de chapitre : 'plafond_unit', 'plafond', 'qty_period'",
            "type_honoraire":    "STRING — Type d'honoraire : 'montant' ou 'lettre'",
            "dent":              "INTEGER — Numéro de dent (soins dentaires, 0 = non dentaire)",
            "montant_depense":   "FLOAT — MONTANT DÉPENSÉ — utiliser SUM() pour total par prestation",
            "montant_pec":       "FLOAT — MONTANT PRIS EN CHARGE — utiliser SUM() pour total PEC",
            "montant_frais":     "FLOAT — Montant des frais",
            "first_mnt_pec":     "FLOAT — Premier montant PEC (avant ajustements)",
            "price_unit":        "FLOAT — Prix unitaire",
            "qty":               "FLOAT — Quantité / nombre d'unités",
            "qty_pec":           "FLOAT — Quantité prise en charge",
            "nbr_jour":          "FLOAT — Nombre de jours (hospitalisation)",
            "nbr_lettre_doc":    "FLOAT — Nombre de lettres clés documentées",
            "nbre_kine":         "INTEGER — Nombre de séances kiné",
            "reste_nbre_kine":   "INTEGER — Reste de séances kiné",
            "ecart_demande":     "INTEGER — Écart demandé",
            "ecart_real":        "INTEGER — Écart réel",
            "valeur_cle_pec":    "FLOAT — Valeur lettre clé PEC",
            "valeur_lettre_chapitre": "FLOAT — Valeur lettre par chapitre",
            "tarif_jour":        "FLOAT — Tarif journalier",
            "tarif_hosp_pec":    "FLOAT — Tarif hospitalier PEC",
            "total_prix_doc":    "FLOAT — Total prix document",
            "pec_cnam":          "FLOAT — Part remboursée CNAM",
            "conditions":        "STRING — Conditions particulières d'application",
            "detail-incognito":  "INTEGER — Flag incognito (technique)",
            "active":            "BOOLEAN — Ligne active",
            "is_acuity":         "BOOLEAN — Soin d'acuité visuelle",
            "is_cnam":           "BOOLEAN — Soumis à la CNAM",
            "is_cnam_required":  "BOOLEAN — CNAM obligatoire",
            "is_condition_met":  "BOOLEAN — Condition remplie",
            "is_cv_confirm":     "BOOLEAN — CV confirmé",
            "is_nbr_cv_lettre":  "BOOLEAN — Compteur CV lettre",
            "is_nbr_lettre":     "BOOLEAN — Compteur lettre",
            "is_prestataire":    "BOOLEAN — Prestataire",
            "is_seance_kine":    "BOOLEAN — Séance de kinésithérapie",
            "chap_id":           "INTEGER — ID du chapitre (FK)",
            "prestation_id":     "INTEGER — ID de la prestation parent (FK)",
            "product_id":        "INTEGER — ID du produit (FK)",
            "nomenclature_doc_id": "INTEGER — ID nomenclature (FK)",
        },
    },
    "BulletinSoinMessage": {
        "desc": "Message / observation sur une ligne de prestation (message TPA, observation, commentaire)",
        "props": {
            "code":       "STRING — Code du message",
            "id":         "INTEGER — Identifiant interne",
            "is_msg_tpa": "BOOLEAN — Message TPA (true = message du TPA)",
            "list_msg":   "STRING — Texte du message / liste d'observations",
            "msg_tpa":    "STRING — Message TPA détaillé",
            "name":       "STRING — Nom / titre du message",
        },
    },
    "BulletinSoinTag": {
        "desc": "Tag / étiquette attaché à un BS (ex: 'Traité', 'C.V à traiter', 'Export Client')",
        "props": {
            "id":   "INTEGER — Identifiant interne",
            "name": "STRING — Nom du tag",
        },
    },
    "Client": {
        "desc": "Entreprise cliente (société adhérente au contrat collectif)",
        "props": {
            "id":           "INTEGER — Identifiant interne",
            "name":         "STRING — Nom de l'entreprise",
            "display_name": "STRING — Nom affiché",
        },
    },
    "College": {
        "desc": "Collège / catégorie d'assurés dans une entreprise",
        "props": {
            "id":         "INTEGER — Identifiant interne",
            "name":       "STRING — Nom du collège (ex: 'ACTIF', 'Cadres', 'Non-cadres')",
            "code":       "STRING — Code du collège (ex: '1')",
            "company_id": "INTEGER — ID de l'entreprise (FK)",
        },
    },
    "Gestionnaire": {
        "desc": "Gestionnaire (personne qui traite les BS)",
        "props": {
            "id":   "INTEGER — Identifiant interne",
            "name": "STRING — Nom / code du gestionnaire",
        },
    },
    "HmsPhysician": {
        "desc": "Médecin / professionnel de santé (prescripteur ou exécutant)",
        "props": {
            "id":                  "INTEGER — Identifiant interne",
            "name":                "STRING — Nom / raison sociale (cabinet, clinique, etc.)",
            "code":                "STRING — Code RPPS / numéro d'inscription",
            "rne":                 "STRING — Numéro RNE (souvent identique au code)",
            "specialty_id":        "INTEGER — ID de la spécialité médicale (FK)",
            "street":              "STRING — Rue d'exercice",
            "geo_latitude":        "FLOAT — Latitude géographique",
            "geo_longitude":       "FLOAT — Longitude géographique",
            "typeprestataire":     "STRING — Type : 'doc' (médecin), 'dent', 'radio', 'labo', 'cliniq' (clinique)",
            "active":              "BOOLEAN — Professionnel actif",
            "is_control_physician":"BOOLEAN — Médecin contrôleur",
            "is_prestataire_tpa":  "BOOLEAN — Prestataire TPA",
        },
    },
    "InsuranceContract": {
        "desc": "Contrat d'assurance individuel lié à un assuré",
        "props": {
            "id":               "INTEGER — Identifiant interne",
            "name":             "STRING — Nom / référence du contrat (ex: '544/2016')",
            "state":            "STRING — État : 'done', 'terminated', 'suspended'",
            "year_contract":    "INTEGER — Année du contrat",
            "limit_age":        "INTEGER — Âge limite de couverture",
            "limit_age_prest":  "INTEGER — Âge limite pour les prestations",
            "active":           "BOOLEAN — Contrat actif",
            "is_consom_couple": "BOOLEAN — Consommation en couple",
            "assure_id":        "INTEGER — ID de l'assuré (FK)",
            "offer_id":         "INTEGER — ID de l'offre (FK)",
        },
    },
    "InsuranceContractCompany": {
        "desc": "Contrat entreprise (liaison entre assureur, offre et entreprise cliente)",
        "props": {
            "id":               "INTEGER — Identifiant interne",
            "name":             "STRING — Nom du contrat entreprise",
            "state":            "STRING — État : 'active', 'draft'",
            "date_start":       "DATE — Date de début d'effet",
            "date_end":         "DATE — Date de fin d'effet",
            "limit_age":        "INTEGER — Âge limite de couverture",
            "limit_age_prest":  "INTEGER — Âge limite prestations",
            "active":           "BOOLEAN — Contrat actif",
            "company_id":       "INTEGER — ID entreprise cliente (FK)",
            "assurance_id":     "INTEGER — ID assureur (FK)",
            "offer_id":         "INTEGER — ID offre souscrite (FK)",
        },
    },
    "InsuranceContractConsommation": {
        "desc": "CONSOMMATION CONTRACTUELLE — suivi des plafonds et reste à charge par assuré",
        "props": {
            "id":                          "INTEGER — Identifiant interne",
            "plafond":                     "FLOAT — PLAFOND GLOBAL — montant total de couverture annuelle",
            "reste_plafond":               "FLOAT — RESTE À CHARGE GLOBAL — plafond - montant déjà consommé",
            "plafond_malade_chronique":    "FLOAT — Plafond spécifique pour les malades chroniques",
            "reste_plafond_chronique":     "FLOAT — Reste à charge pour les malades chroniques",
            "plafond_malade_grave":        "FLOAT — Plafond spécifique pour les maladies graves",
            "reste_plafond_grave":         "FLOAT — Reste à charge pour les maladies graves",
            "statut":                      "STRING — Statut : 'active'",
            "active":                      "BOOLEAN — Consommation active",
            "is_chronique":                "BOOLEAN — Assuré en affection de longue durée (ALD)",
            "is_grave":                    "BOOLEAN — Assuré avec maladie grave",
            "assure_id":                   "INTEGER — ID de l'assuré (FK)",
            "contract_id":                 "INTEGER — ID du contrat (FK)",
            "beneficiaire_id":             "INTEGER — ID du bénéficiaire (FK)",
        },
    },
    "InsuranceContractConsommationForfait": {
        "desc": "Forfait de consommation (ex: forfait annuel maternité, circoncision, frais funéraires)",
        "props": {
            "id":         "INTEGER — Identifiant interne",
            "name":       "STRING — Nom du forfait (ex: 'Maternité', 'Circoncision', 'Frais Funéraires')",
            "periode":    "INTEGER — Période / fréquence en jours (0 = unique)",
            "chapitre_id":"INTEGER — ID du chapitre (FK)",
            "consom_id":  "INTEGER — ID de la consommation (FK)",
        },
    },
    "InsuranceContractConsommationLimit": {
        "desc": "Limite de consommation (quantité max par période, ex: nombre de montures optiques tous les 2 ans)",
        "props": {
            "id":                "INTEGER — Identifiant interne",
            "name":              "STRING — Nom de la limite (ex: 'Optique: Montures', 'Cure Thermale')",
            "periode":           "INTEGER — Période en jours (730 = 2 ans, 0 = unique)",
            "qty":               "INTEGER — Quantité maximale autorisée sur la période",
            "qty_consom":        "INTEGER — Quantité déjà consommée",
            "chapitre_id":       "INTEGER — ID du chapitre (FK)",
            "consom_id":         "INTEGER — ID de la consommation (FK)",
        },
    },
    "InsuranceContractConsommationPlafond": {
        "desc": "PLAFOND PAR CHAPITRE — montant max de remboursement par catégorie (hospitalisation, dentaire, optique, pharmacie, etc.)",
        "props": {
            "id":                       "INTEGER — Identifiant interne",
            "plafond":                  "FLOAT — PLAFOND DU CHAPITRE — utiliser pour 'plafond hospitalisation', 'plafond dentaire', etc.",
            "reste":                    "FLOAT — RESTE DU CHAPITRE — ce qu'il reste à consommer sur ce chapitre",
            "plafond_malade_chronique": "FLOAT — Plafond chapitre pour malades chroniques",
            "reste_plafond_chronique":  "FLOAT — Reste plafond chronique pour ce chapitre",
            "plafond_malade_grave":     "FLOAT — Plafond chapitre pour maladies graves",
            "reste_plafond_grave":      "FLOAT — Reste plafond grave pour ce chapitre",
            "name":                     "STRING — Nom du plafond / chapitre (ex: 'Pharmacie', 'Optique: Lentilles')",
            "is_chronique":             "BOOLEAN — Concerne les affections chroniques",
            "is_grave":                 "BOOLEAN — Concerne les maladies graves",
            "chapitre_id":              "INTEGER — ID du chapitre ciblé (FK)",
            "consom_id":                "INTEGER — ID de la consommation parent (FK)",
        },
    },
    "InsuranceOffer": {
        "desc": "Offre d'assurance (produit d'assurance souscrit par l'entreprise)",
        "props": {
            "id":                       "INTEGER — Identifiant interne",
            "name":                     "STRING — Nom de l'offre (ex: 'Client 47 2018701000024/2024')",
            "police":                   "STRING — Numéro de police d'assurance",
            "date_effet":               "DATE — Date d'effet de l'offre",
            "plafond":                  "FLOAT — Plafond global de l'offre",
            "plafond_malade_chronique": "FLOAT — Plafond malade chronique de l'offre",
            "plafond_malade_grave":     "FLOAT — Plafond maladie grave de l'offre",
            "active":                   "BOOLEAN — Statut actif/inactif du contrat",
            "assurance_id":             "INTEGER — ID de l'assureur (FK)",
            "societe_id":               "INTEGER — ID de la société cliente (FK)",
        },
    },
    "InsuranceOfferChapitre": {
        "desc": "CHAPITRE D'OFFRE — catégorie de garantie (hospitalisation, dentaire, pharmacie, optique, etc.)",
        "props": {
            "id":                    "INTEGER — Identifiant interne",
            "name":                  "STRING — NOM DU CHAPITRE — utiliser pour filtrer par catégorie (CONTAINS 'hospitalisation', 'dentaire', etc.)",
            "type_chap":             "STRING — Type de chapitre (ex: 'forfait')",
            "plafond":               "FLOAT — Plafond du chapitre dans l'offre",
            "plafond_malade_grave":  "FLOAT — Plafond grave du chapitre",
            "pourcentage":           "FLOAT — Pourcentage de remboursement",
            "forfait":               "FLOAT — Forfait (montant fixe)",
            "qty":                   "INTEGER — Quantité / nombre d'actes couverts",
            "delai_carence":         "INTEGER — Délai de carence (en jours)",
            "limit_age":             "INTEGER — Âge limite pour ce chapitre",
            "period":                "INTEGER — Période de couverture (en jours)",
            "amount_chroni":         "FLOAT — Montant pour les chroniques",
            "is_acuity":             "BOOLEAN — Acuité visuelle concernée",
            "is_carence":            "BOOLEAN — Période de carence active",
            "is_cnam":               "BOOLEAN — Chapitre CNAM",
            "is_forfait_couple":     "STRING — Forfait couple (ex: 'one_for_two')",
            "chapitre_id":           "INTEGER — ID du chapitre de référence (FK)",
            "offer_id":              "INTEGER — ID de l'offre parent (FK)",
        },
    },
    "InsuranceOfferChapitreCondition": {
        "desc": "Condition d'activation d'un chapitre d'offre (ex: condition pour qu'un acte soit remboursé)",
        "props": {
            "active":      "BOOLEAN — Condition active",
            "chapitre_id": "INTEGER — ID du chapitre associé (FK)",
            "id":          "INTEGER — Identifiant interne",
            "name":        "STRING — Nom de la condition (ex: 'soin_prothese_dentaire')",
        },
    },
    "InsuranceOfferChapitreList": {
        "desc": "Liste / type de chapitre (classification des catégories de garantie)",
        "props": {
            "id":                      "INTEGER — Identifiant interne",
            "name":                    "STRING — Nom du type de chapitre (ex: 'CONSULTATION GENERALISTE', 'Implants Dentaires')",
            "condition_type_chapitre": "STRING — Condition d'activation du chapitre (ex: 'soin_prothese_dentaire')",
            "active":                  "BOOLEAN — Statut actif/inactif",
        },
    },
    "LettresCle": {
        "desc": "Lettre clé (tarif de base pour un acte médical, ex: 'C', 'B', 'K')",
        "props": {
            "id":          "INTEGER — Identifiant interne",
            "name":        "STRING — Nom de la lettre clé (ex: 'KE', 'KC', 'D', 'R', 'Z')",
            "value":       "FLOAT — Valeur monétaire de la lettre clé",
            "type_lettre": "STRING — Type de lettre ('rubriq', 'value')",
            "active":      "BOOLEAN — Statut actif/inactif",
        },
    },
    "LettresCleOffer": {
        "desc": "Lettre clé spécifique à une offre (tarif négocié par chapitre)",
        "props": {
            "id":               "INTEGER — Identifiant interne",
            "value_lettre_cle": "FLOAT — Valeur négociée de la lettre clé dans l'offre",
            "active":           "BOOLEAN — Statut actif/inactif",
            "chapitre_id":      "INTEGER — ID du chapitre (FK)",
            "lettre_cle_id":    "INTEGER — ID de la lettre clé de référence (FK)",
        },
    },
    "PhysicianSpecialty": {
        "desc": "Spécialité médicale (cardiologue, radiologue, dentiste, etc.)",
        "props": {
            "id":               "INTEGER — Identifiant interne",
            "name":             "STRING — Nom de la spécialité (ex: 'MEDECIN GENERALISTE', 'OPTIOCIEN')",
            "type_prestataire": "STRING — Type de prestataire associé (ex: 'cliniq', 'opt', 'doc')",
        },
    },
    "Product": {
        "desc": "PRODUIT — médicament, dispositif médical, prothèse, lentille, etc.",
        "props": {
            "id":                "INTEGER — Identifiant interne",
            "name":              "STRING — Nom du produit (ex: 'CICA-TREAT ZINC SPRAY 100ML')",
            "code_pct":          "STRING — Code PCT (ex: '350933', '103293')",
            "cotation":          "FLOAT — Cotation",
            "list_price":        "FLOAT — Prix de vente",
            "value_lettre_cle":  "FLOAT — Valeur lettre clé associée",
            "gender":            "STRING — Genre cible si applicable (ex: 'all')",
            "child_age":         "INTEGER — Âge enfant si applicable (0 = non concerné)",
            "malade_chron":      "BOOLEAN — Concerne les malades chroniques",
            "pregnancy_warning": "BOOLEAN — Avertissement grossesse",
            "lactation_warning": "BOOLEAN — Avertissement allaitement",
            "active":            "BOOLEAN — Statut actif/inactif",
            "categ_id":          "INTEGER — ID de la catégorie (FK)",
            "famille":           "INTEGER — Famille du produit (REM: utiliser ProductFamille via IN_FAMILLE, pas ce champ FK)",
            "nature":            "INTEGER — Nature du produit (REM: utiliser ProductNature via HAS_NATURE, pas ce champ FK)",
        },
    },
    "ProductCategory": {
        "desc": "Catégorie de produit",
        "props": {
            "id":             "INTEGER — Identifiant interne",
            "complete_name":  "STRING — Nom complet de la catégorie (ex: 'SALLE D'OPERATION', 'ALL')",
            "honorary_type":  "STRING — Type d'honoraire associé (ex: 'cliniq', 'radio', 'doc')",
            "active":         "BOOLEAN — Statut actif/inactif",
        },
    },
    "ProductFamille": {
        "desc": "Famille de produit (ex: 'Médicaments', 'Dispositifs médicaux')",
        "props": {
            "id":        "INTEGER — Identifiant interne",
            "name":      "STRING — Nom de la famille (ex: 'DERMATOLOGIE', 'COSMETIQUE')",
            "active":    "BOOLEAN — Statut actif/inactif",
        },
    },
    "ProductNature": {
        "desc": "Nature de produit (ex: 'Pharmaceutique', 'Optique', 'Dentaire')",
        "props": {
            "id":   "INTEGER — Identifiant interne",
            "name": "STRING — Nom de la nature — utiliser pour filtrer 'pharmaceutique', 'optique', etc.",
            "active": "BOOLEAN — Statut actif/inactif",
        },
    },
    "State": {
        "desc": "État / gouvernorat (division administrative, Tunisie)",
        "props": {
            "id":   "INTEGER — Identifiant interne",
            "name": "STRING — Nom du gouvernorat (ex: 'Ben Arous', 'Bizerte', 'Béja')",
        },
    },
}


# ── Helpers ──────────────────────────────────────────────────────────────────


def format_property_registry(
    node_labels: list[str] | None = None,
) -> str:
    """Format the NODE_PROPERTY_REGISTRY as a prompt-friendly block.

    Shows exactly the properties defined per label (hand-curated).
    When *node_labels* is given, only those labels are rendered.
    """
    labels = node_labels or sorted(NODE_PROPERTY_REGISTRY.keys())
    lines: list[str] = []
    for label in labels:
        entry = NODE_PROPERTY_REGISTRY.get(label)
        if not entry:
            continue
        ndesc = entry.get("desc", "")
        props = entry.get("props", {})
        if not props:
            continue
        header = f"-- {label}"
        if ndesc:
            header += f" -- {ndesc}"
        lines.append(header)
        for pname, pdesc in props.items():
            lines.append(f"  {pname:<30s} {pdesc}")
    return "\n".join(lines)
