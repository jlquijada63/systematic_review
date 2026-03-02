# AGENTS.md — Guía operativa del agente de metaanálisis pronóstico

## OVERVIEW

Este repositorio implementa un agente motorizado por Inteligencia Artificial (IA) para la extraccion de datos y valoracion de los mismos, de un articulo cientifico para su posible inclusion en un posterior **metaanalisis**

## Objetivos y alcance

- La entrada sera un articulo determinado en formato pdf
- Extraer datos estructurados segun los criterios del checklist CHARMS-PF
- Evaluar riesgo de sesgo para articulos cientificos referidos a factores pronostico (QUIPS).

```mermeid
  A[articulo-pdf] --> B [Extracion datos CHARMS-PF]
  B --> C [evaluacion riesgo bias QUIPS]
```


## Pipeline de extracción

1) Ingesta de referencias: normalizar metadatos (PMID/DOI/título/autores/año).
2) Deduplicación: reglas deterministas (PMID/DOI) + similitud difusa (título/autores).
3) Cribado T/A: clasificador con justificación textual y etiqueta de incertidumbre.
4) Recuperación full-text: preferir HTML/PMC cuando exista; PDF si es accesible.
5) Parsing:
   - PDF→texto/estructura (GROBID opcional).
   - detectar tablas y extraer resultados por outcome y por nivel de ajuste.
6) Extracción estructurada (Pydantic):
   - Study
   - OutcomeDefinition
   - EffectEstimate (tipo, valor, SE/CI, ajustado/no, covariables)
   - Provenance (fuente + ubicación + evidencia)
7) Manejo de missing/conflict:
   - Missing: null + razón + "qué se intentó".
   - Conflicto: guardar ambas versiones + abrir "approval gate".
8) Persistencia:
   - Parquet/SQLite para datos estructurados.
   - JSONL para logs de decisión.

## Riesgo de sesgo

- Seleccionar herramienta:
  - QUIPS: factores pronósticos.
  - NOS: cohort/case-control cuando QUIPS no aplica.
  - ROBINS-I: si el factor es una exposición/intervención comparativa.
- Salida:
  - Juicio por dominio + juicio global + notas + evidencia.

## Síntesis estadística

- Preparación:
  - Transformar a escala log cuando aplique (log(HR), log(OR), log(RR)).
  - Derivar SE desde IC95% cuando proceda.
- Modelos:
  - Efectos fijos (IV).
  - Efectos aleatorios (REML; alternativa DL).
  - Intervalos: Wald o HKSJ (según plan).
- Heterogeneidad:
  - Q, I², tau², intervalo de predicción (si procede).
- Exploración:
  - Subgrupos (por definición de outcome, medición del factor, setting).
  - Meta-regresión (si hay suficientes estudios).
- Sensibilidad:
  - solo ajustados vs solo no ajustados
  - excluir alto RoB
  - leave-one-out
  - preprints aparte

## Incertidumbre y reporte

- Reportar:
  - Forest plots, tablas de efectos, heterogeneidad (I²/tau²) y PI cuando se use.
  - PRISMA flow diagram + checklist.
  - MOOSE checklist (observacionales).
- Advertir:
  - Meta-regresión es asociacional (no causal).
  - Heterogeneidad puede ser alta por definiciones y mediciones.

## Reproducibilidad, logging, versionado y auditoría

- Cada ejecución crea `outputs/runs/<run_id>/` con:
  - config.yaml copiada (inmutable)
  - queries.txt
  - decisions.jsonl (inclusión/exclusión con razones)
  - extracted.parquet (staging + final)
  - rob.parquet
  - stats.json (métodos + resultados)
  - report.md/pdf
- Versionado:
  - fijar dependencias en `pyproject.toml` + lockfile
  - registrar versión del modelo y del agente
- Auditoría:
  - trazas (si habilitadas) + export local de eventos críticos.

## Ética y privacidad

- No incluir datos personales sensibles (PII/PHI).
- Respetar licencias y acceso a texto completo.
- Señalar preprints como no revisados por pares.
- El output no es guía clínica; requiere revisión humana.

## Tests y validación

- Unit tests:
  - validación de config y esquemas
  - dedupe determinista y difuso
  - extracción con casos “gold”
  - cálculo meta-analítico con dataset pequeño conocido
- Integración:
  - ejecución end-to-end con 5–10 PMIDs de fixture
- Validación estadística:
  - comparar con outputs de R/metafor o RevMan en un caso de referencia.

## Dependencias y entorno

- Python >= 3.10
- openai-agents
- pydantic, httpx, pandas/polars, pyarrow
- (opcional) grobid client, sqlalchemy, redis
- (opcional) rpy2 o llamada a R para verificación cruzada

## Comandos de ejemplo

Instalar:
  pip install -e .

Ejecutar una revisión:
  python -m agent_app.main --config configs/example_review.yaml

Correr tests:
  pytest -q

Empaquetar artefactos:
  python -m agent_app.tools.io_artifacts bundle --run outputs/runs/<run_id>/
