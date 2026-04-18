# Brief: Expediente Abierto

> **Tipo de documento:** brief genérico para LLM agéntico.
> **Etapa del proyecto:** concepto (pre-build).
> **Autor del brief:** el propietario del producto, con asistencia de un modelo lingüístico.
> **Idioma operativo:** español (pero el agente puede trabajar en cualquier idioma si resulta más efectivo).

---

## 0. Cómo usar este documento

Este brief describe una idea de producto **en fase de concepto**. Fue escrito para poder ser usado por un LLM agéntico avanzado en **al menos tres modos distintos**:

1. **Modo construcción.** Tomar el brief como especificación y comenzar a prototipar el producto: arquitectura, stack, código, contenido.
2. **Modo refinamiento.** Leer el brief críticamente, detectar contradicciones, vacíos, riesgos no mencionados, y devolver preguntas afiladas o propuestas alternativas.
3. **Modo investigación.** Usar el brief como punto de partida para investigar viabilidad técnica, costos operativos, landscape competitivo, regulación aplicable, o cualquier otra dimensión que el proyecto requiera.

El agente debe **elegir explícitamente un modo** (o combinarlos) antes de producir salida, y reportar qué modo tomó y por qué.

Al final del documento hay **prompts sugeridos** para cada modo. No son obligatorios: el agente puede proponer un abordaje mejor si lo considera.

---

## 1. TL;DR

Juego de detectives por suscripción, entregado enteramente por email. El usuario recibe un caso ficticio y debe resolverlo conversando por mail con testigos, sospechosos e informantes. Todos esos personajes son **agentes de IA autónomos** con personalidad, memoria y secretos. La ficción está declarada (no se engaña al usuario). Hay un catálogo de casos, duración configurable (desde una noche hasta semanas), y modos individual + tres modos multijugador.

---

## 2. Contexto y motivación

### 2.1 Problema / oportunidad percibida

- Existe un mercado probado para juegos de detectives por correo (Hunt A Killer, The Mysterious Package Co.), pero son **100% guionados**: no reaccionan al jugador.
- Existen ARGs (Alternate Reality Games) que logran inmersión altísima, pero son **masivos, sincronizados y caros de operar**.
- Existen chatbots narrativos con IA (Character.AI, AI Dungeon) que prueban apetito por ficción con IA, pero **carecen de arco narrativo cerrado** y de estructura.
- La oportunidad es combinar las tres categorías: estructura narrativa tipo Hunt A Killer + inmersión tipo ARG + flexibilidad de la IA generativa, en el canal más íntimo y universal que existe: el email.

### 2.2 Premisa de producto

> El próximo caso no está en una app. Está en tu bandeja de entrada.

El email no es un medio obsoleto para este producto: es el medio **ideal**. Es asincrónico (respeta el ritmo del jugador), es privado, tiene latencia natural (un forense tarda más que un amigo) y está profundamente integrado en la vida del usuario.

---

## 3. Concepto central

El usuario entra a un sitio web, elige un caso de un catálogo, deja su correo y un alias de investigador. A partir de ahí **no vuelve a la plataforma**: toda la experiencia sucede en su inbox.

Recibe un primer mail "oficial" (tipo expediente) con la información inicial del caso, contactos clave, y una primera misión. Puede responder al expediente central o escribir directamente a los personajes del caso, cada uno con su propia dirección de correo. Los personajes responden con memoria, personalidad y agenda propia.

El jugador avanza escribiendo, presionando, deduciendo. Los agentes le pasan pistas, le mienten, le ocultan cosas, lo apuran si se queda callado. Aparecen nuevos personajes y documentos (adjuntos generados: fotos, audios, PDFs, recortes de prensa) a medida que el caso avanza. Cuando cree tener la respuesta, envía una **resolución formal** y recibe un epílogo personalizado que narra las consecuencias de su investigación.

---

## 4. Experiencia del usuario (flujos)

### 4.1 Onboarding

1. Landing page → catálogo de casos con previews (tema, duración estimada, dificultad, cantidad de personajes).
2. Elección de caso → formulario con email, alias, duración deseada (ej: "1 semana intensiva", "un mes relajado"), modo (individual / cooperativo / roles / competitivo).
3. Si es multijugador: generación de código de partida para invitar al resto.
4. Confirmación de pacto de ficción (disclaimer claro: esto es un juego).
5. Primer mail: expediente inicial con hechos, contactos, primera misión.

### 4.2 Loop de juego

- Jugador escribe a un personaje (o al expediente central).
- Guardián de tiempo decide cuánto tarda la respuesta según personaje, situación y configuración de duración.
- Personaje responde coherente con su ficha, su memoria acumulada y la "verdad del caso".
- Si el jugador no escribe en X tiempo: los personajes lo apuran con mensajes proactivos.
- El Director de caso dispara nuevos eventos (nuevo testigo, nuevo documento filtrado) si el jugador se estanca o para avanzar la trama según los hitos de ritmo.
- Se generan adjuntos (fotos, audios, PDFs falsos) cuando la trama lo requiere.

### 4.3 Cierre

- Jugador envía una resolución formal (a quién acusa, con qué pruebas, por qué).
- Sistema evalúa la resolución contra la verdad del caso + las decisiones tomadas en el camino.
- Recibe un epílogo personalizado: qué pasó con cada personaje, cuál fue el impacto de sus decisiones, en qué acertó y en qué no.
- CTA para siguiente caso.

---

## 5. Modos de juego (v1)

| Modo | Descripción |
|---|---|
| **Individual** | Un jugador, un caso, un inbox. Experiencia base. |
| **Cooperativo clásico** | Varios jugadores comparten el mismo detective y el mismo inbox. Se coordinan entre ellos. |
| **Roles especializados** | Cada jugador es un rol distinto (forense, periodista, policía, abogado). Los agentes tratan a cada uno según su rol y le dan info distinta. Los jugadores deben compartir pistas. **Este modo es el más diferencial del producto.** |
| **Competitivo** | Varios jugadores investigan el mismo caso por separado. Gana el que resuelve primero o mejor. |

---

## 6. Arquitectura de agentes de IA

Sistema **multi-agente**. No hay un solo modelo respondiendo a todo.

| Agente | Responsabilidad |
|---|---|
| **Director de caso** | Custodia la verdad del caso. Decide qué se revela y cuándo. Detecta si el jugador se atascó. Dispara hitos de ritmo. |
| **Personajes (NPCs)** | Uno por cada personaje del caso. Ficha con personalidad, voz, coartada, secretos, estado emocional, memoria completa del intercambio con cada jugador. |
| **Guardián de tiempo** | Decide latencia de cada respuesta. Sostiene verosimilitud. Dispara apuros cuando el jugador se va del ritmo configurado. |
| **Generador de pruebas** | Produce adjuntos: fotos, recortes de prensa, audios, PDFs, capturas de chat, documentos escaneados. |
| **Moderador / seguridad** | Evita break-character, prompt injection, spoilers prematuros, contenido inapropiado. |
| **Árbitro de partida** | Solo en modos multijugador. Reparte información según rol, lleva tablero común, decide ganador. |

---

## 7. Diseño de casos

Cada caso = **esqueleto humano + espacio vivo para IA**.

El guionista humano entrega:
- **Biblia del caso:** quién hizo qué, cuándo, por qué. La verdad oculta. Canónica, inmutable durante la partida.
- **Fichas de personaje:** personalidad, voz, qué sabe, qué oculta, bajo qué presión rompe.
- **Pistas obligatorias:** piezas que el jugador debe encontrar para poder cerrar el caso.
- **Hitos de ritmo:** eventos disparables si el jugador se estanca (nuevo testigo, documento filtrado).
- **Finales posibles:** 2 o 3 resoluciones distintas según decisiones del jugador.
- **Configuración de duración:** el mismo caso debe poder jugarse en una noche, un fin de semana o un mes, ajustando tiempos de respuesta y espaciado entre hitos.

**Railroading:** en v1 hay siempre un camino sugerido claro. El jugador puede explorar, pero el Director de caso lo reencauza orgánicamente si se pierde. Mundo abierto queda para v2.

---

## 8. Modelo de negocio

### 8.1 Modelo principal

Suscripción mensual. Planes tentativos:

| Plan | Contenido | Modos | Extras |
|---|---|---|---|
| Aficionado | 1 caso corto / mes | Individual | — |
| Investigador | 1 caso estándar / mes | Individual + cooperativo | Casos temáticos |
| Detective | Ilimitado | Todos los modos | Casos premium, finales alternativos |

### 8.2 Consideraciones críticas de margen

- Cada caso tiene **costo variable de cómputo** (tokens de IA).
- Un jugador "insistente" puede disparar el costo de su caso a niveles que rompan el margen del plan.
- El modelo de precios debe contemplar topes, rate limiting narrativo, o costos escalonados.

### 8.3 Revenue streams adicionales

- Casos premium "de autor" en colaboración con escritores de género.
- Ediciones temáticas por tiempo limitado (true crime, sci-fi, histórico).
- Modo corporativo: casos para team-building, eventos, activaciones de marca.
- Merchandising físico: cajas con objetos reales ligadas a un caso.

---

## 9. Decisiones cerradas (NO cambiar sin revisar)

- **Canal:** email. No app, no web app durante el juego.
- **Ficción declarada.** No se finge que los hechos son reales.
- **Catálogo de casos.** El jugador elige, no se asignan a ciegas.
- **Duración configurable.** Desde una noche hasta semanas, definida por el jugador.
- **Railroading activo** en v1. Siempre hay un siguiente paso sugerido.
- **Los agentes apuran al jugador** si no responde. Ritmo activo, no pasivo.
- **Cuatro modos de juego** en v1: individual, cooperativo clásico, roles especializados, competitivo.

## 10. Decisiones abiertas (bloquean build completo)

- **Nombre definitivo** del producto ("Expediente Abierto" es placeholder).
- **Géneros narrativos** de lanzamiento: ¿true crime, noir, sobrenatural, mezcla?
- **Precios concretos** por plan.
- **Stack técnico:** modelos de IA (proveedor, familia, tamaño), proveedor de email transaccional (SendGrid, Postmark, AWS SES...), hosting, base de datos, almacenamiento de adjuntos.
- **Mercado de lanzamiento:** ¿español primero, inglés primero, bilingüe?
- **Formato del caso piloto:** duración, temática, cantidad de personajes, complejidad.
- **Equipo mínimo** para producir un caso (guionista, diseñador de agentes, QA narrativo, ilustrador de pruebas).
- **Política de contenido sensible:** qué temas están permitidos, qué temas nunca.

---

## 11. Riesgos y desafíos conocidos

### 11.1 Técnicos
- Consistencia de personajes a lo largo de días o semanas (manejo de memoria / contexto largo).
- Control de costos de IA ante jugadores insistentes.
- Deliverability: evitar que los mails caigan en spam, manejar dominios ficticios creíbles sin ser flaggeados.
- Prompt injection: jugadores que intenten quebrar a los agentes.
- Orquestación multi-agente sin perder coherencia global.

### 11.2 Narrativos
- Escribir casos buenos y rejugables es caro. Necesita proceso de producción de contenido, no solo tecnología.
- Mantener tensión dramática cuando el jugador tiene iniciativa total.
- Evitar la sensación de "estoy hablando con un bot" en momentos clave.

### 11.3 Legales y éticos
- Deslinde si un jugador se toma la ficción demasiado en serio.
- No tocar hechos o personas reales sin consentimiento.
- Protección de datos: el jugador comparte su mail y puede compartir info personal en sus respuestas.
- Regulación de IA generativa según jurisdicción (UE AI Act, etc.).

---

## 12. Criterios de éxito

El producto está validado si:
- El jugador promedio **completa al menos un caso** sin abandonar.
- El NPS o equivalente indica que lo recomendaría.
- El **costo de IA por caso completado** cabe cómodamente dentro del margen del plan pagado.
- Al menos el **30% de los jugadores** renueva la suscripción después del primer caso.
- Las partidas multijugador (especialmente roles especializados) tienen tasa de finalización comparable a la individual.

---

## 13. Prompts sugeridos por modo

Estos prompts son guías, no obligaciones. El agente puede mejorarlos o combinarlos.

### 13.1 Modo construcción
> "Usando este brief, diseñá una arquitectura técnica mínima viable para un caso piloto de 3 días con 4 personajes. Incluí: elección de modelos de IA (con justificación), esquema de datos para fichas de personaje y memoria conversacional, flujo de orquestación entre agentes, estimación de costo por caso, y una lista ordenada de los primeros 10 tickets de desarrollo. Marcá explícitamente todo lo que asumiste y todo lo que seguiría bloqueado por las decisiones abiertas de la sección 10."

### 13.2 Modo refinamiento
> "Leé este brief críticamente. Identificá: (1) contradicciones internas, (2) supuestos no explicitados que pueden ser falsos, (3) riesgos no mencionados, (4) decisiones que parecen cerradas pero en realidad dependen de información que no tenemos. Devolveme entre 5 y 10 preguntas afiladas que, si las respondo bien, hacen al brief significativamente más sólido. Para cada pregunta, decime por qué es importante."

### 13.3 Modo investigación
> "Investigá los siguientes frentes y devolvé un reporte con fuentes: (a) estado actual del mercado de juegos por correo y cifras de Hunt A Killer y competidores, (b) costo estimado por caso usando los modelos más adecuados (con cálculo explícito de tokens), (c) proveedores de email transaccional viables con pros/contras para este caso de uso, (d) regulación de IA generativa aplicable en el mercado objetivo, (e) 3 productos emergentes en los últimos 24 meses que compitan o complementen esta propuesta."

---

## 14. Notas finales para el agente

- Si encontrás una contradicción entre este brief y el sentido común, **señalala antes de resolverla**. No la resuelvas silenciosamente.
- Si una decisión abierta bloquea tu trabajo, **no asumas arbitrariamente**: pedí input o marcá claramente el supuesto.
- El producto es **ficción**: cuidá que cualquier output (código, copy, diseño de caso) refleje esa naturaleza lúdica.
- El propietario del proyecto **no es un desarrollador full-time**: priorizá explicaciones claras sobre jerga, y outputs accionables sobre teoría.
- Si vas a proponer alternativas radicales al concepto, **proponelas como alternativa**, no como reemplazo.

---

*Fin del brief.*
