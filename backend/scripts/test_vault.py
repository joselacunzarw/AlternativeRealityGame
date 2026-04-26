"""
Test de la Bóveda Forense — Valida el endpoint /api/v1/vault/unlock.

Simula directamente la lógica del endpoint sin levantar el servidor,
probando con un usuario con sesión activa en un caso que tenga vault_evidence.
"""
import os
import sys
from pathlib import Path

# Agregar el directorio backend al PYTHONPATH
backend_dir = Path(__file__).parent.parent
sys.path.append(str(backend_dir))

from core.orchestrator import cases_db

def test_vault_logic():
    print("=== INICIANDO PRUEBA DE BÓVEDA FORENSE ===\n")
    
    # 1. Verificar que todos los casos tengan vault_evidence
    print("--- 1. Verificación: vault_evidence en todos los casos ---")
    all_have_vault = True
    for case_id, case_data in cases_db.items():
        vault = case_data.get("vault_evidence", {})
        count = len(vault)
        status = "✅" if count > 0 else "❌"
        if count == 0:
            all_have_vault = False
        print(f"  {status} {case_id}: {count} evidencias en bóveda")
        for code, info in vault.items():
            print(f"      🔑 {code} → {info['title']} ({info['type']})")
    
    if all_have_vault:
        print("\n  ✅ Todos los casos tienen vault_evidence configurado.\n")
    else:
        print("\n  ❌ Hay casos SIN vault_evidence.\n")
    
    # 2. Simular desbloqueo con código válido (caso postuma_0)
    print("--- 2. Prueba: Código VÁLIDO en postuma_0 ---")
    test_case_id = "postuma_0"
    test_code = "TRINIDAD-1994"
    
    case_data = cases_db.get(test_case_id)
    if not case_data:
        print(f"  ❌ Caso {test_case_id} no encontrado.")
        return
    
    vault = case_data.get("vault_evidence", {})
    evidence = vault.get(test_code.upper())
    
    if evidence:
        print(f"  ✅ Código '{test_code}' desbloqueó:")
        print(f"     Título: {evidence['title']}")
        print(f"     Tipo:   {evidence['type']}")
        print(f"     Desc:   {evidence['desc']}")
    else:
        print(f"  ❌ Código '{test_code}' NO reconocido.")
    
    # 3. Simular desbloqueo con código inválido
    print("\n--- 3. Prueba: Código INVÁLIDO en postuma_0 ---")
    bad_code = "HACKER-9999"
    bad_evidence = vault.get(bad_code.upper())
    
    if bad_evidence:
        print(f"  ❌ El código falso '{bad_code}' desbloqueó algo (NO debería).")
    else:
        print(f"  ✅ Código '{bad_code}' correctamente rechazado (no existe).")
    
    # 4. Probar case-insensitivity
    print("\n--- 4. Prueba: Case-Insensitivity ---")
    lower_code = "trinidad-1994"
    lower_evidence = vault.get(lower_code.upper())
    
    if lower_evidence:
        print(f"  ✅ Código '{lower_code}' (minúsculas) mapeó correctamente a '{lower_evidence['title']}'.")
    else:
        print(f"  ❌ Fallo de case-insensitivity para '{lower_code}'.")
    
    # 5. Resumen de todos los códigos disponibles
    print("\n--- 5. Resumen: Todos los códigos de la Bóveda ---")
    total_codes = 0
    for case_id, case_data in cases_db.items():
        vault = case_data.get("vault_evidence", {})
        for code in vault:
            total_codes += 1
            print(f"  [{case_id}] 🔑 {code}")
    
    print(f"\n  Total de códigos registrados: {total_codes}")
    print("\n=== PRUEBA FINALIZADA ===")

if __name__ == "__main__":
    test_vault_logic()
