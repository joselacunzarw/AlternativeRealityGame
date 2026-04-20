import requests

url = "http://127.0.0.1:8001/api/v1/webhook/inbound"

print("--- INICIANDO EL CASO CERO ---")
print("El detective le escribe a Nicolás Ferrari (El Editor) tras ver su anuncio de auxilio.")

payload_inicio = {
    "from_email": "detective_privado@gmail.com",
    "to_email": "nicolas.ferrari@casos.expedienteabierto.com",
    "subject": "Respuesta a su solicitud de servicios",
    "text": "Señor Ferrari, me indicaron en la Agencia que usted estaba aterrado y requería un investigador discreto. ¿Qué ocurre con su escritora muerta? Cuénteme todo."
}

try:
    response = requests.post(url, json=payload_inicio)
    data = response.json()
    print("\n[Respuesta del Servidor / Gemini]:")
    print(data.get("ai_response", "Error de lectura"))
except requests.exceptions.ConnectionError:
    print("Error: Asegúrate de que el servidor FastAPI esté corriendo y que la API Key en .env sea válida.")
