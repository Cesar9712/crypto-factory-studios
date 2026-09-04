from __future__ import annotations

import hashlib
import json
import re
from typing import Callable


TIER_META = {
    "free": {
        "price": "0.00", "label": "FREE", "difficulty": "BEGINNER", "license": "PERSONAL",
        "depth": "Entrega una solución directa y práctica. Incluye pasos claros, una lista de comprobación corta y evita relleno.",
    },
    "starter": {
        "price": "1.99", "label": "STARTER", "difficulty": "INTERMEDIATE", "license": "PERSONAL",
        "depth": "Desarrolla la solución por fases. Incluye decisiones clave, checklist, dos alternativas y una sección de errores comunes.",
    },
    "creator": {
        "price": "4.99", "label": "CREATOR", "difficulty": "ADVANCED", "license": "COMMERCIAL",
        "depth": "Trabaja en varias fases: diagnóstico, estrategia, ejecución y control de calidad. Incluye variantes reutilizables y criterios de éxito.",
    },
    "pro": {
        "price": "9.99", "label": "PRO", "difficulty": "EXPERT", "license": "COMMERCIAL",
        "depth": "Construye un sistema profesional completo con diagnóstico, estrategia, ejecución, scoring, casos límite, QA y entregables reutilizables.",
    },
    "unlimited": {
        "price": "19.99", "label": "UNLIMITED", "difficulty": "EXPERT", "license": "EXTENDED",
        "depth": "Opera como un equipo senior multidisciplinario. Diseña un sistema end-to-end con auditoría, estrategia, ejecución, métricas, riesgos, QA, variantes, plantillas reutilizables y plan de iteración.",
    },
}


# Three practical use cases for every category currently exposed by Prompt Factory.
# Price/depth is assigned deterministically across the five platform price tiers.
CATEGORY_SPECS = [
    ("AI AGENTS", "AI Agents", [
        ("Agente de soporte inteligente", "arquitecto de agentes de IA y CX", "diseñar un agente de soporte que clasifique, responda y escale consultas con seguridad", "arquitectura del agente, intents, herramientas, políticas, prompts y casos de prueba"),
        ("Workflow multiagente autónomo", "arquitecto senior de sistemas multiagente", "diseñar un flujo multiagente con roles, handoffs, memoria, herramientas y recuperación ante fallos", "mapa de agentes, contratos de entrada/salida, orquestación, observabilidad y pruebas"),
        ("Evaluador y QA de agentes", "especialista en evaluación, seguridad y reliability de agentes", "crear una batería de evaluaciones para medir exactitud, seguridad, coste, latencia y robustez de un agente", "dataset de evaluación, rúbrica, casos adversariales, métricas y criterios de release"),
    ]),
    ("MARKETING", "Marketing", [
        ("Campaña de marketing 360", "estratega senior de marketing", "crear una campaña multicanal alineada a audiencia, oferta, presupuesto y objetivo", "posicionamiento, mensajes, canales, calendario, KPIs y experimentos"),
        ("Funnel de lanzamiento", "growth marketer y especialista CRO", "diseñar un funnel completo de lanzamiento desde adquisición hasta conversión y retención", "funnel, activos, secuencias, eventos, métricas y plan A/B"),
        ("Sistema de crecimiento repetible", "director de growth", "construir un sistema mensual de adquisición, activación, retención, referral y monetización", "growth loops, backlog de experimentos, scoring ICE, dashboard y cadencia operativa"),
    ]),
    ("SOCIAL MEDIA", "Social Media", [
        ("Calendario social de 30 días", "social media strategist", "crear un calendario de contenido de 30 días adaptado a marca, audiencia y plataforma", "calendario, pilares, formatos, hooks, CTA y métricas"),
        ("Guiones virales para short-form", "guionista de contenido short-form", "crear guiones breves con hook fuerte, retención y CTA sin caer en clickbait engañoso", "guiones, hooks alternativos, B-roll, captions y CTA"),
        ("Motor de contenido multiplataforma", "director de contenido y distribución", "convertir una idea central en un sistema de piezas coordinadas para varias redes", "pieza madre, derivados por canal, calendario, reutilización y tracking"),
    ]),
    ("BUSINESS", "Business", [
        ("Modelo de negocio rentable", "estratega de negocios", "analizar una idea y convertirla en un modelo de negocio viable con supuestos explícitos", "propuesta de valor, segmentos, canales, costes, ingresos, riesgos y validación"),
        ("Pricing y unit economics", "especialista en pricing y finanzas operativas", "diseñar precios y paquetes sostenibles a partir de valor, costes y comportamiento esperado", "tiers, márgenes, CAC/LTV objetivo, sensibilidad y experimentos"),
        ("Sistema operativo de empresa", "COO y arquitecto de operaciones", "crear un sistema operativo ligero para ejecutar prioridades, procesos, métricas y reuniones", "SOPs, RACI, scorecard, cadencias, riesgos y mejora continua"),
    ]),
    ("CODING", "Coding", [
        ("Debugger sistemático", "ingeniero senior de software", "diagnosticar un bug a partir de síntomas, logs y código sin inventar causas", "hipótesis priorizadas, pruebas mínimas, fix, regresiones y verificación"),
        ("Code review y refactor", "staff software engineer", "auditar código por corrección, legibilidad, seguridad, rendimiento y mantenibilidad", "hallazgos priorizados, patch propuesto, tests y deuda técnica"),
        ("Arquitectura production-ready", "arquitecto de software", "diseñar una arquitectura lista para producción con interfaces, persistencia, seguridad, observabilidad y despliegue", "diagrama textual, componentes, contratos, modelo de datos, CI/CD y runbook"),
    ]),
    ("WEB DEVELOPMENT", "Web Development", [
        ("Landing page de alta conversión", "product designer y frontend engineer", "definir una landing responsive rápida, accesible y enfocada en conversión", "estructura, copy, componentes, estados, eventos y criterios de aceptación"),
        ("SaaS full-stack blueprint", "arquitecto full-stack SaaS", "diseñar un SaaS completo desde autenticación hasta billing, datos y administración", "arquitectura, esquema, APIs, permisos, UI, seguridad, QA y deploy"),
        ("Auditoría web performance + security", "ingeniero web de performance y seguridad", "auditar una aplicación web y producir un plan medible de mejora", "matriz de hallazgos, severidad, Core Web Vitals, seguridad, fixes y validación"),
    ]),
    ("GAME DEVELOPMENT", "Game Development", [
        ("Core loop de videojuego", "game designer senior", "diseñar un core loop divertido con progresión, feedback y objetivos claros", "loop minuto-a-minuto, metajuego, recompensas, dificultad y métricas"),
        ("Economía y balance de juego", "economy designer", "diseñar una economía equilibrada evitando inflación, pay-to-win y cuellos de botella", "fuentes/sumideros, curvas, tablas, simulación conceptual y alertas"),
        ("GDD + plan de producción", "director de juego y productor", "convertir un concepto en un GDD ejecutable con alcance realista y roadmap", "GDD, sistemas, contenido, UX, arte, tech, hitos, QA y riesgos"),
    ]),
    ("WEB3", "Web3", [
        ("DApp token-gated", "arquitecto Web3", "diseñar una dApp con acceso token-gated sin depender de lógica crítica en el cliente", "flujos wallet, contratos, backend, firmas, permisos y UX de errores"),
        ("Especificación segura de smart contract", "ingeniero de smart contracts orientado a seguridad", "producir una especificación implementable con invariantes y checklist de seguridad", "interfaces, estados, eventos, controles, invariantes, tests y amenazas"),
        ("Arquitectura Web3 production-ready", "arquitecto Web3 y backend", "diseñar una arquitectura híbrida on-chain/off-chain robusta y operable", "contratos, indexación, API, jobs, reorg handling, claves, monitoreo y recovery"),
    ]),
    ("CRYPTO", "Crypto", [
        ("Due diligence de token", "analista de activos digitales", "estructurar una investigación neutral de un token sin convertirla en recomendación financiera", "tokenomics, equipo, producto, liquidez, riesgos, catalizadores y preguntas abiertas"),
        ("Mapa de riesgo de cartera cripto", "analista de riesgo", "evaluar concentraciones y escenarios de riesgo de una cartera con supuestos transparentes", "exposición, correlaciones cualitativas, escenarios, drawdown hipotético y controles"),
        ("Radar de mercado cripto", "research lead de mercados digitales", "crear un sistema de seguimiento de mercado basado en datos verificables y señales claramente etiquetadas", "dashboard conceptual, fuentes, indicadores, alertas, régimen y protocolo de revisión"),
    ]),
    ("DESIGN", "Design", [
        ("Sistema de identidad de marca", "brand designer", "traducir estrategia de marca en un sistema visual coherente y aplicable", "dirección visual, tipografía, color, composición, iconografía, do/don't y aplicaciones"),
        ("Auditoría UX/UI", "product designer senior", "detectar fricción de experiencia e interfaz y priorizar mejoras por impacto", "heurísticas, issues, severidad, journey, wireframe textual y backlog"),
        ("Design system escalable", "design systems lead", "definir un sistema de diseño consistente para producto web/móvil", "tokens, componentes, variantes, estados, accesibilidad, gobernanza y documentación"),
    ]),
    ("IMAGE GENERATION", "Image Generation", [
        ("Hero visual de producto", "art director de imagen generativa", "crear instrucciones visuales precisas para un hero de producto premium", "prompt principal, negative guidance, composición, lente, luz y variantes"),
        ("Personaje consistente multiimagen", "character art director", "diseñar un sistema de prompts para mantener identidad visual consistente entre múltiples escenas", "character bible, anclas visuales, escenas, poses, iluminación y control de consistencia"),
        ("Dirección de arte de campaña", "creative director generativo", "crear una campaña visual coherente con múltiples piezas y formatos", "concepto, art bible, prompts por pieza, adaptaciones, QA visual y matriz de consistencia"),
    ]),
    ("VIDEO GENERATION", "Video Generation", [
        ("Storyboard para anuncio corto", "director creativo audiovisual", "convertir una oferta en un anuncio breve con escenas claras y ritmo de retención", "beat sheet, storyboard, prompts de escena, cámara, audio y CTA"),
        ("Prompt cinematográfico multi-escena", "director y prompt designer de video", "diseñar secuencias de video generativo con continuidad de personaje, cámara y atmósfera", "shot list, continuidad, prompts por plano, transiciones y negative guidance"),
        ("Sistema de campaña de video", "creative producer", "planificar una familia de anuncios de video reutilizando concepto, assets y aprendizajes", "matriz de conceptos, variantes, guiones, shots, testing y métricas creativas"),
    ]),
    ("CONTENT CREATION", "Content Creation", [
        ("Artículo útil y original", "editor senior", "crear un artículo orientado a intención real del lector con estructura clara y evidencia", "outline, borrador, ejemplos, verificaciones, CTA y checklist editorial"),
        ("Newsletter recurrente", "editor de newsletters", "crear un formato recurrente que combine valor, voz propia y consistencia", "plantilla, secciones, asunto, edición, CTA y calendario"),
        ("Sistema editorial completo", "content operations lead", "construir un sistema editorial desde ideación hasta distribución y reciclaje", "pilares, pipeline, briefs, QA, calendario, distribución, métricas y retroalimentación"),
    ]),
    ("SEO", "SEO", [
        ("Keyword cluster por intención", "SEO strategist", "agrupar temas y consultas por intención y relación semántica sin inventar volúmenes", "clusters, intención, páginas objetivo, prioridad y huecos de contenido"),
        ("Brief SEO on-page", "editor SEO", "crear un brief accionable que cubra intención, estructura, entidades y experiencia de lectura", "title, H1/H2, preguntas, entidades, enlaces, schema sugerido y QA"),
        ("Topical authority roadmap", "SEO lead", "diseñar una arquitectura de autoridad temática y crecimiento orgánico medible", "mapa temático, hubs/spokes, enlazado, roadmap, KPIs y actualización"),
    ]),
    ("YOUTUBE", "YouTube", [
        ("Ideas de título y miniatura", "estratega de packaging para YouTube", "crear pares título-miniatura claros y curiosos sin promesas engañosas", "conceptos, títulos, texto visual, tensión de curiosidad y criterios A/B"),
        ("Guion de alta retención", "guionista de YouTube", "estructurar un video que mantenga interés mediante progresión, payoff y claridad", "hook, open loops, bloques, pattern interrupts, CTA y cierre"),
        ("Sistema de crecimiento de canal", "YouTube growth lead", "crear una estrategia repetible de temas, packaging, producción, publicación y aprendizaje", "pilares, series, calendario, experimentos, métricas y revisión mensual"),
    ]),
    ("AUTOMATION", "Automation", [
        ("Automatizador de tarea repetitiva", "automation engineer", "convertir una tarea manual en un flujo automatizado con entradas, reglas y manejo de errores", "mapa AS-IS/TO-BE, triggers, acciones, excepciones y pruebas"),
        ("Workflow no-code robusto", "especialista en automatización no-code", "diseñar un workflow entre aplicaciones con idempotencia, reintentos y trazabilidad", "trigger, pasos, datos, filtros, retries, alertas y runbook"),
        ("Arquitectura de automatización empresarial", "automation architect", "crear una capa de automatización gobernada para múltiples procesos y equipos", "catálogo de flujos, prioridades, seguridad, observabilidad, SLAs, ownership y roadmap"),
    ]),
    ("PRODUCTIVITY", "Productivity", [
        ("Plan diario de foco", "coach de productividad basado en sistemas", "convertir prioridades y restricciones reales en un plan diario ejecutable", "top outcomes, time blocks, límites WIP, pausas y cierre del día"),
        ("Planificador de proyecto", "project manager", "transformar un objetivo en hitos, tareas, dependencias y riesgos", "WBS, hitos, responsables, dependencias, riesgos y cadencia"),
        ("Sistema operativo personal", "diseñador de sistemas de productividad", "crear un sistema sostenible para capturar, priorizar, ejecutar y revisar compromisos", "inbox, proyectos, calendario, revisiones, métricas y reglas de mantenimiento"),
    ]),
    ("EDUCATION", "Education", [
        ("Plan de clase adaptativo", "diseñador instruccional", "crear una clase ajustada a nivel, objetivos, tiempo y conocimientos previos", "objetivos, activación, explicación, práctica, evaluación y adaptación"),
        ("Generador de evaluación con rúbrica", "especialista en assessment", "crear una evaluación alineada a objetivos y una rúbrica clara para corregir", "blueprint, preguntas, respuestas esperadas, rúbrica y errores frecuentes"),
        ("Currículo completo de curso", "learning experience designer", "diseñar un curso progresivo con resultados medibles y práctica auténtica", "outcomes, módulos, lecciones, proyectos, evaluaciones, recursos y mejora"),
    ]),
    ("RESEARCH", "Research", [
        ("Síntesis de fuentes", "research analyst", "sintetizar múltiples fuentes separando evidencia, consenso, desacuerdo e incertidumbre", "hallazgos, tabla de evidencia, contradicciones, límites y preguntas pendientes"),
        ("Research de competidores", "competitive intelligence analyst", "comparar competidores de forma verificable y orientada a decisiones", "matriz, posicionamiento, producto, pricing, canales, fortalezas, huecos y oportunidades"),
        ("Protocolo de deep research", "research lead", "diseñar y ejecutar conceptualmente una investigación profunda reproducible", "preguntas, hipótesis, estrategia de fuentes, criterios, síntesis, confidence y auditoría"),
    ]),
    ("DATA ANALYSIS", "Data Analysis", [
        ("Análisis exploratorio de datos", "data analyst", "estructurar un EDA que detecte calidad, distribuciones, relaciones y anomalías", "checks de calidad, estadísticas, segmentación, anomalías, visuales sugeridos y conclusiones"),
        ("Diseño de dashboard KPI", "analytics engineer", "definir un dashboard que conecte métricas con decisiones y evite vanity metrics", "north star, KPIs, fórmulas, dimensiones, alertas, layout y data requirements"),
        ("Informe ejecutivo de insights", "data strategy lead", "convertir análisis complejos en decisiones, impacto y próximos experimentos", "resumen ejecutivo, evidencia, magnitud, drivers, riesgos, acciones y seguimiento"),
    ]),
    ("SALES", "Sales", [
        ("Guion de discovery consultivo", "sales consultant", "preparar una conversación de discovery centrada en problema, impacto, prioridad y fit", "agenda, preguntas, señales, notas, criterios de avance y follow-up"),
        ("Manejo de objeciones", "sales enablement lead", "crear respuestas útiles a objeciones sin manipulación ni presión indebida", "mapa de objeciones, diagnóstico, respuesta, evidencia, pregunta de avance y límites"),
        ("Playbook comercial completo", "VP Sales", "construir un playbook repetible desde ICP y prospección hasta cierre y handoff", "ICP, mensajes, stages, qualification, cadencias, assets, KPIs, coaching y QA"),
    ]),
    ("COPYWRITING", "Copywriting", [
        ("Página de venta clara", "conversion copywriter", "escribir una página de venta que conecte problema, valor, evidencia y CTA sin exageraciones", "headline, secciones, objeciones, prueba, CTA y variantes"),
        ("Secuencia de emails de conversión", "email copy strategist", "crear una secuencia que eduque, construya confianza y mueva a la siguiente acción", "asuntos, emails, CTA, lógica de secuencia y tests"),
        ("Sistema de voz y copy de marca", "brand copy director", "crear un sistema reutilizable de voz, mensajes y patrones de copy para múltiples canales", "voice chart, mensajes, lexicon, ejemplos, prohibiciones, plantillas y QA"),
    ]),
    ("E-COMMERCE", "E-Commerce", [
        ("Ficha de producto optimizada", "e-commerce copywriter", "crear una ficha de producto que explique valor, uso, especificaciones y objeciones con claridad", "título, bullets, descripción, FAQ, SEO y CTA"),
        ("Auditoría de conversión de tienda", "CRO specialist de e-commerce", "detectar fricciones desde landing hasta checkout y priorizar mejoras", "funnel, issues, severidad, quick wins, tests y métricas"),
        ("Sistema de crecimiento de catálogo", "e-commerce growth lead", "diseñar un sistema para surtido, merchandising, adquisición, retención y rentabilidad", "segmentación, bundles, merchandising, CRM, experimentos, métricas y calendario"),
    ]),
    ("OTHER", "General", [
        ("Matriz de decisión compleja", "facilitador de decisiones", "comparar opciones con criterios explícitos, incertidumbre y trade-offs", "criterios, pesos, matriz, sensibilidad, riesgos y recomendación condicionada"),
        ("Facilitador de reunión productiva", "facilitador ejecutivo", "convertir una reunión en decisiones, responsables y próximos pasos verificables", "agenda, preguntas, decisiones, action items, owners, fechas y follow-up"),
        ("Brief maestro de proyecto", "program manager", "transformar una idea ambigua en un brief ejecutable y alineado", "objetivo, alcance, no-alcance, usuarios, requisitos, hitos, riesgos, métricas y decisiones abiertas"),
    ]),
]


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:58] or "prompt"


def _ids(slug: str) -> tuple[str, str, str]:
    digest = hashlib.sha256(f"cfs-official-catalog-v1:{slug}".encode()).hexdigest()[:24]
    return f"prm_seed_{digest}", f"lst_seed_{digest}", f"prompt_catalog_{digest}"


def _prompt_text(*, role: str, goal: str, deliverable: str, tier: dict) -> str:
    return f"""Actúa como {role}.

OBJETIVO
{goal}.

CONTEXTO DEL USUARIO
{{{{contexto}}}}

OBJETIVO ESPECÍFICO / RESULTADO DESEADO
{{{{objetivo}}}}

AUDIENCIA O USUARIO FINAL
{{{{audiencia}}}}

RESTRICCIONES, RECURSOS O LÍMITES
{{{{restricciones}}}}

MODO DE TRABAJO — {tier['label']}
{tier['depth']}

PROCESO OBLIGATORIO
1. Resume lo que entendiste en un máximo de 5 puntos y separa hechos de supuestos.
2. Detecta información faltante que cambie materialmente el resultado. Si no es imprescindible, declara un supuesto razonable y continúa.
3. Analiza opciones y trade-offs antes de elegir una dirección.
4. Ejecuta la solución con suficiente detalle para poder usarla inmediatamente.
5. Revisa consistencia, riesgos, contradicciones y puntos débiles antes de entregar.
6. Propón el siguiente experimento o iteración de mayor impacto.

REGLAS DE CALIDAD
- No inventes datos, métricas, fuentes ni resultados. Señala claramente cualquier supuesto.
- Prioriza acciones concretas sobre teoría genérica.
- Adapta lenguaje, profundidad y ejemplos a la audiencia indicada.
- Cuando haya varias opciones válidas, compáralas y explica cuándo usar cada una.
- Si el contexto implica una decisión sensible o de alto impacto, presenta incertidumbre y límites con claridad.

FORMATO DE ENTREGA
{deliverable}.
Termina con: (1) checklist de ejecución, (2) riesgos/errores a evitar y (3) tres próximos pasos priorizados."""


def _system_instructions(role: str, tier_label: str) -> str:
    return (
        f"Eres {role}. Trabajas en nivel {tier_label}. "
        "Sé preciso, útil y orientado a ejecución. No inventes hechos; distingue evidencia, inferencias y supuestos. "
        "Respeta privacidad, seguridad, propiedad intelectual y límites profesionales aplicables."
    )


def iter_catalog() -> list[dict]:
    tiers = ["free", "starter", "creator", "pro", "unlimited"]
    rows: list[dict] = []
    item_index = 0
    for category_index, (category, subcategory, specs) in enumerate(CATEGORY_SPECS):
        for use_index, (title, role, goal, deliverable) in enumerate(specs):
            tier_id = tiers[item_index % len(tiers)]
            tier = TIER_META[tier_id]
            slug = f"cfs-{_slugify(title)}"
            rows.append({
                "slug": slug,
                "title": title,
                "description": f"Prompt oficial {tier['label']} para {goal}. Diseñado para entregar {deliverable}.",
                "role": role,
                "goal": goal,
                "deliverable": deliverable,
                "category": category,
                "subcategory": subcategory,
                "tier_id": tier_id,
                "tier": tier,
                "tags": ["cfs-official", f"tier-{tier_id}", _slugify(category), _slugify(subcategory)],
                "models": ["ChatGPT", "Claude", "Gemini"],
                "featured": 1 if tier_id == "unlimited" or (tier_id == "free" and category_index % 6 == 0) else 0,
                "order": item_index,
            })
            item_index += 1
    return rows


CATALOG = iter_catalog()
CATALOG_COUNT = len(CATALOG)
CATALOG_CATEGORIES = len(CATEGORY_SPECS)
CATALOG_PRICES = tuple(sorted({meta["price"] for meta in TIER_META.values()}, key=float))


def ensure_official_prompt_catalog(db, now: Callable[[], int]) -> int:
    """Idempotently seed the official marketplace catalog without overwriting sales/reviews.

    The official catalog is attached to the oldest active platform_owner. If no owner exists,
    seeding is skipped rather than creating a privileged service account implicitly.
    """
    seller = db.one(
        "SELECT id FROM users WHERE role='platform_owner' AND disabled=0 ORDER BY created_at ASC,id ASC LIMIT 1"
    )
    if not seller:
        return 0

    seller_id = seller["id"]
    t = now()
    variables = [
        {"name": "contexto", "label": "Contexto", "required": True, "default": ""},
        {"name": "objetivo", "label": "Objetivo específico", "required": True, "default": ""},
        {"name": "audiencia", "label": "Audiencia", "required": False, "default": "general"},
        {"name": "restricciones", "label": "Restricciones", "required": False, "default": "ninguna adicional"},
    ]
    variables_json = json.dumps(variables, ensure_ascii=False, separators=(",", ":"))

    db.execute(
        """INSERT INTO seller_balances(seller_id,available_usd,pending_usd,lifetime_earnings_usd,platform_fees_usd,updated_at)
           VALUES(?,0,0,0,0,?) ON CONFLICT(seller_id) DO NOTHING""",
        (seller_id, t),
    )

    seeded = 0
    for row in CATALOG:
        tier = row["tier"]
        prompt_id, listing_id, product_id = _ids(row["slug"])
        prompt_text = _prompt_text(
            role=row["role"], goal=row["goal"], deliverable=row["deliverable"], tier=tier
        )
        system_instructions = _system_instructions(row["role"], tier["label"])
        content_hash = hashlib.sha256(
            (prompt_text + "\n---SYSTEM---\n" + system_instructions + "\n---VARS---\n" + variables_json).encode()
        ).hexdigest()
        tags_json = json.dumps(row["tags"], ensure_ascii=False, separators=(",", ":"))
        models = list(row["models"])
        if row["category"] == "IMAGE GENERATION":
            models = ["Midjourney", "Flux", "Stable Diffusion"]
        elif row["category"] == "VIDEO GENERATION":
            models = ["Sora", "Runway", "Kling", "Veo"]
        elif row["category"] in {"CODING", "WEB DEVELOPMENT", "GAME DEVELOPMENT", "WEB3"}:
            models = ["ChatGPT", "Claude", "Codex", "Cursor"]
        elif row["category"] == "AI AGENTS":
            models = ["ChatGPT", "OpenAI API", "Claude", "Gemini"]
        models_json = json.dumps(models, ensure_ascii=False, separators=(",", ":"))

        existed = db.one("SELECT prompt_id FROM prompts WHERE prompt_id=?", (prompt_id,))
        db.execute(
            """INSERT INTO prompts(
                 prompt_id,owner_id,slug,title,description,prompt_text,system_instructions,category,subcategory,
                 tags_json,ai_models_json,difficulty,language,variables_json,visibility,status,content_hash,created_at,updated_at,archived_at
               ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0)
               ON CONFLICT(prompt_id) DO NOTHING""",
            (
                prompt_id, seller_id, row["slug"], row["title"], row["description"], prompt_text,
                system_instructions, row["category"], row["subcategory"], tags_json, models_json,
                tier["difficulty"], "es", variables_json, "FOR_SALE", "ACTIVE", content_hash, t, t,
            ),
        )
        db.execute(
            """INSERT INTO prompt_versions(
                 version_id,prompt_id,version_number,prompt_text,system_instructions,variables_json,changelog,content_hash,created_at
               ) VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(prompt_id,version_number) DO NOTHING""",
            (f"ver_{prompt_id[4:]}", prompt_id, 1, prompt_text, system_instructions, variables_json,
             "Official catalog seed v1", content_hash, t),
        )
        db.execute(
            """INSERT INTO products(product_id,label,description,price_usd,entitlement_key,active,created_at)
               VALUES(?,?,?,?,?,?,?) ON CONFLICT(product_id) DO UPDATE SET
               label=excluded.label,description=excluded.description,price_usd=excluded.price_usd,
               entitlement_key=excluded.entitlement_key,active=excluded.active""",
            (
                product_id, row["title"], row["description"], tier["price"],
                f"prompt_listing:{listing_id}", 0 if tier["price"] == "0.00" else 1, t,
            ),
        )
        preview = (
            f"{tier['label']} · {row['category']} — {row['goal'].capitalize()}. "
            f"Entrega: {row['deliverable']}. Incluye variables reutilizables y control de calidad."
        )
        examples_json = json.dumps(
            [
                f"Úsalo para {row['goal']} con un contexto real de tu proyecto.",
                f"Personaliza audiencia, objetivo y restricciones antes de ejecutar.",
            ],
            ensure_ascii=False,
            separators=(",", ":"),
        )
        db.execute(
            """INSERT INTO prompt_listings(
                 listing_id,prompt_id,seller_id,product_id,price_usd,pricing_model,license_type,preview_text,
                 examples_json,status,commission_bps,featured,sales_count,rating_avg,rating_count,created_at,updated_at
               ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,0,0,0,?,?)
               ON CONFLICT(prompt_id) DO UPDATE SET
                 price_usd=excluded.price_usd,pricing_model=excluded.pricing_model,license_type=excluded.license_type,
                 preview_text=excluded.preview_text,examples_json=excluded.examples_json,status='PUBLISHED',
                 commission_bps=excluded.commission_bps,featured=excluded.featured,updated_at=excluded.updated_at""",
            (
                listing_id, prompt_id, seller_id, product_id, tier["price"], "FIXED", tier["license"],
                preview, examples_json, "PUBLISHED", 800, row["featured"], t, t,
            ),
        )
        if not existed:
            seeded += 1

    return seeded
