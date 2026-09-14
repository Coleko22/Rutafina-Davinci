from __future__ import annotations

from datetime import date


class Promocion:
    def __init__(
        self,
        id_promocion: int,
        titulo: str,
        descripcion: str,
        porcentaje_descuento: float,
        fecha_inicio: date,
        fecha_fin: date,
        estado: str = "activa",
    ) -> None:
        self.id_promocion = id_promocion
        self.titulo = titulo
        self.descripcion = descripcion
        self.porcentaje_descuento = porcentaje_descuento
        self.fecha_inicio = fecha_inicio
        self.fecha_fin = fecha_fin
        self.estado = estado

    def estaVigente(self, fecha: date | None = None) -> bool:
        fecha = fecha or date.today()
        return (
            self.estado == "activa"
            and self.fecha_inicio <= fecha <= self.fecha_fin
        )

    def calcularDescuento(self, monto: float) -> float:
        if not self.estaVigente():
            return 0.0
        return round(monto * (self.porcentaje_descuento / 100), 2)

    def __repr__(self) -> str:
        return f"Promocion({self.titulo}, {self.porcentaje_descuento}%)"
