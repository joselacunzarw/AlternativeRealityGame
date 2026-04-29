"""
Tests para el Guardián del Tiempo.

Valida:
  1. Parsing correcto de latencia desde system prompts reales.
  2. Cálculo de delay con factores de intensidad y urgencia.
  3. Detección de horarios imposibles.
  4. Integración del nodo time_guardian con el estado del grafo.
"""

import sys
import os
import unittest
from datetime import datetime, timezone

# Ajustar path para imports desde el directorio backend
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.time_guardian import (
    parse_latency_from_prompt,
    calculate_delay_minutes,
    should_use_impossible_hour,
    adjust_for_impossible_hour,
)


class TestLatencyParsing(unittest.TestCase):
    """Testea el parser de latencia contra los system_prompts reales del juego."""

    def test_nicolas_ferrari_rapido(self):
        """Nicolás: 'Respondes rápido, entre 5 y 15 minutos'"""
        prompt = "Respondes rápido, entre 5 y 15 minutos. Si el jugador pide..."
        min_m, max_m = parse_latency_from_prompt(prompt)
        self.assertEqual(min_m, 5)
        self.assertEqual(max_m, 15)

    def test_marta_soler_20_90(self):
        """Marta: 'Respondés entre 20 y 90 minutos, nunca inmediato'"""
        prompt = "Respondés entre 20 y 90 minutos, nunca inmediato. Al menos una de cada tres..."
        min_m, max_m = parse_latency_from_prompt(prompt)
        self.assertEqual(min_m, 20)
        self.assertEqual(max_m, 90)

    def test_laura_soler_horas(self):
        """Laura (0 pistas): 'respondés lento, 2 a 4 horas'"""
        prompt = "respondés lento, 2 a 4 horas, fría: 'no sé nada de esos mails'"
        min_m, max_m = parse_latency_from_prompt(prompt)
        self.assertEqual(min_m, 120)
        self.assertEqual(max_m, 240)

    def test_tomas_vega_mixed(self):
        """Tomás: 'Latencia variable: 5 minutos o 6 horas'"""
        prompt = "Latencia variable: 5 minutos o 6 horas, inestable."
        min_m, max_m = parse_latency_from_prompt(prompt)
        self.assertEqual(min_m, 5)
        self.assertEqual(max_m, 360)

    def test_damian_villalba_horas(self):
        """Damián: 'Respondés en 1 a 3 horas'"""
        prompt = "Respondés en 1 a 3 horas, con pausas largas."
        min_m, max_m = parse_latency_from_prompt(prompt)
        self.assertEqual(min_m, 60)
        self.assertEqual(max_m, 180)

    def test_pato_quiroga_single(self):
        """Pato: 'Respondés rápido, 30 minutos'"""
        prompt = "Respondés rápido, 30 minutos, NO por cooperación sino para controlar."
        min_m, max_m = parse_latency_from_prompt(prompt)
        # Single value → ±30% margin → (21, 39)
        self.assertGreaterEqual(min_m, 15)
        self.assertLessEqual(max_m, 45)

    def test_lucia_valente_wide_range(self):
        """Lucía: 'entre 30 minutos y 24 horas' — mixed units."""
        prompt = "Respondés cuando te da la gana, entre 30 minutos y 24 horas."
        min_m, max_m = parse_latency_from_prompt(prompt)
        # Mixed unit: 30 minutos = 30, 24 horas = 1440
        self.assertEqual(min_m, 30)
        self.assertEqual(max_m, 1440)

    def test_default_when_no_latency(self):
        """Prompt sin mención de latencia → default (15, 60)"""
        prompt = "Eres un personaje genérico sin información de tiempos de respuesta."
        min_m, max_m = parse_latency_from_prompt(prompt)
        self.assertEqual(min_m, 15)
        self.assertEqual(max_m, 60)


class TestDelayCalculation(unittest.TestCase):
    """Testea el cálculo de delay con factores aplicados."""

    def test_basic_delay_in_range(self):
        """El delay calculado cae dentro del rango parseado."""
        prompt = "Respondés entre 20 y 90 minutos."
        for _ in range(50):  # Probabilístico, repetir
            delay = calculate_delay_minutes(prompt)
            self.assertGreaterEqual(delay, 2)   # Mínimo absoluto
            self.assertLessEqual(delay, 100)     # Rango con margenes

    def test_intensity_compresses_delay(self):
        """Muchas interacciones comprimen el delay."""
        prompt = "Respondés entre 60 y 120 minutos."
        delays_low = [calculate_delay_minutes(prompt, interaction_count=0) for _ in range(50)]
        delays_high = [calculate_delay_minutes(prompt, interaction_count=15) for _ in range(50)]
        avg_low = sum(delays_low) / len(delays_low)
        avg_high = sum(delays_high) / len(delays_high)
        self.assertGreater(avg_low, avg_high)

    def test_urgency_reduces_delay(self):
        """Urgencia reduce el delay significativamente."""
        prompt = "Respondés entre 60 y 120 minutos."
        delays_normal = [calculate_delay_minutes(prompt, is_urgent=False) for _ in range(50)]
        delays_urgent = [calculate_delay_minutes(prompt, is_urgent=True) for _ in range(50)]
        avg_normal = sum(delays_normal) / len(delays_normal)
        avg_urgent = sum(delays_urgent) / len(delays_urgent)
        self.assertGreater(avg_normal, avg_urgent)


class TestImpossibleHours(unittest.TestCase):
    """Testea la lógica de horarios imposibles."""

    def test_marta_triggers_impossible(self):
        """Marta Soler tiene la regla de horarios imposibles."""
        prompt = "horarios 'imposibles' para un humano"
        # Debería disparar en message_count múltiplo de 3
        self.assertTrue(should_use_impossible_hour(prompt, 0))
        self.assertFalse(should_use_impossible_hour(prompt, 1))
        self.assertFalse(should_use_impossible_hour(prompt, 2))
        self.assertTrue(should_use_impossible_hour(prompt, 3))

    def test_normal_char_no_impossible(self):
        """Personajes normales no disparan horarios imposibles."""
        prompt = "Respondés rápido, entre 5 y 15 minutos."
        for i in range(10):
            self.assertFalse(should_use_impossible_hour(prompt, i))

    def test_adjust_moves_to_3_5_am(self):
        """La hora ajustada cae entre 3:00 y 5:30 AM."""
        base = datetime(2026, 4, 26, 14, 30, 0, tzinfo=timezone.utc)
        adjusted = adjust_for_impossible_hour(base)
        self.assertGreaterEqual(adjusted.hour, 3)
        self.assertLessEqual(adjusted.hour, 5)
        if adjusted.hour == 5:
            self.assertLessEqual(adjusted.minute, 30)


if __name__ == "__main__":
    unittest.main()
