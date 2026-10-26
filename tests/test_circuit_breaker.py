import pytest

from app.resilience.circuit_breaker import CircuitBreaker, CircuitoAbierto, EstadoCircuito


class Reloj:
    t = 0.0

    def __call__(self):
        return self.t


def falla():
    raise RuntimeError("x")


def test_abre_tras_umbral_de_fallos():
    cb = CircuitBreaker(3, 30, Reloj())
    for _ in range(3):
        with pytest.raises(RuntimeError):
            cb.llamar(falla)
    assert cb.estado is EstadoCircuito.ABIERTO
    with pytest.raises(CircuitoAbierto):
        cb.llamar(lambda: 1)


def test_exito_reinicia_contador():
    cb = CircuitBreaker(3, 30, Reloj())
    for _ in range(2):
        with pytest.raises(RuntimeError):
            cb.llamar(falla)
    assert cb.llamar(lambda: "ok") == "ok" and cb.fallos == 0


def test_semiabierto_y_recuperacion():
    r = Reloj()
    cb = CircuitBreaker(2, 30, r)
    for _ in range(2):
        with pytest.raises(RuntimeError):
            cb.llamar(falla)
    r.t = 31
    assert cb.estado is EstadoCircuito.SEMIABIERTO
    assert cb.llamar(lambda: 1) == 1 and cb.estado is EstadoCircuito.CERRADO


def test_semiabierto_vuelve_a_abrir_si_falla():
    r = Reloj()
    cb = CircuitBreaker(2, 30, r)
    for _ in range(2):
        with pytest.raises(RuntimeError):
            cb.llamar(falla)
    r.t = 31
    with pytest.raises(RuntimeError):
        cb.llamar(falla)
    assert cb.estado is EstadoCircuito.ABIERTO
