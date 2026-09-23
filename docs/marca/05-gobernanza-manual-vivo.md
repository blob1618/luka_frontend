# 05 · Nivel Reflexivo, Gobernanza y Manual Vivo

> **Entregable de Fase 5.** El nivel reflexivo (Norman) es el más alto: autoimagen, orgullo, pertenencia y recuerdo duradero. Aquí se define cómo la marca se cultiva y cómo este manual se mantiene vivo.
> Marco: Neumeier, *The Brand Gap* — «pass out the compasses»: un PDF estático se archiva y se olvida; una marca se cultiva con herramientas vivas.

---

## 1. Impacto reflexivo: quién se vuelve el usuario con Luka

### 1.1 La identidad que Luka refuerza

El usuario de Luka no se vuelve contador ni tacaño: se vuelve una **persona financiera consciente** — alguien que sabe qué pasa con su dinero y decide con intención, sin perder tiempo libre.

**Reglas de comunicación reflexiva:**
1. **Luka no premia la tacañería; celebra la claridad y la intencionalidad.** Gastar en lo que importa es una decisión válida; lo que se celebra es saberlo.
2. **Los resúmenes son victorias del héroe**, no reportes de auditoría. El sujeto es el usuario, no el sistema.
3. **Nunca vergüenza.** Sin frases que impliquen culpa («otra vez te pasaste»); se informa y se ofrece una acción.
4. **Competencia, no competencia tóxica.** Gamificación (release 7) celebra constancia y decisiones, no compara usuarios entre sí.

### 1.2 Fórmulas de redacción aprobadas

| Contexto | En lugar de… | Decir… |
|---|---|---|
| Resumen mensual | «Gastaste $450.000. Categoría top: Comida.» | «Este mes lograste mantener tu balance bajo control en un 92 %. Tu categoría principal fue Comida.» |
| Ahorro | «No gastaste nada en ocio.» | «Reservaste $35.000 para tus metas. Ese es tu ahorro del mes.» |
| Desvío | «Excediste Comida en $10.000.» | «Comida se pasó $10.000 del límite. ¿Querés ajustar el límite o compensarlo con otra categoría?» |
| Racha (roadmap) | «Perdiste tu racha.» | «Registraste 21 días seguidos. Hoy es un buen día para seguir.» |

*(Los tres primeros son plantillas de copy a validar; el producto hoy entrega datos, no resúmenes redactados — ver `02-identidad-verbal.md` §8.)*

### 1.3 La tribu

Pertenencia = «yo soy de los que tienen sus números claros». Los canales de marca (comunidad, campañas, landing) hablan a esa identidad: pragmática, argentina, sin jerga financiera, sin culpa.

---

## 2. Brújulas: checklist de publicación

Antes de publicar **una función, un mensaje masivo o una pantalla**, el responsable repasa esta lista. **Es una guía recomendada, no un gate bloqueante (D5.1, aprobado 2026-09-23):** si algo falla, se corrige o se documenta el desvío en el changelog; la decisión de publicar es del equipo.

### 2.1 Filtro narrativo (StoryBrand SB7)

- [ ] El **usuario es el héroe** del texto; Luka es el guía (nunca «nosotros» como protagonista de la historia).
- [ ] El **problema** está enunciado en su capa correcta (externo/interno/filosófico) y sin dramatizar.
- [ ] Queda claro el **siguiente paso** (CTA directo o transicional).
- [ ] El beneficio se expresa como **resultado del usuario**, no como lista de features.

### 2.2 Test Neumeier

- [ ] ¿Esto **suena a Luka** o a un banco genérico? (prueba: léelo en voz alta con `02-identidad-verbal.md` §1 al lado)
- [ ] ¿Es **diferente** a lo que dice la competencia (o es el mismo «zag» de siempre)?
- [ ] ¿Parece pato y nada como pato? (coherencia promesa ↔ experiencia)

### 2.3 Filtro de voz y tono

- [ ] Voseo, frases cortas, sin jerga, sin culpa (`02-identidad-verbal.md` §4).
- [ ] Emojis del set aprobado, con función de señalética.
- [ ] Nombres: `LUKA` solo en marca gráfica; `Luka` en prosa.
- [ ] Ortografía y tildes correctas (revisión obligatoria).
- [ ] Los términos financieros están en el glosario humanizado o se explican en el momento.

### 2.4 Filtro conductual (Norman + MECLABS)

- [ ] El flujo respeta el **presupuesto de decisiones** (`04-ux-conductual.md` §6).
- [ ] Hay **feedback en tiempo real** para toda espera > 2 s.
- [ ] Ninguna confirmación se emite sin persistencia real (verdad operativa).
- [ ] El error está diseñado: ambigüedad → repregunta; fallo → salida clara; nada se convierte en éxito falso.
- [ ] El checklist **A1–A10** (`04-ux-conductual.md` §8) está pasado para features conversacionales.

### 2.5 Filtro visual y accesibilidad

- [ ] Todo color sale de tokens (`03-identidad-visual.md` §8); nada hardcodeado.
- [ ] Contraste texto ≥ 4.5:1 y no-texto ≥ 3:1 en el tema correspondiente.
- [ ] Estado nunca comunicado solo por color.
- [ ] Números con cifras tabulares y formato es-AR.
- [ ] Foco visible, navegación por teclado y `alt`/`aria-label` en el componente nuevo (web).
- [ ] Se usó la variante correcta del isotipo y su zona de resguardo.

---

## 3. Proceso de cambio del manual

| Aspecto | Regla |
|---|---|
| **Ubicación** | `luka_frontend/docs/marca/` (este repositorio). Fuente de verdad única; los tokens viven en `tokens/`. |
| **Versionado** | Semver del manual en este encabezado: `v1.0.0`. Cambios de fondo (propósito, tono, paleta) → major; secciones nuevas → minor; correcciones → patch. |
| **Registro** | Toda modificación actualiza el changelog del `00-luka-brand-compass.md` (sección §7) con fecha, autor y motivo. |
| **Aprobación** | En equipo (D5.2): los cambios se proponen por PR y requieren al menos una revisión de otra persona del equipo. Sin owner único. |
| **Ritmo** | Revisión completa **mensual** (D5.4); revisión extraordinaria tras cualquier release de producto o incidente de marca. |
| **Definition of Done de marca** | Una feature no se considera terminada si: su copy no pasó el §2, sus colores no salen de tokens, o su flujo excede el presupuesto de decisiones sin excepción documentada. |
| **Excepciones** | Toda excepción se documenta en el changelog con fecha de revisión; las excepciones vencen a los 90 días. |

---

## 4. Repositorio de tokens compartido

**Fuente de verdad:** `docs/marca/tokens/design-tokens.json` → **implementación:** `docs/marca/tokens/tokens.css` → **código:** `static/css/*.css` (adopción pendiente, `03-identidad-visual.md` §9).

### 4.1 Proceso de cambio de un token

1. **Propuesta** (issue) con motivo, uso previsto y valor propuesto.
2. **Verificación de contraste** (script WCAG) para todo valor de color; el resultado se anota en la propuesta.
3. **Actualización** de `design-tokens.json` y `tokens.css` en el mismo cambio (nunca desincronizados).
4. **Nota de migración** en `03-identidad-visual.md` §9 si reemplaza un valor en uso.
5. **Changelog** en `00-luka-brand-compass.md` §7.

### 4.2 Sincronización diseño ↔ código

| Herramienta | Regla |
|---|---|
| Figma | Las variables de Figma se nombran igual que los tokens (`color/semantic/dark/bg-surface`); el JSON es la referencia, Figma es consumidor |
| Código | Prohibido hardcodear hex/tamaños: todo componente referencia variables CSS o tokens |
| Chat (PNG) | La paleta de gráficos se importa del mismo archivo de tokens; nada de paletas ad-hoc (`movement_chart.py`) |
| Sitios de terceros (Meta, badges, etc.) | Solo se usan las variantes de isotipo aprobadas |

---

## 5. Métricas de marca (brújula cuantitativa)

| Dimensión | Métrica | Fuente | Objetivo inicial |
|---|---|---|---|
| Claridad | Tasa de reformulación de mensajes por el usuario (el bot no entendió) | logs del dispatcher | ↓ mes a mes |
| Confianza | Persistencias incorrectas toleradas = **0** | auditoría | invariante |
| Fluidez | Latencia percibida P50/P95 | STK-221 (observabilidad) | P50 < 3 s · P95 < 8 s |
| Retención | Días activos por usuario por mes (registro o consulta) | eventos | ↑ mes a mes |
| Hábito | Racha de días con registro; recordatorios proactivos respondidos | release 5 (HU-GAM-02) | ↑ |
| Reflexivo | Preguntas respondidas «¿cómo vengo?» sin pedir ayuda | encuestas/entrevistas | cualitativo |
| Costo | Costo LLM + mensajería por usuario activo | STK-140/141 | controlado (ver SPIKE-01) |
| Voz | Rechazos de copy en revisión de publicación | este proceso | ≤ 1 ciclo de corrección por pieza |

**Regla:** las métricas no se convierten en metas de vanidad; cada una debe poder accionar una decisión de producto o marca.

---

## 6. Qué hacer cuando algo de este manual no aplica

1. ¿Es una excepción de negocio? → documentar en changelog con fecha de revisión.
2. ¿El manual está desactualizado respecto del producto? → abrir issue de gobernanza; el producto manda (si Luka cambió su comportamiento, la marca se actualiza, no al revés).
3. ¿Hay conflicto voz vs negocio? → gana la verdad operativa y la confianza del usuario (`01-plataforma-estrategica.md` §7); nunca un copy que prometa lo que el sistema no hace.

---

## 7. Decisiones de esta fase

| # | Decisión | Estado |
|---|---|---|
| D5.1 | Checklists de publicación como guía recomendada (no bloqueante) | ✅ Aprobado 2026-09-23 |
| D5.2 | Versionado semver + changelog + aprobación en equipo (PR con revisión) | ✅ Aprobado 2026-09-23 |
| D5.3 | `design-tokens.json` como fuente de verdad; Figma y código consumidores | ✅ Aprobado 2026-09-23 |
| D5.4 | Revisión **mensual** del manual + Definition of Done de marca | ✅ Aprobado 2026-09-23 |
| D5.5 | Tablero de métricas de marca completo (§5) | ✅ Aprobado 2026-09-23 |

---

## 8. Fuentes

- Todas las fases de este manual (`00`–`04`)
- `luka/docs/architecture.md` (observabilidad, latencia), `docs/features.md`
- Jira STK-140, STK-141, STK-221, STK-225 y releases 1–7
- Norman, D. *Emotional Design* (nivel reflexivo); Neumeier, M. *The Brand Gap* (brújulas, cultivo de marca).
