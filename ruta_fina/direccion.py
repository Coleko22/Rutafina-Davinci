from __future__ import annotations


class Direccion:
    def __init__(
        self,
        id_direccion: int,
        calle: str,
        numero: str,
        localidad: str,
        codigo_postal: str,
        referencia: str = "",
        alias: str = "",
    ) -> None:
        self.id_direccion = id_direccion
        self.calle = calle
        self.numero = numero
        self.localidad = localidad
        self.codigo_postal = codigo_postal
        self.referencia = referencia
        self.alias = alias

    def modificarDireccion(self, **campos) -> None:
        for clave, valor in campos.items():
            if hasattr(self, clave):
                setattr(self, clave, valor)

    def __str__(self) -> str:
        alias = f"[{self.alias}] " if self.alias else ""
        return f"{alias}{self.calle} {self.numero}, {self.localidad} ({self.codigo_postal})"
