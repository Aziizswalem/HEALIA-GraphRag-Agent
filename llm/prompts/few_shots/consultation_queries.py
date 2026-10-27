"""Few-shot examples (schema-faithful, minimal, deterministic).

Includes negative guidance (BAD vs GOOD).
"""

FEW_SHOTS = """
# HARD Example 1 - Multi-hop + aggregation
Question: Quels produits sont les plus prescrits dans les bulletins de soins ?
Cypher:
MATCH (d:BulletinSoinPrestationDetail)-[:USES_PRODUCT]->(p:Product)
RETURN p.id AS product_id, p.name AS nom, count(d) AS nb_prescriptions
ORDER BY nb_prescriptions DESC


# Negative guidance (BAD vs GOOD)
# BAD: adds implicit filters/limit and extra fields
# MATCH (b:Beneficiaire {active: true}) RETURN b.id, b.first_name, b.last_name LIMIT 50
# GOOD: only requested constraints/fields; no implicit filters/limit
# MATCH (b:Beneficiaire)-[:A_BULLETIN]->(bs:BulletinSoin)
# WITH b, count(bs) AS nombre_bulletins
# WHERE nombre_bulletins > 50
# RETURN b.id AS beneficiaire_id, nombre_bulletins
"""
