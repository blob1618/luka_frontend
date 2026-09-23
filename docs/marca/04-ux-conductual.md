# 04 · Diseño Conductual y de Interacción (Nivel Conductual de Norman)

> **Entregable de Fase 4.** El nivel conductual mide rendimiento, usabilidad y efectividad: ¿Luka hace lo que promete sin frustrar? Aquí se normaliza la experiencia operativa: brechas, valores predeterminados, errores, fricción y feedback.
> Fuentes: `luka/docs/features.md`, `luka/docs/conversation-flows.md`, `luka/docs/movement-charts.md`, `luka/app/services/*`, `luka-llm-research/FALENCIAS.md`, `luka_frontend/app/**`.
> Marco: Norman, *The Design of Everyday Things* (gulfs, signifiers, diseño para el error); MECLABS (fricción cognitiva).

---

## 1. Principios conductuales de Luka

1. **Un mensaje basta.** Toda acción frecuente se completa en lenguaje natural; los comandos (`/link`, `/movimientos`, `/egresos`) son atajos, no requisitos.
2. **Nunca hacer sentir tonto al usuario.** La ambigüedad se repregunta con opciones; el error del sistema no se muestra como error del usuario.
3. **El sistema decide lo obvio, el usuario decide lo importante.** Fecha, categoría y moneda se infieren; montos, límites y eliminaciones los confirma el usuario.
4. **La incertidumbre se declara.** Si el sistema no está seguro, pregunta o dice que no sabe; no inventa (regla ya vigente, `core_prompt.md:30`).
5. **Toda operación tiene salida.** Cancelar siempre está a un mensaje; nada queda «a medias» sin estado visible.

---

## 2. Brecha de ejecución (Gulf of Execution)

*Distancia entre lo que el usuario quiere y los pasos que la herramienta exige.*

| Quiero… | Hoy hago… | Fricción | Estado |
|---|---|---|---|
| Registrar un gasto | Un mensaje: «Gasté 4500 en nafta» | 1 paso, 0 formularios | ✅ Implementado (`core_prompt.md:79`) |
| Registrar varios | Un mensaje compuesto | 1 paso | ✅ Multiop (`core_prompt.md:23,89-91`) |
| Corregir el último | «Cambiá el monto del último» | 1 paso + confirmación | ✅ Referencias («ese», «el último») |
| Anular | «Anulá el super» / «los últimos dos» | 1 paso | ✅ Multi-anulación |
| Consultar | «¿Cuánto gasté este mes?» / `/movimientos` | 1 paso | ✅ |
| Poner un límite | «Límite de 50000 en comida» | 1–2 pasos (falta mes/año si no lo dice) | ✅ |
| Recordar un pago | «Recordame pagar el wifi el 5» | 1–2 pasos | ✅ |
| Ver el dashboard | `/link` → enlace mágico → Google | 3 pasos web | ✅ (mínimos, de seguridad) |
| Registrar por voz | — | — | 🗓 Release 6 (STK-36 / TE-MEDIA STK-219) |
| Registrar un ticket por foto | — | — | 🗓 Release 6 (STK-37) |

**Signifiers de capacidad:** comandos visibles y descubribles sin documentación.
- `/link` — dashboard (`core_prompt.md:45`)
- `/movimientos`, `/egresos` — consultas (`docs/features.md:119-131`)
- «mis recordatorios», «mis límites» — listados en lenguaje natural
- El propio error orienta: «Podés escribir algo como: 'Gasté 5000 en supermercado'.» (`dispatcher.py:208-212`)

**Regla:** si una capacidad nueva no se puede ejecutar en ≤ 2 mensajes, se rediseña; si no se puede descubrir, no existe.

---

## 3. Brecha de evaluación (Gulf of Evaluation)

*Distancia entre el resultado y su comprensión.*

| Necesidad | Respuesta del sistema | Estado |
|---|---|---|
| «¿Entendió bien?» | Confirmación explícita con tipo, descripción, monto y moneda | ✅ (`dispatcher.py:137`) |
| «¿Está procesando?» | Reacción ⏳ en el mensaje + indicador «escribiendo…» + tarea en background | ✅ (STK-180/231) |
| «¿Salió bien o mal?» | Reacción ✅/❌ al cerrar el proceso | 🗓 STK-222 (abierto) |
| «¿Cómo viene el mes?» | Balance con gastado/límite/restante/% y gráficos PNG | ✅ |
| «¿Por qué el número cambió?» | Recálculo tras editar/anular + propuesta de compensación explicada («no se modifica ningún movimiento») | ✅ |
| «¿Dónde está mi plata?» | Dashboard con KPIs, cartera, flujo y últimas transacciones | ⚠️ Patrimonio real multinivel pendiente (release 4) |

**Reglas de evaluación:**
1. Toda operación escribe **estado + siguiente paso** (nada de «Listo.» seco).
2. Los números siempre van con contexto: monto + moneda + período.
3. Lo que el sistema no puede verificar, lo declara («No puedo confirmar valores o tasas actuales…», `financial_education.py:130-131`).

---

## 4. Smart defaults

| Contexto | Default | Regla de override |
|---|---|---|
| Fecha del movimiento | Hoy (`FECHA ACTUAL` inyectada; relativos resueltos) | El usuario puede decir «ayer», «el martes», o corregir `fecha` |
| Tipo | Inferido del verbo (gasté → egreso; cobré → ingreso) | Si es ambiguo, Luka pregunta (`core_prompt.md:14,19-21`) |
| Moneda | ARS | «en dólares» / USD explícito |
| Categoría | Sinónimo más cercano de la taxonomía; si no hay, pide confirmar o deja sin categoría | El usuario corrige; «Cambiar categoría» es botón de primera clase |
| Mes del límite | Mes actual si no lo dice | «para diciembre» |
| Referencias | Último movimiento / últimos N | Desambiguación explícita («Tengo varios límites de X. ¿A cuál te referís?») |
| Consultas de gráfico | Barras, última consulta conservada como contexto | Opciones numeradas sin gastar LLM (`docs/movement-charts.md:43-46`) |

**Principio:** el default nunca debe sorprender. Si el default podría ser el equivocado (ej., categoría dudosa), se **confirma en vez de asumir** (patrón ya implementado, `dispatcher.py:179-183`).

---

## 5. Prevención y gestión de errores

### 5.1 Diseño para el error (Norman)

El error humano en finanzas da pánico; el sistema lo amortigua.

| Escenario | Comportamiento correcto | Implementación |
|---|---|---|
| Mensaje ambiguo («Anotame 5000») | Repreguntar en lenguaje natural, sin error técnico | Regla binaria + aclaración (`core_prompt.md:19-22`) |
| Multiop incompleto | Reportar qué sí y qué no: «Registré 2 de 3… ¿los reenviás?» | `dispatcher.py:254-257` |
| Movimiento duplicado | No duplicar y decirlo | `dispatcher.py:194` |
| Corrección sobre dato cambiado | Explicar y pedir reconsultar («cambió desde que lo mostramos») | `dispatcher.py:423-431` |
| Compensación con saldos cambiados | Invalidar propuesta y pedir recálculo | `dispatcher.py:1366-1371` |
| Botón/opción vencida | «Esa opción ya no está disponible. Escribime qué querés hacer.» | `dispatcher.py:3666` |
| LLM caído | Pedir reformular (nunca crash silencioso) | `llm.py:177-186,407-413` |
| Redis caído | **No confirmar éxito**; respuesta segura del dispatcher | `docs/conversation-flows.md:193-218,286-313` |

### 5.2 Acciones críticas: confirmación, deshacer y congelamiento

Reglas para acciones irreversibles o sensibles:

| Acción | Patrón exigido | Estado |
|---|---|---|
| Aplicar compensación de presupuesto | Propuesta explícita con montos + vencimiento 30 min + «confirmar compensación» / «no por ahora» | ✅ (`dispatcher.py:1324-1343`) |
| Eliminar movimientos | Confirmación del lote/objeto exacto antes de borrar | ✅ |
| Eliminar límite / recordatorio / categoría | Confirmación + «Listo, no hice ningún cambio» al cancelar | ✅ (`dispatcher.py:2690-2745,3624-3630`) |
| Borrar historial / resetear presupuestos / exportar datos sensibles | **Buffer de deshacer**: «Gasto eliminado. Tocá aquí para deshacer» | 🗓 Propuesta (no existe undo temporal; hoy hay confirmación) |
| Reset de contexto («olvidá lo anterior») | Confirmación fija del backend | ✅ (`dispatcher.py:886`) |

**Reglas transversales:**
1. Ninguna confirmación sin persistencia real (`core_prompt.md:5`).
2. Ningún fallo se convierte en éxito (`docs/conversation-flows.md:9-24`).
3. Toda cancelación es limpia: estado + «no hice ningún cambio».
4. Las acciones destructivas no se ofrecen como opción por defecto (nunca un botón «Eliminar todo» al lado de «Guardar»).

---

## 6. Modelo de fricción (MECLABS)

La fricción ocurre en la mente del usuario: cada decisión, cada campo y cada espera suman. Adaptación operativa de la fórmula `C = 4m + 3v + 2(i − f) − 2a`: motivación y valor pesan más que incentivos, y cada punto de fricción resta. *(D4.1, aprobado 2026-09-23: guía de diseño, no bloqueante.)*

**Presupuesto de decisiones por flujo:**

| Flujo | Decisiones permitidas | Decisiones reales hoy |
|---|---|---|
| Registrar movimiento | ≤ 1 (¿confirmar categoría dudosa?) | 0–1 |
| Crear límite | ≤ 2 (categoría, monto; mes por default) | 0–2 |
| Crear recordatorio | ≤ 2 (concepto, día) | 0–2 |
| Onboarding web | ≤ 2 (aceptar términos, elegir cuenta Google) | 2 (+ 2 clics de navegación) |
| Consulta/gráfico | ≤ 1 (filtro que pida el usuario) | 0–1 |
| Eliminar/cancelar | 1 (confirmar) + salida siempre disponible | 1–2 |

**Reglas MECLABS para Luka:**
- Si un flujo pide un dato que puede inferirse, **se infiere**; si el dato es riesgoso de inferir, se confirma con un toque (botones), no escribiendo.
- Toda espera > 2 s necesita señal visible (⏳/typing).
- Toda pantalla/flujo nuevo **debería** auditarse con esta tabla antes de publicar (`05-gobernanza-manual-vivo.md` §2); es guía, no gate.
- Medición recomendada: latencia P50/P95 y tasa de éxito por flujo (STK-221, abierto).

---

## 7. Feedback en tiempo real

| Momento | Señal | Especificación |
|---|---|---|
| Mensaje recibido | Reacción ⏳ | Inmediata, no bloqueante (STK-180) |
| Procesando | Indicador «escribiendo…» de WhatsApp | Mientras corre el pipeline (STK-231) |
| Éxito | Reacción ✅ (STK-222) + mensaje de confirmación con datos | Al persistir |
| Error | Reacción ❌ + mensaje de salida (¿reintentar? ¿reformular?) | Nunca solo ❌ |
| Sin respuesta inmediata posible | El backend responde igual: pedir reformular o avisar demora | `llm.py:407-413` |
| Gráfico | PNG asíncrono; si falla, avisar y ofrecer reintento | `whatsapp.py:612-613` |

**Objetivo de latencia percibida:** primera señal ≤ 1 s; respuesta completa P50 < 3 s (medir con STK-221/225; techo aceptable P95 < 8 s con mensaje de espera).

---

## 8. Checklist anti-falencias (evidencia empírica → regla de diseño)

Falencias A1–A10 detectadas en el experimento con LLMs (`luka-llm-research/FALENCIAS.md`). Estado actual y regla permanente:

| # | Falencia original | Estado hoy | Regla permanente |
|---|---|---|---|
| A1 | Contrato de un solo movimiento | ✅ Resuelto (`movements[]`, `core_prompt.md:23,89-91`) | Todo mensaje con N operaciones se registra completo o se reporta parcial |
| A2 | Crash ante array JSON del LLM | ✅ Guard + retry (`llm_contract.py:34-45`) | La salida del LLM jamás llega cruda a persistencia |
| A3 | Sin fecha ni relativos | ✅ Campo `fecha` + `FECHA ACTUAL` (`core_prompt.md:17`) | Ninguna fecha se asume si el usuario dijo otra |
| A4 | Sin taxonomía cerrada | ✅ Taxonomía canónica + sinónimos + siembra (9 categorías) | El usuario siempre puede corregir la categoría en un toque |
| A5 | Pérdida silenciosa de un movimiento | ✅ Multiop reporta registrados vs total | Nunca pérdida silenciosa de datos financieros |
| A6 | Campo `expense` redundante | ⚠️ Parcial (redundancia convive en prompts legacy) | Un dato, un solo campo semántico |
| A7 | Sin retry/fallback | ✅ Retry 1 + fallback con mensaje; 🗓 fallback multi-proveedor (STK-216) | El LLM no es punto único de falla |
| A8 | Instrucciones ambiguas | ✅ Regla binaria con ejemplos contrastados | Toda regla del prompt tiene ejemplo positivo y negativo |
| A9 | Sin ejemplos multiop/coloquial | ✅ Multiop; ⚠️ coloquial («lucas», «palo») sigue siendo riesgo residual | Todo patrón de habla frecuente tiene few-shot |
| A10 | `reply_text` sin validar contra registro | ⚠️ Parcial (confirmación generada en backend) | El texto nunca contradice el estado persistido |

**Uso del checklist (D4.4, aprobado 2026-09-23):** recomendado — toda feature conversacional nueva **debería** auditarse contra A1–A10 en la revisión de publicación; no bloquea por sí mismo.

---

## 9. Decisiones de esta fase

| # | Decisión | Estado |
|---|---|---|
| D4.1 | Presupuesto de decisiones por flujo (§6) como guía de diseño no bloqueante | ✅ Aprobado 2026-09-23 |
| D4.2 | Patrón undo/deshacer para acciones destructivas futuras (roadmap) | ✅ Aprobado 2026-09-23 |
| D4.3 | Contrato de feedback ⏳/✅/❌ + mensaje acompañante | ✅ Aprobado 2026-09-23 (STK-222 pendiente de implementar) |
| D4.4 | Checklist A1–A10 como recomendado, no bloqueante | ✅ Aprobado 2026-09-23 |
| D4.5 | Objetivos de latencia: primera señal ≤ 1 s, P50 < 3 s, P95 < 8 s | ✅ Aprobado 2026-09-23 |

---

## 10. Fuentes

- `luka/docs/features.md`, `conversation-flows.md`, `movement-charts.md`, `architecture.md`, `recurring-expenses-runbook.md`
- `luka/app/services/dispatcher.py`, `llm.py`, `llm_contract.py`, `scheduler.py`, `financial_education.py`, `app/api/whatsapp.py`
- `luka-llm-research/FALENCIAS.md`
- `luka_frontend/app/main.py`, `app/templates/**`
- Jira STK-180, STK-221, STK-222, STK-225, STK-231, STK-216, STK-219
- Norman, D. *The Design of Everyday Things*; MECLABS Institute, *Usability Reduces Friction*.
