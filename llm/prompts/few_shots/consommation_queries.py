"""Few-shot examples for consommation / plafond traversal patterns.

These examples are the most critical for the health-insurance graph because
the model tends to collapse the 3-hop path:
  BulletinSoin -[:AFFECTS]-> InsuranceContractConsommation -[:CONCERNS_ASSURE]-> Assure
into a wrong direct relationship, and to place plafond properties on the
wrong node (BulletinSoin or Assure instead of InsuranceContractConsommation).
"""

FEW_SHOTS = """
### Q: Combien d'assurés par assureur ont dépassé leur plafond cette année ?
# PROCESSING PHASE:
# 1) Detect metric: "combien" => aggregation with count(DISTINCT assure)
# 2) Detect grouping: "par assureur" => RETURN assureur.name + count(...)
# 3) Detect timeframe: "cette année" => bs.validation_date >= date({year: date().year, month: 1, day: 1})
# 4) Detect plafond overflow: icc.reste_plafond <= 0
# THINKING CHECKLIST (schema-faithful):
# - reste_plafond is on InsuranceContractConsommation, NOT on BulletinSoin/Assure
# - traversal is BulletinSoin -[:AFFECTS]-> InsuranceContractConsommation -[:CONCERNS_ASSURE]-> Assure
# - insurer grouping comes from (bs)-[:COVERED_BY]->(assureur:Assureur)
MATCH (bs:BulletinSoin)-[:AFFECTS]->(icc:InsuranceContractConsommation)-[:CONCERNS_ASSURE]->(a:Assure),
      (bs)-[:COVERED_BY]->(assureur:Assureur)
WHERE bs.validation_date >= date({year: date().year, month: 1, day: 1})
  AND icc.reste_plafond <= 0
RETURN assureur.name AS assureur,
       count(DISTINCT a) AS nb_assures_depasses
ORDER BY nb_assures_depasses DESC

### Q: Quels assurés ont épuisé leur plafond de consommation ?
# KEY: start from InsuranceContractConsommation to get plafond data
MATCH (icc:InsuranceContractConsommation)-[:CONCERNS_ASSURE]->(a:Assure)
WHERE icc.reste_plafond <= 0
RETURN a.id AS assure_id,
       a.first_name,
       a.last_name,
       icc.plafond,
       icc.reste_plafond
ORDER BY icc.reste_plafond ASC
LIMIT 50

### Q: Taux de consommation moyen par chapitre pour les malades chroniques
# KEY: chapter-level plafond is on InsuranceContractConsommationPlafond, not on Chapitre
MATCH (p:InsuranceContractConsommationPlafond)-[:CEILING_OF_CHAPTER]->(chap:InsuranceOfferChapitre),
      (p)-[:CEILING_UNDER_CONSOMMATION]->(icc:InsuranceContractConsommation)
WHERE icc.is_chronique = true
  AND p.plafond > 0
WITH chap.name AS chapitre,
     avg((p.plafond - p.reste) / p.plafond * 100) AS taux_conso_moyen
RETURN chapitre, round(taux_conso_moyen, 2) AS taux_pct
ORDER BY taux_conso_moyen DESC

### Q: Combien de clients ont au moins 3 contrats d'entreprise actifs ?
# STEP 1: Group by company (Client) and count active contracts
# STEP 2: Filter companies having count >= 3
# STEP 3: Return the total count of these companies
MATCH (client:Client)<-[:APPLIES_TO_COMPANY]-(contract:InsuranceContractCompany)
WHERE contract.active = true
WITH client, count(contract) AS nb_contrats_de_l_entreprise
WHERE nb_contrats_de_l_entreprise >= 3
RETURN count(client) AS nb_entreprises_satisfaisantes

### Q: Quels assurés chroniques ont consommé plus de 80% de leur plafond chronique ?
# KEY: plafond_malade_chronique and reste_plafond_chronique are on InsuranceContractConsommation
MATCH (icc:InsuranceContractConsommation)-[:CONCERNS_ASSURE]->(a:Assure)
WHERE icc.is_chronique = true
  AND icc.plafond_malade_chronique > 0
  AND (icc.plafond_malade_chronique - icc.reste_plafond_chronique) / icc.plafond_malade_chronique >= 0.8
RETURN a.id AS assure_id,
       a.first_name,
       a.last_name,
       icc.plafond_malade_chronique,
       icc.reste_plafond_chronique
ORDER BY icc.reste_plafond_chronique ASC

### Q: Combien de bénéficiaires par assuré en moyenne ?
# KEY: MUST use OPTIONAL MATCH so assures with 0 beneficiaries are counted in the average.
# KEY: Direction is (b:Beneficiaire)-[:DEPENDENT_OF]->(a:Assure) NOT the reverse.
MATCH (a:Assure)
OPTIONAL MATCH (b:Beneficiaire)-[:DEPENDENT_OF]->(a)
WITH a, count(b) AS nb_benef
RETURN avg(nb_benef) AS moyenne_beneficiaires
""".strip()
