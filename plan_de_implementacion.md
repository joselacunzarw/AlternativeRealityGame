# Expediente Abierto - Arquitectura y Refinamiento (Modos 1 y 2)

Este documento materializa el análisis crítico del brief ("Modo Refinamiento") y la primera propuesta de arquitectura técnica ("Modo Construcción"). El objetivo es establecer un consenso sólido sobre cómo operará el juego y con qué tecnologías antes de empezar a programar.

## User Review Required

> [!IMPORTANT]
> **Preguntas Críticas (Refinamiento)**
> He analizado a fondo el brief y he detectado algunas áreas que necesitan tu decisión para poder avanzar con la programación. Por favor revisa y contesta los siguientes puntos:

1. **Gestión de Dominios y Remitentes:**
   Para que el jugador envíe correos a personajes (ej. `juez_garcia@...`), no podemos registrar múltiples dominios sueltos sin caer en listas de spam.
   * **Propuesta:** Adquirir un dominio maestro (ej. `@casos.expedienteabierto.com`) y crear alias por personaje (ej. `marcos.garcia@casos...`). ¿Estás de acuerdo con este enfoque?
2. **Recepción de la "Resolución Formal":**
   El brief indica que el jugador envía una resolución final explicando la trama.
   * **Problema:** Si lo envía por email abierto, la IA (el Director) deberá leerlo, entender un razonamiento no estructurado, y compararlo contra la "verdad". Esto es altamente propenso a alucinaciones.
   * **Propuesta:** ¿Preferimos validarlo por email y asumir el riesgo narrativo configurando al LLM para evaluar rigurosamente con "output estructurado", o usamos un formulario web final externo temporal para que someta evidencia y nombres con casillas estructuradas?
3. **El Costo del "Guardián de Tiempo" y los "Apuros":**
   Enviar correos proactivos para apurar al jugador requiere procesos en background consultando el estado y ejecutando LLMs sin interacción previa del cliente, lo que suma costos variables y recurrentes.
   * **Propuesta:** Para controlar costos en v1, limitaremos los apuros a eventos fijos (ej. a las 48hs de inactividad) usando plantillas curadas con ligera estocasticidad (o generadas con modelos más baratos), en lugar de usar un Master LLM que constantemente audite si debe o no hablar. ¿Conforme con cuidar así el presupuesto?
4. **Generación de Pruebas (Adjuntos):**
   * **Pregunta:** Las fotos, PDFs y recortes de prensa, ¿serán archivos estáticos pre-cargados por el guionista (barato, determinista) o generados por IA mid-juego (caro y riesgoso)?
   * **Propuesta Fuerte:** Que sean estáticos ("Assets" creados a mano) en la v1 para asegurar una calidad cinematográfica a las pruebas y evitar inconsistencias.

## Proposed Changes

La arquitectura base que prepararemos comprende un sistema Multi-Agente manejado mediante eventos asíncronos y webhooks.

### Componentes Core (El "Stack")

- **Lenguaje de Backend:** **Python**. Es nativo para los ecosistemas de LLMs rápidos y asíncronos (LangChain/LangGraph/PydanticAI).
- **Framework de Agentes / Orquestación:** **LangGraph** (o **PydanticAI**) para diseñar las máquinas de estados de los casos y orquestar al "Director", al "Guardián" y a los "NPCs".
- **Proveedor de Correo MTP (Manejo Transaccional):** **Resend** (o SendGrid/Postmark) configurado con un *Inbound Webhook* que convierte los emails del jugador en variables JSON hacia el backend.
- **Base de Datos:** **Supabase (PostgreSQL)** para guardar la memoria relacional de los casos (historias de usuario, hilos conversacionales completos, configuraciones de personajes).
- **LLM Principal:** **Gemini 1.5 Pro / Flash** (por su amplia ventana de contexto, crucial para recordar semanas de correos, y su costo-beneficio inmejorable para razonamientos largos).

### Flujo Técnico del Loop de Juego (Propuesta V1)

1. **Ingreso:** Una ruta webhook de la API recibe un payload JSON de Resend informando que el detective escribió a `testigo@casos...`.
2. **Normalización:** La API usa expresiones regulares o una pequeña capa LLM "Parser" para limpiar el email entrante (removemos firmas, advertencias de antivirus y el "historial" repetido que todo cliente de correo encadena al citar respuestas).
3. **Orquestación:**
   - La API despierta al agente orquestador en LangGraph, pasándole el contexto y el `state` del jugador consultado en base de datos.
   - El sistema decide en función del destinatario: ¿Va al testigo? Reúne el system_prompt del testigo, el "estado de la verdad" inmutable y lo que han charlado.
4. **Respuesta Latente:** Genera la respuesta del NPC, pero el **Guardián del Tiempo** determina enviarla no instantáneamente, sino en un *background task* (usando Redis Queue o Celery) tras X minutos u horas simulando latencia humana real.

## Open Questions

- Entiendo que la decisión respecto a si lanzamos en Español o Inglés (Sección 10) no bloquea la arquitectura técnica, ¿pero **comenzamos la prueba de concepto 100% en español**?
- Para la versión inicial y el MVP técnico, ¿estamos de acuerdo en limitar el desarrollo **únicamente al modo Individual**?
- Si apruebas este plan general, crearé un andamiaje base de FastAPI en Python y configuraremos nuestro primer punto final de webhook en falso (Mock) para testear la mecánica.

## Verification Plan

### Automated Tests
- Simulación de tráfico de correos "Inbound": Enviaremos peticiones JSON HTTP que calcan lo que un proveedor de email (ej. Resend) escupiría para asegurar que el pipeline lo decodifica y genera bien hacia LangGraph.

### Manual Verification
- Desplegaremos de forma local un túnel temporal (ej. ngrok/localtunnel) con un webhook funcional conectado a nuestro proveedor. Enviaremos emails desde una cuenta de Gmail personal al software para certificar el feeling del juego y el retraso realista del "Guardián".
