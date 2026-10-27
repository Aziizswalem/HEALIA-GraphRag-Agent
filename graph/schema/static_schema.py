"""
graph/schema/static_schema.py — v2 (fix C6)

FIX C6 — DOMAIN_TOPOLOGY : chemins composés → triplets simples
───────────────────────────────────────────────────────────────
AVANT : DOMAIN_TOPOLOGY contenait des lignes multi-sauts comme :
          (:Client)<-[:APPLIES_TO_COMPANY]-(:InsuranceContractCompany)-[:HAS_COLLEGE]->...
        Le parser regex de graph_path_semantic_check ne matchait que
        les triplets simples (A)-[R]->(B) → ces chemins composés
        n'étaient pas indexés → triples manquants → faux positifs.

APRÈS : chaque relation est sur sa propre ligne, format canonique :
          (:Source)-[:REL_TYPE]->(:Target)
        Compatible à la fois avec l'ancienne regex et la nouvelle
        version de _parse_topology_triples (FIX C6 dans query_guard_patch.py).

FULL_SCHEMA : inchangé (source de vérité pour les labels/relations).
DOMAIN_TOPOLOGY : nettoyé, triplets simples uniquement, commentaires réduits.
"""
from __future__ import annotations

# ── Complete relationship map (source → rel → target) ─────────────────────────
# Verified against live Neo4j DB — 2026-05

FULL_SCHEMA = """
══════════════════════════════════════════════════════════════════
COMPLETE GRAPH SCHEMA — all node labels and relationships
══════════════════════════════════════════════════════════════════

## Core claim nodes

(:BulletinSoin)-[:CREATED_FOR]->(:Assure)
(:BulletinSoin)-[:AFFECTS]->(:InsuranceContractConsommation)
(:BulletinSoin)-[:COVERED_BY]->(:Assureur)
(:BulletinSoin)-[:ISSUED_BY_COMPANY]->(:Client)
(:BulletinSoin)-[:CLAIM_UNDER_OFFER]->(:InsuranceOffer)
(:BulletinSoin)-[:FILED_UNDER_CONTRACT]->(:InsuranceContract)
(:BulletinSoin)-[:MANAGED_BY]->(:Gestionnaire)
(:BulletinSoin)-[:IN_BORDEREAU]->(:Bordereau)
(:BulletinSoin)-[:CLAIM_FOR_DEPENDENT]->(:Beneficiaire)
(:BulletinSoin)-[:CLAIM_FOR_COUPLE]->(:Assure)
(:BulletinSoin)-[:LINKED_TO_BS]->(:BulletinSoin)
(:BulletinSoin)-[:HAS_TAG]->(:BulletinSoinTag)

## Prestation (line items inside a claim)

(:BulletinSoinPrestation)-[:BELONGS_TO_BS]->(:BulletinSoin)
(:BulletinSoinPrestation)-[:PERFORMED_BY]->(:HmsPhysician)
(:BulletinSoinPrestation)-[:PRESCRIBED_BY_SPECIALTY]->(:PhysicianSpecialty)
(:BulletinSoinPrestationDetail)-[:CREATED_UNDER]->(:BulletinSoinPrestation)
(:BulletinSoinPrestationDetail)-[:COVERED_BY_CHAPTER]->(:InsuranceOfferChapitre)
(:BulletinSoinPrestationDetail)-[:USES_PRODUCT]->(:Product)
(:BulletinSoinPrestationDetail)-[:IN_SOUS_CHAPITRE]->(:InsuranceOfferChapitre)
(:BulletinSoinPrestationDetail)-[:BILLED_WITH_LETTRE_CLE]->(:LettresCle)
(:BulletinSoinPrestationDetail)-[:HAS_LINE_OBSERVATION]->(:BulletinSoinMessage)

## Consommation / plafond (consumption tracking)

(:InsuranceContractConsommation)-[:CONCERNS_ASSURE]->(:Assure)
(:InsuranceContractConsommation)-[:TRACKS_CONTRACT]->(:InsuranceContract)
(:InsuranceContractConsommationPlafond)-[:CEILING_UNDER_CONSOMMATION]->(:InsuranceContractConsommation)
(:InsuranceContractConsommationPlafond)-[:CEILING_OF_CHAPTER]->(:InsuranceOfferChapitre)
(:InsuranceContractConsommationLimit)-[:LIMIT_UNDER_CONSOMMATION]->(:InsuranceContractConsommation)
(:InsuranceContractConsommationLimit)-[:LIMIT_OF_CHAPTER]->(:InsuranceOfferChapitre)
(:InsuranceContractConsommationForfait)-[:FORFEIT_UNDER_CONSOMMATION]->(:InsuranceContractConsommation)
(:InsuranceContractConsommationForfait)-[:FORFEIT_OF_CHAPTER]->(:InsuranceOfferChapitre)
(:InsuranceContractConsommationForfait)-[:FORFEIT_TRIGGERED_BY_BS]->(:BulletinSoin)

## Contract hierarchy

(:InsuranceContract)-[:COVERS]->(:Assure)
(:InsuranceContract)-[:ISSUED_BY]->(:InsuranceContractCompany)
(:InsuranceContract)-[:CONTRACT_UNDER_OFFER]->(:InsuranceOffer)
(:InsuranceContract)-[:CONTRACTED_FOR_COUPLE]->(:Assure)
(:InsuranceContractCompany)-[:APPLIES_TO_COMPANY]->(:Client)
(:InsuranceContractCompany)-[:COMPANY_CONTRACT_UNDER_OFFER]->(:InsuranceOffer)
(:InsuranceContractCompany)-[:HAS_COLLEGE]->(:College)
(:InsuranceContractCompany)-[:CONTRACT_BELONGS_TO_ASSUREUR]->(:Assureur)

## Offer / chapter structure

(:InsuranceOffer)-[:OFFER_BELONGS_TO_ASSUREUR]->(:Assureur)
(:InsuranceOffer)-[:MARKETED_TO_COMPANY]->(:Client)
(:InsuranceOfferChapitre)-[:CHAPTER_UNDER_OFFER]->(:InsuranceOffer)
(:InsuranceOfferChapitre)-[:OF_CHAPITRE_TYPE]->(:InsuranceOfferChapitreList)
(:InsuranceOfferChapitre)-[:HAS_PARENT_CHAPITRE]->(:InsuranceOfferChapitre)
(:InsuranceOfferChapitre)-[:HAS_PRODUCT]->(:Product)
(:InsuranceOfferChapitre)-[:HAS_PRODUCT_CATEGORY]->(:ProductCategory)
(:InsuranceOfferChapitre)-[:HAS_PRODUCT_FAMILLE]->(:ProductFamille)
(:InsuranceOfferChapitre)-[:HAS_PRODUCT_NATURE]->(:ProductNature)
(:InsuranceOfferChapitreCondition)-[:CONDITION_OF_CHAPTER]->(:InsuranceOfferChapitre)

## Product / nomenclature

(:Product)-[:IN_CATEGORY]->(:ProductCategory)
(:Product)-[:IN_FAMILLE]->(:ProductFamille)
(:Product)-[:HAS_NATURE]->(:ProductNature)
(:Product)-[:PRICED_BY_LETTRE_CLE]->(:LettresCle)
(:LettresCleOffer)-[:HAS_LETTRE_CLE]->(:LettresCle)
(:LettresCleOffer)-[:APPLIES_TO_CHAPTER]->(:InsuranceOfferChapitre)
(:LettresCleOffer)-[:CUSTOMIZED_FOR_PHYSICIAN]->(:HmsPhysician)

## People / org

(:Assure)-[:MEMBER_OF_COLLEGE]->(:College)
(:Assure)-[:MARRIED_TO]->(:Assure)
(:Assure)-[:HAS_ASSURANCE]->(:InsuranceOfferChapitreList)
(:Beneficiaire)-[:DEPENDENT_OF]->(:Assure)
(:Beneficiaire)-[:CONCERNS_BENEFICIAIRE]->(:InsuranceContractConsommation)
(:College)-[:PART_OF_COMPANY]->(:Client)
(:Bordereau)-[:ISSUED_FOR]->(:Client)
(:Bordereau)-[:GENERATED_FOR]->(:Client)
(:Bordereau)-[:BORDEREAU_UNDER_OFFER]->(:InsuranceOffer)
(:HmsPhysician)-[:HAS_SPECIALTY]->(:PhysicianSpecialty)
(:HmsPhysician)-[:LOCATED_IN_STATE]->(:State)
══════════════════════════════════════════════════════════════════
"""

# ── Critical traversal paths (DOMAIN_TOPOLOGY) ────────────────────────────────
# FIX C6 : UNIQUEMENT des triplets simples (:Source)-[:REL]->(:Target).
# Plus de chemins composés multi-sauts sur une seule ligne.
# Chaque relation est sur sa propre ligne → compatible avec _parse_topology_triples.

DOMAIN_TOPOLOGY = """\
══════════════ DOMAIN TOPOLOGY — annotated by business intent ════════
Use ONLY these traversal paths. Never shortcut or invent alternatives.

━━━ INTENTION: "Actes / prestations d'un adhérent" ━━━
// Quand l'utilisateur parle de "montant dépensé", "montant PEC", "nombre d'actes",
// "liste des prestations", "consommation financière", "détails des soins" →
// utiliser ce chemin pour compter/agréger les lignes de prestation
(:BulletinSoin)-[:CREATED_FOR]->(:Assure)
(:BulletinSoinPrestation)-[:BELONGS_TO_BS]->(:BulletinSoin)
(:BulletinSoinPrestationDetail)-[:CREATED_UNDER]->(:BulletinSoinPrestation)
(:BulletinSoinPrestationDetail)-[:COVERED_BY_CHAPTER]->(:InsuranceOfferChapitre)
(:BulletinSoinPrestationDetail)-[:IN_SOUS_CHAPITRE]->(:InsuranceOfferChapitre)
//   → COUNT(det) = nombre d'actes, SUM(det.montant_depense) = total dépensé
//   → SUM(det.montant_pec) = total pris en charge
//   → COUNT(DISTINCT bs) = nombre de bulletins de soin

━━━ INTENTION: "Plafond / consommation contractuelle" ━━━
// Quand l'utilisateur parle de "plafond", "reste à charge", "consommation par rapport
// au contrat", "plafond chronique", "plafond global" → utiliser ce chemin
(:InsuranceContractConsommation)-[:CONCERNS_ASSURE]->(:Assure)
(:InsuranceContractConsommation)-[:TRACKS_CONTRACT]->(:InsuranceContract)
//   → icc.plafond = plafond total, icc.reste_plafond = reste
//   → icc.plafond - icc.reste_plafond = montant déjà consommé
//   → icc.is_chronique, icc.plafond_malade_chronique, icc.reste_plafond_chronique
// ATTENTION: "consomme le plus" est AMBIGU — peut être actes (chemin BS→BSP→Detail)
//   OU plafond consommé (chemin ICC). Si ambigu, privilégier le chemin BS.

━━━ INTENTION: "Plafond par chapitre / spécialité" ━━━
// Quand l'utilisateur précise un type : "hospitalisation", "dentaire", "optique",
// "pharmacie", "consultation" → utiliser ce chemin AVEC filtrage sur le chapitre
(:InsuranceContractConsommationPlafond)-[:CEILING_OF_CHAPTER]->(:InsuranceOfferChapitre)
(:InsuranceContractConsommationPlafond)-[:CEILING_UNDER_CONSOMMATION]->(:InsuranceContractConsommation)
(:InsuranceContractConsommation)-[:CONCERNS_ASSURE]->(:Assure)
//   → p.plafond = plafond du chapitre, p.reste = reste du chapitre
//   → Filtrer: WHERE toLower(chap.name) CONTAINS "hospitalisation"

━━━ INTENTION: "Détails d'un Bulletin de Soin" ━━━
// Quand l'utilisateur demande les infos d'un BS spécifique ou liste de BS
(:BulletinSoin)-[:AFFECTS]->(:InsuranceContractConsommation)
(:BulletinSoin)-[:COVERED_BY]->(:Assureur)
(:BulletinSoin)-[:ISSUED_BY_COMPANY]->(:Client)
(:BulletinSoin)-[:CLAIM_UNDER_OFFER]->(:InsuranceOffer)
(:BulletinSoin)-[:FILED_UNDER_CONTRACT]->(:InsuranceContract)
(:BulletinSoin)-[:MANAGED_BY]->(:Gestionnaire)
(:BulletinSoin)-[:IN_BORDEREAU]->(:Bordereau)
(:BulletinSoin)-[:CLAIM_FOR_DEPENDENT]->(:Beneficiaire)
(:BulletinSoin)-[:CLAIM_FOR_COUPLE]->(:Assure)
(:BulletinSoin)-[:LINKED_TO_BS]->(:BulletinSoin)

━━━ INTENTION: "Produit / Médicament" ━━━
// Quand l'utilisateur parle de "médicament", "produit",
// "princeps", "générique" → utiliser ces chemins
(:BulletinSoinPrestationDetail)-[:USES_PRODUCT]->(:Product)
(:Product)-[:IN_CATEGORY]->(:ProductCategory)
(:Product)-[:IN_FAMILLE]->(:ProductFamille)
(:Product)-[:HAS_NATURE]->(:ProductNature)
(:Product)-[:PRICED_BY_LETTRE_CLE]->(:LettresCle)
(:InsuranceOfferChapitre)-[:HAS_PRODUCT]->(:Product)
(:InsuranceOfferChapitre)-[:HAS_PRODUCT_CATEGORY]->(:ProductCategory)
(:InsuranceOfferChapitre)-[:HAS_PRODUCT_FAMILLE]->(:ProductFamille)
(:InsuranceOfferChapitre)-[:HAS_PRODUCT_NATURE]->(:ProductNature)

━━━ INTENTION: "Médecin / Spécialité" ━━━
// Quand l'utilisateur parle de "médecin", "docteur", "spécialité",
// "cardiologue", "chirurgien" → utiliser ces chemins
(:BulletinSoinPrestation)-[:PERFORMED_BY]->(:HmsPhysician)
(:BulletinSoinPrestation)-[:PRESCRIBED_BY_SPECIALTY]->(:PhysicianSpecialty)
(:HmsPhysician)-[:HAS_SPECIALTY]->(:PhysicianSpecialty)
(:HmsPhysician)-[:LOCATED_IN_STATE]->(:State)

━━━ INTENTION: "Assureur / Contrat / Offre" ━━━
// Quand l'utilisateur parle de "compagnie d'assurance", "assureur", "contrat",
// "offre", "police", "primes" → utiliser ces chemins
(:InsuranceContractCompany)-[:APPLIES_TO_COMPANY]->(:Client)
(:InsuranceContractCompany)-[:COMPANY_CONTRACT_UNDER_OFFER]->(:InsuranceOffer)
(:InsuranceContractCompany)-[:HAS_COLLEGE]->(:College)
(:InsuranceContractCompany)-[:CONTRACT_BELONGS_TO_ASSUREUR]->(:Assureur)
(:InsuranceContract)-[:COVERS]->(:Assure)
(:InsuranceContract)-[:CONTRACT_UNDER_OFFER]->(:InsuranceOffer)
(:InsuranceContract)-[:ISSUED_BY]->(:InsuranceContractCompany)
(:InsuranceContract)-[:CONTRACTED_FOR_COUPLE]->(:Assure)
(:InsuranceOffer)-[:OFFER_BELONGS_TO_ASSUREUR]->(:Assureur)
(:InsuranceOffer)-[:MARKETED_TO_COMPANY]->(:Client)
(:InsuranceOfferChapitre)-[:CHAPTER_UNDER_OFFER]->(:InsuranceOffer)
(:InsuranceOfferChapitre)-[:OF_CHAPITRE_TYPE]->(:InsuranceOfferChapitreList)
(:InsuranceOfferChapitre)-[:HAS_PARENT_CHAPITRE]->(:InsuranceOfferChapitre)
//   NEVER link (College) directly to (InsuranceContract)
//   NEVER link (BulletinSoin) directly to (Assureur) if you need Contract data

━━━ INTENTION: "Nomenclature / Lettre clé" ━━━
// Quand l'utilisateur parle de "nomenclature", "lettre clé", "acte médical",
// "tarif", "cotation" → utiliser ces chemins
(:BulletinSoinPrestationDetail)-[:BILLED_WITH_LETTRE_CLE]->(:LettresCle)

━━━ INTENTION: "Assuré / Bénéficiaire / Famille" ━━━
// Quand l'utilisateur parle de "conjoint", "enfant", "bénéficiaire",
// "famille", "ayant-droit" → utiliser ces chemins
(:Assure)-[:MEMBER_OF_COLLEGE]->(:College)
(:Assure)-[:MARRIED_TO]->(:Assure)
(:Assure)-[:HAS_ASSURANCE]->(:InsuranceOfferChapitreList)
(:Beneficiaire)-[:DEPENDENT_OF]->(:Assure)
(:Beneficiaire)-[:CONCERNS_BENEFICIAIRE]->(:InsuranceContractConsommation)
(:College)-[:PART_OF_COMPANY]->(:Client)

━━━ INTENTION: "Bordereau / TPA" ━━━
// Quand l'utilisateur parle de "bordereau", "TPA", "lot de BS",
// "envoi" → utiliser ces chemins
(:BulletinSoin)-[:IN_BORDEREAU]->(:Bordereau)
(:Bordereau)-[:ISSUED_FOR]->(:Client)
(:Bordereau)-[:GENERATED_FOR]->(:Client)
(:Bordereau)-[:BORDEREAU_UNDER_OFFER]->(:InsuranceOffer)
//   Label is exactly "Bordereau" — NOT BordereauSoin or any variant

━━━ INTENTION: "Limites / Forfaits" ━━━
(:InsuranceContractConsommationLimit)-[:LIMIT_OF_CHAPTER]->(:InsuranceOfferChapitre)
(:InsuranceContractConsommationLimit)-[:LIMIT_UNDER_CONSOMMATION]->(:InsuranceContractConsommation)
(:InsuranceContractConsommationForfait)-[:FORFEIT_OF_CHAPTER]->(:InsuranceOfferChapitre)
(:InsuranceContractConsommationForfait)-[:FORFEIT_UNDER_CONSOMMATION]->(:InsuranceContractConsommation)
(:InsuranceContractConsommationForfait)-[:FORFEIT_TRIGGERED_BY_BS]->(:BulletinSoin)

━━━ RÈGLES DE SÉLECTION DE CHEMIN ━━━
// Quand l'utilisateur dit → PRIVILÉGIER le chemin
// "consomme le plus" (sans préciser) → Chemin BS→BSP→BSPDetail (montant_depense)
// "plafond" / "reste" → Chemin ICC
// "montant dépensé" → Chemin BS→BSP→BSPDetail (SUM det.montant_depense)
// "montant PEC" → Chemin BS→BSP→BSPDetail (SUM det.montant_pec)
// "nombre d'actes" → Chemin BS→BSP→BSPDetail (COUNT det)
// "liste des prestations" → Chemin BS→BSP→BSPDetail
// "médicaments" / "produits" → Chemin BSPDetail→Product
// "par spécialité" → Chemin BSP→PhysicianSpecialty
// "par assureur" → Chemin BS→Assureur ou ICC→Assureur
// "bordereau" → Chemin BS→Bordereau
// "bénéficiaires" → Chemin Beneficiaire→Assure
// SI LA QUESTION EST AMBIGUË → PRIVILÉGIER le chemin le plus spécifique
//   ou demander une clarification à l'utilisateur
═══════════════════════════════════════════════════════════════════"""
