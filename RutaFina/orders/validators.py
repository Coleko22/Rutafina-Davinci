import re
from datetime import datetime

def validar_algoritmo_luhn(numero_tarjeta: str) -> bool:
    """Implementa el algoritmo de Luhn para validar números de tarjetas."""
    digitos = [int(d) for d in re.sub(r'\D', '', numero_tarjeta)]
    if len(digitos) < 13 or len(digitos) > 19:
        return False

    checksum = 0
    paridad = (len(digitos) - 2) % 2
    for i, digito in enumerate(digitos[:-1]):
        if i % 2 == paridad:
            digito *= 2
            if digito > 9:
                digito -= 9
        checksum += digito

    return (checksum + digitos[-1]) % 10 == 0

def detectar_tipo_tarjeta(numero_tarjeta: str) -> str:
    """Identifica el emisor según el prefijo BIN."""
    limpio = re.sub(r'\D', '', numero_tarjeta)
    if re.match(r'^4[0-9]{12}(?:[0-9]{3})?$', limpio):
        return 'Visa'
    elif re.match(r'^5[1-5][0-9]{14}$', limpio) or re.match(r'^2(?:22[1-9]|2[3-9][0-9]|[3-6][0-9]{2}|7[01][0-9]|720)[0-9]{12}$', limpio):
        return 'Mastercard'
    elif re.match(r'^3[47][0-9]{13}$', limpio):
        return 'American Express'
    elif re.match(r'^(?:6011|65[0-9]{2}|64[4-9][0-9])[0-9]{12}$', limpio):
        return 'Discover'
    return 'Desconocida'

def validar_vencimiento(mes: int, anio: int) -> bool:
    """Valida que la fecha de vencimiento sea a futuro."""
    hoy = datetime.now()
    if mes < 1 or mes > 12:
        return False
    # Si viene en formato 2 dígitos (ej: 26) lo pasamos a 2026
    anio_completo = anio if anio >= 2000 else 2000 + anio
    if anio_completo < hoy.year:
        return False
    if anio_completo == hoy.year and mes < hoy.month:
        return False
    return True