import sys
import os
import json
import argparse
from datetime import datetime, timezone
from pathlib import Path

# Forzar UTF-8 en Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Configurar path para imports del proyecto
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.orchestrator import app_graph, cases_db
from database.database import SessionLocal
from database.models import User, GameSession
from langchain_core.messages import HumanMessage

# Configuración del detective de pruebas
TEST_EMAIL = "test@test.com"

class C:
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    END = '\033[0m'

# =====================================================================
# LIBRERÍA DE PLAYTHROUGHS (HAPPY PATHS)
# =====================================================================

PLAYTHROUGHS = {
    "caso_cero": [
        ("nicolas.ferrari", "Nicolás, recibí tus correos sobre Marta. ¿Qué piensas de todo esto?"),
        ("laura.soler", "Laura, estuve analizando los mensajes y son demasiado perfectos, casi matemáticos. ¿Estás usando una IA para imitar a tu hermana?"),
        ("director", "Director, he resuelto el caso 'Correspondencia Póstuma'. Descubrí que Laura Soler utiliza un modelo de lenguaje entrenado con los escritos de Marta para mantener su presencia viva y terminar su novela. Nicolás está siendo engañado por este software.")
    ],
    "grabacion_1": [
        ("osvaldo.carranza", "Alcalde, ¿qué sabe sobre la desaparición de Julián Belmonte en 1994?"),
        ("ruben.belmonte", "Rubén, ¿qué me puede decir de Ana Morel y sus grabaciones?"),
        ("ana.morel", "Ana, escuché el tren en tu audio. Sé que estás cerca de la casa del alcalde. ¿Osvaldo tiene algo que ver con Julián?"),
        ("director", "Director, caso 'La Grabación 1' resuelto. Ana Morel está viva y escondida. Ella descubrió que el alcalde Osvaldo Carranza fue el responsable de la desaparición de Julián Belmonte en 1994, no su padre Rubén. Ana lo probó con grabaciones ambientales.")
    ],
    "herencia_2": [
        ("isabel.valente", "Isabel, ¿cómo era tu relación con tu padre últimamente?"),
        ("santiago.valente", "Santiago, me resulta curioso que uses las mismas expresiones que el Dr. Farré. ¿Ya sabías que tu padre está fingiendo su muerte?"),
        ("dr.farre", "Dr. Farré, o debería decir... ¿Eduardo? La casa sigue habitada y Santiago ya lo sabe todo. Es hora de terminar el teatro."),
        ("director", "Director, he resuelto 'La Herencia'. El Dr. Farré es en realidad Eduardo Valente fingiendo su muerte. Santiago lo descubrió y manipuló el proceso. Recomiendo el final C: Eduardo toma el mando tras limpiar las mentiras de Santiago.")
    ],
    "martes_3": [
        ("juan.beretta", "Juan, ¿qué pasó realmente en Leiden con Hernán?"),
        ("hernan.dellarno", "Hernán, encontré los registros. Sí estuviste en Leiden. El Club de los Martes es real."),
        ("paula.vandijk", "Paula, sé lo de tu enfermedad y por qué Mira está fingiendo ser la secretaria. Quieres que Hernán recuerde."),
        ("director", "Director, caso 'El Club de los Martes' resuelto. Hernán sí estuvo en el equipo de Leiden. Todo es una intervención de Paula van Dijk y Juan Beretta para que Hernán recupere sus recuerdos antes de que Paula muera.")
    ],
    "novia_4": [
        ("elsa.acuna", "Doña Elsa, ¿me puede enviar la foto anónima de la boda?"),
        ("damian.villalba", "Damián, ¿por qué Pato sale en la foto en un horario distinto al que me dijiste?"),
        ("rocio.olmedo", "Rocío, sé que tú mandaste la foto. Protegeré tu identidad, cuéntame qué encontraste en el celular de Marisol."),
        ("director", "Director, resolución de 'La novia del pueblo'. Patricio Quiroga empujó a Marisol durante una discusión tras ser descubierta su relación oculta con Damián. Arreglaron la escena como suicidio. Rocío tiene las pruebas del celular.")
    ],
    "experimento_5": [
        ("elena.vasquez", "Dra. Vásquez, ¿qué detalles específicos hay en ese sueño del asesinato?"),
        ("silvia.moreno", "Silvia, ¿su marido Ignacio ha tenido algún diagnóstico médico recientemente? Me preocupa su salud."),
        ("ignacio.moreno", "Dr. Moreno, usted plantó el sueño en sus colegas. El hombre asesinado es usted. El glioblastoma lo está obligando a despedirse así."),
        ("director", "Director, he resuelto 'El Experimento'. No hay asesino real, es una sugestión pre-hipnótica plantada por el Dr. Ignacio Moreno, quien tiene un tumor terminal y usó el sueño para que sus colegas reconstruyan su vida.")
    ]
}

def setup_session(case_id):
    """Limpia sesiones anteriores e inicia una nueva en la DB."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == TEST_EMAIL).first()
        if not user:
            user = User(email=TEST_EMAIL, is_verified=1)
            db.add(user)
            db.flush()
        
        # Cerrar sesiones activas previas
        db.query(GameSession).filter(GameSession.user_id == user.id, GameSession.status == "active").update({"status": "abandonado"})
        
        # Crear nueva sesión
        new_session = GameSession(user_id=user.id, game_id=case_id, status="active")
        db.add(new_session)
        db.commit()
        db.refresh(new_session)
        return new_session.id
    except Exception as e:
        db.rollback()
        print(f"{C.RED}Error en DB Setup: {e}{C.END}")
        sys.exit(1)
    finally:
        db.close()

def run_playthrough(case_id):
    print(f"\n{C.BOLD}{C.CYAN}{'='*70}{C.END}")
    print(f"{C.BOLD}{C.CYAN}  SIMULADOR DE PARTIDA COMPLETE: {case_id}{C.END}")
    print(f"{C.BOLD}{C.CYAN}{'='*70}{C.END}")

    if case_id not in PLAYTHROUGHS:
        print(f"{C.RED}Error: No hay playthrough definido para {case_id}{C.END}")
        return False

    session_id = setup_session(case_id)
    print(f"{C.GREEN}[SYSTEM] Sesión de juego #{session_id} iniciada para {TEST_EMAIL}{C.END}")

    steps = PLAYTHROUGHS[case_id]
    
    # Thread ID persistente para la partida
    thread_id = f"sim_{case_id}_{datetime.now().strftime('%H%M%S')}"
    
    for i, (to_alias, text) in enumerate(steps):
        is_last = (i == len(steps) - 1)
        target_name = "Director" if to_alias == "director" else to_alias
        
        print(f"\n{C.YELLOW}>>> PASO {i+1}: Enviando a {target_name.upper()}{C.END}")
        print(f"{C.BOLD}Detective:{C.END} {text}")
        
        to_email = f"{to_alias}@casos.expedienteabierto.com"
        
        # Invocar Grafo
        state = {
            "from_email": TEST_EMAIL,
            "to_email": to_email,
            "subject": f"Resolución — {case_id}" if is_last else "Consulta de investigación",
            "text_content": text,
            "messages": [HumanMessage(content=text)]
        }
        
        try:
            result = app_graph.invoke(state, config={"configurable": {"thread_id": thread_id}})
            response = result.get("ai_response", "No response.")
            action = result.get("action_taken", "no_action")
            
            print(f"{C.CYAN}{target_name}:{C.END} {response[:300]}{'...' if len(response)>300 else ''}")
            print(f"{C.BLUE}[INFO] Action: {action}{C.END}")
            
        except Exception as e:
            print(f"{C.RED}FALLO EN EL GRAFO: {e}{C.END}")
            return False

    # Verificación Final en DB
    print(f"\n{C.BOLD}{C.YELLOW}--- VERIFICACIÓN FINAL EN DB ---{C.END}")
    db = SessionLocal()
    try:
        final_session = db.query(GameSession).filter(GameSession.id == session_id).first()
        print(f"Status esperado: completed | Actual: {C.BOLD}{final_session.status}{C.END}")
        print(f"Veredicto: {C.GREEN}{final_session.verdict}{C.END}")
        print(f"Cerrado en: {final_session.completed_at}")
        
        if final_session.status == "completed":
            print(f"\n{C.BOLD}{C.GREEN}[SUCCESS] CASO {case_id} GANADO Y REGISTRADO CORRECTAMENTE.{C.END}")
            return True
        else:
            print(f"\n{C.BOLD}{C.RED}[FAIL] El caso no se cerró en la DB.{C.END}")
            return False
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulador de Partidas de Expediente Abierto")
    parser.add_argument("case_id", nargs="?", help="ID del caso a simular (ej: caso_cero)")
    parser.add_argument("--all", action="store_true", help="Correr todos los playthroughs disponibles")
    args = parser.parse_args()

    if args.all:
        for cid in PLAYTHROUGHS:
            run_playthrough(cid)
    elif args.case_id:
        run_playthrough(args.case_id)
    else:
        print("Uso: python playthrough_simulator.py <case_id> o --all")
        print(f"Casos disponibles: {', '.join(PLAYTHROUGHS.keys())}")
