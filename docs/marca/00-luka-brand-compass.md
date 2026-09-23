# 00 · The Luka Brand Compass (Manual Maestro de Marca)

> **Entregable Final.** Documento central: índice, resumen ejecutivo, decisiones de marca y gobernanza.
> **Estado:** `v0.3.0` — **decisiones cerradas** (2026-09-23); pendientes de implementación: migración de categorías, copy de degradación y reacciones ✅/❌.
> **Alcance:** producto Luka (WhatsApp + dashboard web) en sus repos `luka/` y `luka_frontend/`.
> **Cómo funciona este manual:** los documentos de fase contienen el detalle; este archivo es la brújula que los conecta y el registro de decisiones.

---

## 1. Cómo usar este manual

| Si sos… | Empezá por… | Después… |
|---|---|---|
| **Producto / fundador** | `01-plataforma-estrategica.md` | Decisión D1.x, roadmap §9 de ese documento |
| **Copy / contenido / soporte** | `02-identidad-verbal.md` | Glosario humanizado, anexo de microcopy, checklist de publicación (`05` §2) |
| **Diseño / frontend** | `03-identidad-visual.md` + `tokens/` | Checklist visual y de accesibilidad (`05` §2.5) |
| **Desarrollo (bot y web)** | `04-ux-conductual.md` | Checklist A1–A10, presupuesto de decisiones, tokens §8 de `03` |
| **Gobernanza / PM** | `05-gobernanza-manual-vivo.md` | Changelog (§7 de este archivo), métricas de marca |

**Regla base:** cuando este manual y el producto difieran, gana la realidad operativa (lo que el sistema hace de verdad) y el manual se actualiza en el próximo ciclo.

---

## 2. Mapa del manual

```
docs/marca/
├── 00-luka-brand-compass.md        ← este archivo (índice + decisiones + gobernanza)
├── 01-plataforma-estrategica.md    ← Fase 1: propósito, onlyness, principios, público, roadmap
├── 02-identidad-verbal.md          ← Fase 2: SB7, voz/tono, glosario, microcopy real
├── 03-identidad-visual.md          ← Fase 3: logo, paleta, tipografía, iconos, componentes, migración
├── 04-ux-conductual.md             ← Fase 4: brechas, defaults, errores, MECLABS, feedback
├── 05-gobernanza-manual-vivo.md    ← Fase 5: nivel reflexivo, checklists, tokens, métricas
├── tokens/
│   ├── design-tokens.json          ← fuente de verdad de diseño
│   └── tokens.css                  ← implementación (dark + light)
└── assets/
    ├── isotipo-color.svg           ← isotipo definitivo (por defecto)
    ├── isotipo-claro.svg           ← variante para fondos oscuros
    ├── isotipo-oscuro.svg          ← variante para fondos claros
    ├── isotipo-mono.svg            ← monocromo currentColor
    └── favicon.svg                 ← favicon (viewBox recortado)
```

---

## 3. Resumen ejecutivo por fase

### Fase 1 — Núcleo estratégico (`01`)
- **Propósito:** que cualquiera se haga cargo de su dinero sin aprender a ser contador, sin otra app y sin culpa.
- **Onlyness (versión hoja de ruta):** el único asistente que combina la inmediatez de una conversación cotidiana con el rigor del control financiero automático, para personas que buscan claridad sin fricción bancaria.
- **Escalera de valor:** features → benefits → experiencia → **identificación** (persona financiera consciente).
- **7 principios innegociables**, encabezados por la verdad operativa (nunca confirmar sin persistir).
- **Roadmap:** releases 1–3 en producción; 4–7 no se comunican como disponibles.

### Fase 2 — Identidad verbal (`02`)
- **Voz:** cercana, clara, prudente, resolutiva — nunca paternalista, burlona ni técnica.
- **BrandScript SB7** completo: héroe (usuario), villano (fricción + descontrol + culpa), guía (Luka), plan de 3 pasos.
- **Matriz de tono** por contexto con copys reales citados del código; emojis como señalética, set oficial reducido a 5 (✅ 📁 ⚠️ 🎯 🔔), resto deprecado.
- **Claridad sobre ingenio:** tabla decir/evitar y glosario humanizado (9 términos con fuentes BCRA/INDEC).
- **Anexo:** inventario de ~70 mensajes reales — fuente de consistencia para todo copy nuevo.

### Fase 3 — Identidad visual (`03`)
- **Paleta nueva:** navy profundo + azul `#2563EB` (confianza/acción) + esmeralda `#0E9F6E` (logro/ahorro); grafito para gasto; rojo solo para error.
- **Contraste WCAG AA verificado** en todos los pares texto/superficie y botones; categorías ≥ 3:1.
- **Isotipo:** definido — burbuja entrelazada azul→esmeralda; variantes claro/oscuro/mono; favicon; wordmark PNG vigente.
- **Tipografía:** Space Grotesk (display) + Inter con cifras tabulares (UI/datos) + JetBrains Mono.
- **9 categorías + Otros** con color oficial y nombres unificados con tildes en código y datos (migración pendiente).
- **Migración documentada** (indigo actual → paleta nueva) sin tocar código en esta fase.

### Fase 4 — Diseño conductual (`04`)
- **Brechas de Norman** auditadas: registro en 1 mensaje (ejecución) y feedback ⏳/✅/❌ + balances (evaluación).
- **Smart defaults:** fecha, tipo, moneda, categoría, mes — confirmando solo lo riesgoso.
- **Errores:** repregunta en vez de error técnico, cancelación limpia, degradación que nunca miente, undo aprobado para acciones destructivas (roadmap).
- **Fricción MECLABS:** presupuesto de decisiones por flujo (≤ 2) como guía de diseño (no bloqueante).
- **Checklist A1–A10** derivado de evidencia empírica de fallas reales del LLM (recomendado, no bloqueante).

### Fase 5 — Reflexivo y gobernanza (`05`)
- **Identidad reflexiva:** el usuario se vuelve una persona financiera consciente; se celebra claridad, no tacañería.
- **Brújulas:** checklists recomendados (no bloqueantes) de SB7, Neumeier, voz, conducta y accesibilidad.
- **Manual vivo:** semver, changelog, aprobación en equipo (PR con revisión), revisión **mensual**, Definition of Done.
- **Tokens compartidos:** proceso de cambio y sincronización Figma ↔ código.
- **Métricas de marca** con fuente y objetivo.

---

## 4. Decisiones de marca consolidadas

> Todas las decisiones fueron **cerradas el 2026-09-23** en sesión conjunta. «Implementación pendiente» significa que la decisión está tomada y falta ejecutarla en producto.

| ID | Decisión | Fase | Estado |
|---|---|---|---|
| D1.1 | Propósito oficial aprobado | 1 | ✅ Aprobado 2026-09-23 |
| D1.2 | Onlyness Statement (versión hoja de ruta) como texto de referencia | 1 | ✅ Aprobado 2026-09-23 |
| D1.3 | Pacto de integridad + 7 principios innegociables vinculantes | 1 | ✅ Aprobado 2026-09-23 |
| D1.4 | Releases 4–7 no se comunican como disponibles; «Próximamente» solo en producto | 1 | ✅ Aprobado 2026-09-23 |
| D2.1 | Voz permanente: cercana, clara, prudente, resolutiva | 2 | ✅ Aprobado 2026-09-23 |
| D2.2 | BrandScript SB7 oficial | 2 | ✅ Aprobado 2026-09-23 |
| D2.3 | `LUKA` (marca gráfica) vs `Luka` (prosa) | 2 | ✅ Aprobado 2026-09-23 |
| D2.4 | Set de emojis reducido a 5 oficiales; resto deprecado | 2 | ✅ Aprobado 2026-09-23 |
| D2.5 | Prohibiciones de copy como guía de estilo (no bloqueante) | 2 | ✅ Aprobado 2026-09-23 |
| D2.6 | Reemplazo de mensajes «Se perdió el contexto» por voz Luka | 2 | ✅ Copy aprobado — implementación pendiente |
| D3.1 | Paleta navy/azul/esmeralda verificada AA | 3 | ✅ Aprobado 2026-09-23 |
| D3.2 | Rojo prohibido para gasto; grafito para egreso | 3 | ✅ Aprobado 2026-09-23 |
| D3.3 | Símbolo nuevo de isotipo (fluidez/diálogo/balance); K/A deprecados | 3 | ✅ Cumplido 2026-09-23 — isotipo definitivo en `public/` y `docs/marca/assets/` |
| D3.4 | Space Grotesk (display) + Inter (UI/datos) + JetBrains Mono | 3 | ✅ Aprobado 2026-09-23 |
| D3.5 | Tokens versionados como fuente de verdad | 3 | ✅ Aprobado 2026-09-23 |
| D3.6 | Categorías unificadas con tildes + color oficial | 3 | ✅ Aprobado — migración pendiente |
| D4.1 | Presupuesto de decisiones por flujo como guía (no bloqueante) | 4 | ✅ Aprobado 2026-09-23 |
| D4.2 | Patrón undo/deshacer para acciones destructivas (roadmap) | 4 | ✅ Aprobado 2026-09-23 |
| D4.3 | Contrato de feedback ⏳/✅/❌ + mensaje | 4 | ✅ Aprobado 2026-09-23 |
| D4.4 | Checklist A1–A10 recomendado (no bloqueante) | 4 | ✅ Aprobado 2026-09-23 |
| D4.5 | Latencias: primera señal ≤ 1 s, P50 < 3 s, P95 < 8 s | 4 | ✅ Aprobado 2026-09-23 |
| D5.1 | Checklists de publicación como guía (no bloqueante) | 5 | ✅ Aprobado 2026-09-23 |
| D5.2 | Semver + changelog + aprobación en equipo (sin owner único) | 5 | ✅ Aprobado 2026-09-23 |
| D5.3 | `design-tokens.json` fuente de verdad; Figma/código consumidores | 5 | ✅ Aprobado 2026-09-23 |
| D5.4 | Revisión mensual + Definition of Done de marca | 5 | ✅ Aprobado 2026-09-23 |
| D5.5 | Tablero de métricas de marca completo | 5 | ✅ Aprobado 2026-09-23 |

---

## 5. Inventario de assets y tokens

| Activo | Ruta | Uso |
|---|---|---|
| Wordmark LUKA | `luka/public/logo-luka-texto.png` | Marca principal (pendiente versión SVG) |
| Isotipo color (por defecto) | `docs/marca/assets/isotipo-color.svg` · `luka_frontend/public/logo-luka.svg` | Fondos claros y oscuros, espacios de marca |
| Isotipo claro | `docs/marca/assets/isotipo-claro.svg` · `luka_frontend/public/logo-luka-claro.svg` | Fondos oscuros |
| Isotipo oscuro | `docs/marca/assets/isotipo-oscuro.svg` · `luka_frontend/public/logo-luka-oscuro.svg` | Fondos claros (una tinta negra) |
| Isotipo mono | `docs/marca/assets/isotipo-mono.svg` · `luka_frontend/public/logo-luka-mono.svg` | `currentColor`: sellos, marcas de agua, una tinta |
| Favicon | `luka_frontend/public/favicon.svg` + `favicon-32.png` + `favicon-512.png` + `apple-touch-icon.png` | Pestaña/navegador e iOS |
| Design tokens | `docs/marca/tokens/design-tokens.json` | Fuente de verdad |
| CSS de tokens | `docs/marca/tokens/tokens.css` | Implementación dark + light |
| Iconos UI | `luka_frontend/app/templates/components/icons/` | Set lineal vigente |
| Paleta de gráficos | `luka/app/services/movement_chart.py` | **A migrar** a tokens categóricos |

---

## 6. Checklist maestra (resumen operativo)

Guía operativa recomendada (no bloqueante — D5.1). Antes de publicar cualquier pieza o feature:

- [ ] **SB7:** usuario héroe, problema claro, siguiente paso visible.
- [ ] **Neumeier:** suena a Luka, no a banco genérico; promesa ↔ experiencia coherentes.
- [ ] **Voz:** §4 de `02` + glosario + emojis del set + ortografía.
- [ ] **Conducta:** presupuesto de decisiones, feedback de espera, errores diseñados, A1–A10.
- [ ] **Visual:** tokens, contraste AA, estado no solo por color, cifras tabulares, isotipo correcto.
- [ ] **Verdad operativa:** ninguna confirmación sin persistencia; ningún fallo convertido en éxito.
- [ ] **Registro:** decisión o excepción anotada en el changelog (§7).

Detalle completo: `05-gobernanza-manual-vivo.md` §2.

---

## 7. Changelog del manual

| Versión | Fecha | Cambios |
|---|---|---|
| `v0.1.0` | 2026-09-23 | Creación inicial: fases 1–5, tokens v1.0.0, isotipo propuesto, inventario de microcopy, verificación de contraste WCAG. Basado en análisis de `luka/`, `luka_frontend/`, `luka-llm-research/` y backlog Jira STK (179 issues). Estado: borrador para aprobación. |
| `v0.2.0` | 2026-09-23 | Decisiones D1.1–D5.5 cerradas en sesión conjunta: Onlyness (versión hoja de ruta), emojis reducidos a 5, copy de degradación aprobado, símbolo nuevo de isotipo, categorías con tildes, presupuesto MECLABS y checklists como guía no bloqueante, aprobación en equipo, revisión mensual. |
| `v0.3.0` | 2026-09-23 | Isotipo definitivo integrado: SVG color/claro/oscuro/mono + favicon en `public/` y `docs/marca/assets/`; PNG 32/512 y apple-touch; `03` §2 y §10 actualizados; assets K provisionales eliminados. |

---

## 8. Referencias

- **Neumeier, Marty.** *The Brand Gap: How to Bridge the Distance Between Business Strategy and Design* (New Riders / AIGA). Las 5 disciplinas de marca, diferenciación, *zag*, y el concepto de brújula de marca.
- **Norman, Donald A.** *The Design of Everyday Things* (Basic Books / MIT Press). Affordances, signifiers, diseño centrado en el usuario, brechas de ejecución y evaluación.
- **Norman, Donald A.** *Emotional Design: Why We Love (or Hate) Everyday Things* (Basic Books). Niveles visceral, conductual y reflexivo.
- **Miller, Donald.** *Building a StoryBrand: Clarify Your Message So Customers Will Listen* (HarperCollins). BrandScript SB7, cliente como héroe, claridad sobre ingenio.
- **Cervantes, Ramsés Guri.** *De usuario a héroe: Cómo estructurar el storytelling de nuestras landings* (Aerolab). Storytelling aplicado a producto e interfaces fintech.
- **MECLABS Institute / Neo Insight.** *Usability Reduces Friction*. Fricción cognitiva y optimización de decisiones.
- **Saffer, Dan.** *Microinteractions* / UI Interaction Design Guidelines. Smart defaults, prevención de errores críticos, feedback contextual.
- **WCAG 2.2** (W3C). Contraste 1.4.3 / 1.4.11, uso del color 1.4.1.

---

## 9. Cómo contribuir a este manual

1. Abrí un issue con la sección afectada y el motivo.
2. Si toca tokens, seguí el proceso de `05` §4.1 (incluye verificación de contraste).
3. Actualizá el changelog (§7) con versión semver, fecha, autor y motivo.
4. Una decisión nueva entra a la tabla §4 con estado «Propuesto» hasta su aprobación en equipo.
