"""Few-shot examples (schema-faithful, minimal, deterministic).

Includes multi-hop, aggregation, and negative guidance.
"""

FEW_SHOTS = """
# HARD Example 1 - Aggregation (SUM) + grouping via WITH (no SQL GROUP BY)
Question: Quel est le montant total pris en charge par assureur ?
Cypher:
MATCH (bs:BulletinSoin)-[:COVERED_BY]->(a:Assureur)
RETURN a.name AS assureur, sum(bs.total_pec) AS total_pec
ORDER BY total_pec DESC

# HARD Example 2 - Multi-hop + CONTAINS (string match)
Question: Quels produits dont le nom contient 'radio' apparaissent dans les prestations ?
Cypher:
MATCH (d:BulletinSoinPrestationDetail)-[:USES_PRODUCT]->(p:Product)
WHERE toLower(p.name) CONTAINS 'radio'
RETURN p.id AS product_id, p.name AS nom
ORDER BY nom

# Negative guidance (BAD vs GOOD)
# BAD: adds implicit filters (active=true) or LIMIT without being asked
# GOOD: only explicit constraints/fields; no implicit filters/limit
"""