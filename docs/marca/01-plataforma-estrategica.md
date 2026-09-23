# 01 · Plataforma Estratégica de Marca (Brand Core)

> **Entregable de Fase 1.** Sintetiza por qué existe Luka, cómo se diferencia y qué principios no se negocian.
> Fuentes primarias: `luka/README.md`, `luka/AGENTS.md`, `luka/prompts/core_prompt.md`, `luka/prompt.md`, `luka/docs/*`, `luka-llm-research/FALENCIAS.md`, backlog Jira `STK` (179 issues: 131 finalizadas, 48 abiertas, consultado 2026-09-23).
> Marco: Marty Neumeier, *The Brand Gap* — el cerebro filtra el exceso y solo registra lo diferente; una marca fuerte hace que la competencia parezca irrelevante (*zag when others zig*).

---

## 1. Ficha de marca

| Campo | Valor |
|---|---|
| Nombre de producto | Luka (logotipo: **LUKA**) |
| Categoría | Asistente financiero personal conversacional |
| Canal principal | WhatsApp (Meta WhatsApp Business API) |
| Canal secundario | Dashboard web (`luka_frontend`) |
| Mercado inicial | Argentina, español rioplatense, moneda ARS |
| Estado | MVP en producción controlada; releases 1–3 desplegadas (ver §9) |
| Operación | Bot + LLM (Gemini 3.1 Flash-Lite; fachada multi-proveedor), FastAPI, Supabase/Postgres, Redis |

---

## 2. Propósito

**Existimos para que cualquier persona pueda hacerse cargo de su dinero sin aprender a ser contador, sin instalar otra app y sin culpa.**

El producto nace de una observación de mercado honesta: «para las personas que nunca pudieron mantener sus finanzas organizadas, LUKA elimina la barrera de entrada: no necesitás disciplina de contabilidad ni aprender a usar una herramienta nueva. Solo necesitás WhatsApp, que ya tenés en tu teléfono» (`luka/README.md:28-30`).

## 3. Misión y visión

- **Misión.** Registrar y ordenar las finanzas personales en lenguaje natural por WhatsApp, devolviendo balances, límites y educación financiera sin fricción bancaria.
- **Visión.** Que Luka sea la primera capa de claridad financiera del usuario: «ver patrones, entender en qué gastás y tomar mejores decisiones con tu dinero — todo desde el chat que ya usás todos los días» (`luka/README.md:32-34`).

---

## 4. Escalera de valor (Neumeier: de features a identificación)

Las marcas maduras suben cuatro escalones. Luka hoy vive entre *Benefits* y *Experience*; la marca debe hablar desde *Identification*.

| Escalón | Luka | Evidencia |
|---|---|---|
| **Features — qué es** | Asistente financiero por WhatsApp que interpreta lenguaje natural y registra ingresos/egresos. | `README.md:24`; `AGENTS.md:3` |
| **Benefits — qué hace** | Registra en segundos, categoriza solo, multi-movimiento, detecta duplicados, responde al instante, recuerda pagos y límites, entrega balances y gráficos. | `README.md:36-44`; `docs/features.md` |
| **Experience — qué siente** | Control, orden y alivio frente a la ansiedad del dinero; el costo de registrar baja a un mensaje. | `prompt.md` (búsqueda de calidez); backlog: «sentirse como un amigo» |
| **Identification — quién es** | Una persona financiera consciente y pragmática: domina sus recursos sin sacrificar tiempo libre en planillas ni obsesionarse con cada peso. | Esta fase (propuesta de marca) |

**Regla de marca:** toda comunicación pública (landing, README, campañas, mensajes masivos) se escribe desde el escalón *Identification*, usando los inferiores como prueba.

---

## 5. Onlyness Statement

> **Luka es el único asistente de finanzas personales que combina la inmediatez de una conversación cotidiana con el rigor del control financiero automático, para personas que buscan claridad sin fricción bancaria.** *(Versión de la hoja de ruta, aprobada 2026-09-23.)*

**Test de las tres preguntas (adaptación del test del «solo»):**
1. *¿Es única la idea?* — Sí en la combinación: canal universal (WhatsApp), entrada en lenguaje natural y rigor contable (persistencia verificable, taxonomía, límites, compensación).
2. *¿Es útil?* — Sí: elimina la barrera de entrada que explica por qué la mayoría abandona el registro financiero.
3. *¿Es repetible por la competencia?* — La función es copiable; el activo defendible es la **voz** y la **confianza operativa** (nunca confirmar algo que no se persistió; nunca exponer una capacidad sin backend real).

---

## 6. Coherencia de carácter (pacto de integridad)

Neumeier: «si una marca parece un pato pero nada como un perro, la gente desconfiará». Luka se vende como *simple y directo*; por lo tanto queda **prohibido** en la experiencia de producto:

| Promesa pública | Anti-patrón prohibido | Estado verificado |
|---|---|---|
| «Solo escribí como hablás» | Formularios con fecha, categoría y hora obligatorias | El registro es un mensaje; la fecha y categoría se resuelven por defecto (`core_prompt.md:15-23`) |
| «Sin fricción» | Menús obligatorios o frases reservadas | «No se obliga al usuario a terminar un menú» (`docs/conversation-flows.md:210`) |
| «Confianza» | Confirmar un registro que no ocurrió | «NUNCA confirmes que un movimiento... fue registrado... la confirmación solo la realiza el backend» (`prompts/core_prompt.md:5`) |
| «Claro y humano» | Lenguaje técnico bancario en el chat | Glosario humanizado + reglas de voz (ver `02-identidad-verbal.md`) |
| «Tus datos, tuyos» | Exponer teléfonos/PII o acceso directo a la base | `docs/architecture.md:112-122`; `docs/features.md:228-235` |

Cualquier equipo que rompa este pacto está incumpliendo la marca, no solo el diseño.

---

## 7. Principios innegociables de negocio

Derivados de decisiones ya tomadas y con evidencia en el producto:

1. **Verdad operativa.** Ninguna confirmación se emite antes de persistir. El LLM clasifica; el backend confirma (`core_prompt.md:5`; `dispatcher.py:137`).
2. **No exponer capacidades sin backend real.** «En un producto financiero, exponer una capacidad sin backend real es peor que no exponerla — rompe confianza y es cara de recuperar» (`luka-backlog-arquitectura-interaccion.md:42`).
3. **El error nunca se convierte en éxito.** Ante fallos, Luka pide reformular o avisa; no simula (`docs/conversation-flows.md:9-24`).
4. **Exactitud antes que calidez.** La calidez conversacional no reemplaza la precisión: «Priorizar antes de invertir en calidez conversacional — es un hueco de exactitud, no de tono» (backlog:54).
5. **Fricción cero de entrada.** El único requisito de uso es WhatsApp (`README.md:28-30`).
6. **Prudencia financiera.** Sin asesoramiento de inversión, sin tasas actuales inventadas, sin promesas de resultados (`core_prompt.md:29-30`; `docs/financial-glossary.md:15-18`).
7. **El usuario decide.** Toda acción destructiva o irreversible requiere confirmación o cancelación explícita («Listo, no hice ningún cambio», `dispatcher.py:3630`).

---

## 8. Público, héroe y tribu

- **Héroe (StoryBrand).** Persona que busca estabilidad, tranquilidad y progreso económico; ya usa WhatsApp a diario; abandonó (o nunca empezó) el registro financiero.
- **Insight de segmento.** No es un problema de herramientas: es un problema de hábito y de fricción. «No necesitás disciplina de contabilidad» (`README.md:30`).
- **Anti-público (explícito).** Inversores especulativos, usuarios que buscan asesoramiento de trading, contadores que buscan software profesional.
- **Tribu (nivel reflexivo).** Pertenece quien celebra su **claridad e intencionalidad** financiera, no quien presume tacañería (ver `05-gobernanza-manual-vivo.md` §1).

---

## 9. Diferenciación (zag) y estado del producto

| Alternativa | Lo que hace bien | Donde Luka hace *zag* |
|---|---|---|
| Apps de finanzas (Monefy, Fintonic, etc.) | Potentes, con categorías y reportes | Luka no exige app nueva: vive en WhatsApp; entrada por lenguaje natural |
| Planillas (Excel/Sheets) | Flexibles, gratis | Cero setup, cero fórmulas, cero curva |
| Bancos / homebanking | Datos reales de cuenta | Luka es neutral y multi-fuente; el usuario reporta, Luka ordena; sin burocracia bancaria |
| Otros bots financieros | Comandos rígidos | Lenguaje natural con memoria, multiop, referencias («ese», «el último») |

**Cobertura real hoy vs. promesa** (Jira, 2026-09-23):

| Release | Alcance | Estado |
|---|---|---|
| 1–3 | Registro por texto, categorías, recordatorios (fijos, proactivos, inteligentes), límites y compensación, dashboard web, consultas, gráficos, onboarding + vinculación segura, educación financiera, flujos administrables, memoria conversacional, anulación de movimientos | **Finalizado** |
| 4 | Multidivisa y patrimonio real, recomendaciones de inversión (HU-EDU-02) | Abierto |
| 5 | Metas compartidas, racha, resumen semanal, notificaciones grupales | Abierto |
| 6 | Notas de voz (HU-REG-02), OCR de tickets (HU-REG-03), facturas digitales (HU-REG-04) | Abierto |
| 7 | Gamificación (evolución, desafíos de ahorro) | Abierto |

**Regla de comunicación:** features de releases 4–7 **no se comunican como disponibles**. En canales de producto pueden mostrarse como «Próximamente», nunca como capacidades activas (principio 2).

---

## 10. Decisiones de esta fase

| # | Decisión | Estado |
|---|---|---|
| D1.1 | Propósito oficial aprobado | ✅ Aprobado 2026-09-23 |
| D1.2 | Onlyness Statement — versión de la hoja de ruta aprobada como texto de referencia | ✅ Aprobado 2026-09-23 |
| D1.3 | Pacto de integridad y 7 principios innegociables vinculantes | ✅ Aprobado 2026-09-23 |
| D1.4 | Releases 4–7 no se comunican como disponibles; «Próximamente» solo en producto | ✅ Aprobado 2026-09-23 |

---

## 11. Fuentes

- `luka/README.md`, `luka/AGENTS.md`, `luka/prompt.md`, `luka/prompts/core_prompt.md`, `luka/prompts/financial_glossary.v1.json`
- `luka/docs/features.md`, `luka/docs/conversation-flows.md`, `luka/docs/architecture.md`, `luka/docs/financial-glossary.md`
- `luka/luka-backlog-arquitectura-interaccion.md` (documento local, no versionado)
- `luka-llm-research/FALENCIAS.md`
- Jira STK (proyecto Luka, `philippem.atlassian.net`), consulta 2026-09-23
- Neumeier, M. *The Brand Gap*.
