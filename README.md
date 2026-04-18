# Expediente Abierto - Alternate Reality Game

Motor de IA conversacional para un juego de rol de detectives interactivo basado en correo electrónico.

## Arquitectura del MVP
El sistema está construido íntegramente en Python utilizando una arquitectura de grafos para la Inteligencia Artificial.

### Componentes Principales:
1. **FastAPI (Webhook):** Recibe las interacciones textuales simulando la llegada de correos electrónicos.
2. **LangGraph (Motor Estáuico):** Administra el flujo del juego decidiendo si el jugador habla con un "Director del Juego" evaluador o con un "Personaje In-Game" (NPC).
3. **OpenAI (GPT-4o-mini):** Genera la narrativa de los personajes en base a estrictos System Prompts predefinidos.
4. **SQLAlchemy & LangGraph SqliteSaver:** Actúan en conjunto para generar un *Checkpointer*, dándole a la IA la capacidad psicológica de "recordar" el historial del jugador permanentemente leyendo desde el disco.

### Caso Cero: "Correspondencia Póstuma"
El repositorio inicia con la base de datos de personajes configurada para el **Caso Piloto**. Una escalofriante narrativa sobre un fantasma digital (una IA entrenada por una fallecida escritora) y un jugador atrapado en el dilema de apagarla o permitir que termine su novela final.

## Configuración Creador
Para levantar este servidor de desarrollo:
1. Clonar el repositorio.
2. Generar el entorno virtual dentro de la carpeta `backend` e instalar requisitos.
3. Modificar `backend/.env` colocando `OPENAI_API_KEY=tu_llave`.
4. Ejecutar el servidor con `python -m uvicorn main:app --port 8000`.
