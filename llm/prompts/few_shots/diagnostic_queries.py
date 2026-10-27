"""Few-shot examples (schema-faithful, minimal, deterministic).

Includes date filtering and string matching without inventing functions/properties.
"""

FEW_SHOTS = """
# HARD Example 1 - String matching (CONTAINS)
Question: Quels médecins ont la spécialité cardiologie ?
Cypher:
MATCH (p:HmsPhysician)-[:HAS_SPECIALTY]->(s:PhysicianSpecialty)
WHERE toLower(s.name) CONTAINS 'cardio'
RETURN p.id AS physician_id, p.name AS nom, s.name AS specialite
ORDER BY nom

# HARD Example 2 - Date filter (simple >= comparison)
Question: Liste des bulletins de soins après une date donnée.
Cypher:
MATCH (bs:BulletinSoin)
WHERE bs.validation_date >= $date_min
RETURN bs.id AS bs_id, bs.validation_date AS validation_date
ORDER BY validation_date DESC

# Negative guidance (BAD vs GOOD)
# BAD: uses invented functions like month()/year() or apoc.date.*
# GOOD: simple comparisons (>=, <=) on existing date fields
"""
