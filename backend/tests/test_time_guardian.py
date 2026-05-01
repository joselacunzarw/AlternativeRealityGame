"""
Tests del Guardián del Tiempo.
Cubre: parsing de latencia, cálculo de delay, horarios imposibles.
No requiere LLM ni DB — pura lógica de negocio.
"""
import pytest
from datetime import datetime, timezone
from core.time_guardian import (
    parse_latency_from_prompt,
    calculate_delay_minutes,
    should_use_impossible_hour,
    adjust_for_impossible_hour,
)


class TestLatencyParsing:

    def test_rango_minutos(self):
        min_m, max_m = parse_latency_from_prompt("Respondés rápido, entre 5 y 15 minutos.")
        assert min_m == 5
        assert max_m == 15

    def test_rango_minutos_variante(self):
        min_m, max_m = parse_latency_from_prompt("Respondés entre 20 y 90 minutos, nunca inmediato.")
        assert min_m == 20
        assert max_m == 90

    def test_rango_horas(self):
        min_m, max_m = parse_latency_from_prompt("respondés lento, 2 a 4 horas.")
        assert min_m == 120
        assert max_m == 240

    def test_rango_horas_variante(self):
        min_m, max_m = parse_latency_from_prompt("Respondés en 1 a 3 horas, con pausas largas.")
        assert min_m == 60
        assert max_m == 180

    def test_unidades_mixtas_o(self):
        """'5 minutos o 6 horas' — separador 'o', unidades diferentes."""
        min_m, max_m = parse_latency_from_prompt("Latencia variable: 5 minutos o 6 horas, inestable.")
        assert min_m == 5
        assert max_m == 360

    def test_unidades_mixtas_y(self):
        """'entre 30 minutos y 24 horas' — separador 'y', unidades diferentes."""
        min_m, max_m = parse_latency_from_prompt("Respondés cuando te da la gana, entre 30 minutos y 24 horas.")
        assert min_m == 30
        assert max_m == 1440

    def test_valor_unico_genera_rango(self):
        """Valor único → rango de ±30% alrededor del valor."""
        min_m, max_m = parse_latency_from_prompt("Respondés rápido, 30 minutos.")
        assert min_m >= 15
        assert max_m <= 45
        assert min_m < max_m

    def test_default_sin_latencia(self):
        """Prompt sin mención de latencia → default (15, 60)."""
        min_m, max_m = parse_latency_from_prompt("Eres un personaje genérico.")
        assert min_m == 15
        assert max_m == 60


class TestDelayCalculation:

    def test_delay_dentro_de_rango(self):
        prompt = "Respondés entre 20 y 90 minutos."
        for _ in range(30):
            delay = calculate_delay_minutes(prompt)
            assert delay >= 2
            assert delay <= 100

    def test_intensidad_comprime_delay(self):
        prompt = "Respondés entre 60 y 120 minutos."
        delays_bajo = [calculate_delay_minutes(prompt, interaction_count=0) for _ in range(40)]
        delays_alto = [calculate_delay_minutes(prompt, interaction_count=15) for _ in range(40)]
        assert sum(delays_bajo) / len(delays_bajo) > sum(delays_alto) / len(delays_alto)

    def test_urgencia_reduce_delay(self):
        prompt = "Respondés entre 60 y 120 minutos."
        delays_normal = [calculate_delay_minutes(prompt, is_urgent=False) for _ in range(40)]
        delays_urgente = [calculate_delay_minutes(prompt, is_urgent=True) for _ in range(40)]
        assert sum(delays_normal) / len(delays_normal) > sum(delays_urgente) / len(delays_urgente)

    def test_delay_minimo_absoluto(self):
        """El delay nunca baja de 2 minutos aunque los factores sean máximos."""
        prompt = "Respondés rápido, entre 1 y 2 minutos."
        for _ in range(20):
            delay = calculate_delay_minutes(prompt, interaction_count=30, is_urgent=True)
            assert delay >= 2


class TestHorariosImposibles:

    def test_marta_dispara_en_multiplos_de_3(self):
        prompt = "horarios 'imposibles' para un humano"
        assert should_use_impossible_hour(prompt, 0) is True
        assert should_use_impossible_hour(prompt, 1) is False
        assert should_use_impossible_hour(prompt, 2) is False
        assert should_use_impossible_hour(prompt, 3) is True
        assert should_use_impossible_hour(prompt, 6) is True

    def test_personaje_normal_no_dispara(self):
        prompt = "Respondés rápido, entre 5 y 15 minutos."
        for i in range(10):
            assert should_use_impossible_hour(prompt, i) is False

    def test_ajuste_cae_entre_3_y_5_30_am(self):
        base = datetime(2026, 4, 26, 14, 30, 0, tzinfo=timezone.utc)
        for _ in range(20):
            adjusted = adjust_for_impossible_hour(base)
            assert 3 <= adjusted.hour <= 5
            if adjusted.hour == 5:
                assert adjusted.minute <= 30
