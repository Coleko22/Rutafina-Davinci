"""
Textos del sitio según el "Tono de la app" que el usuario elige en Preferencias.

Los templates usan {{ copy.clave }}; el context processor (users/context_processors.py)
elige el diccionario según users.Cliente.tono. Furioso es el tono de los mockups y
el que ven los usuarios sin cuenta.
"""

TEXTOS = {
    'FURIOSO': {
        'hero_1': 'Tenés hambre.',
        'hero_2': 'Nosotros, bronca.',
        'hero_sub': 'Comercios de tu barrio, repartidores que no frenan y un carrito que no te pregunta dos veces. Pedí y callate.',
        'cta': 'Pedí ya',
        'buscar': '¿Qué querés comer? Decidí ya',
        'login_1': 'Identificate.',
        'login_2': 'No tenemos todo el día.',
        'checkout_1': 'Último paso.',
        'checkout_2': 'No te arrepientas.',
        'seguimiento_1': 'Ya sale.',
        'seguimiento_2': 'Ahora esperá.',
        'historial_1': 'Todo lo que',
        'historial_2': 'ya te comiste.',
        'repartidor_2': 'A la calle.',
        'vacio': 'Todavía no agregaste nada. Elegí algo de la carta y aparece acá.',
    },
    'ENOJADO': {
        'hero_1': '¿Hambre?',
        'hero_2': 'Pedí de una vez.',
        'hero_sub': 'Comercios de tu barrio y repartidores que no se duermen. Elegí y listo.',
        'cta': 'Pedí ahora',
        'buscar': '¿Qué querés comer?',
        'login_1': 'Entrá.',
        'login_2': 'Dale, que se enfría.',
        'checkout_1': 'Último paso.',
        'checkout_2': 'Confirmá y listo.',
        'seguimiento_1': 'Ya sale.',
        'seguimiento_2': 'Bancá un toque.',
        'historial_1': 'Tus pedidos,',
        'historial_2': 'todos acá.',
        'repartidor_2': 'Hay calle.',
        'vacio': 'Todavía no agregaste nada. Elegí algo de la carta y aparece acá.',
    },
    'TRANQUI': {
        'hero_1': '¿Tenés hambre?',
        'hero_2': 'Te lo llevamos.',
        'hero_sub': 'Los comercios de tu barrio, a un par de clics. Elegí con calma.',
        'cta': 'Ver comercios',
        'buscar': '¿Qué tenés ganas de comer?',
        'login_1': 'Hola de nuevo.',
        'login_2': 'Ingresá a tu cuenta.',
        'checkout_1': 'Último paso.',
        'checkout_2': 'Revisá y confirmá.',
        'seguimiento_1': 'Tu pedido',
        'seguimiento_2': 'está en marcha.',
        'historial_1': 'Tus pedidos',
        'historial_2': 'y favoritos.',
        'repartidor_2': 'Buen turno.',
        'vacio': 'Tu carrito está vacío. Cuando agregues algo de la carta, aparece acá.',
    },
}

DEFAULT = 'FURIOSO'


def textos(tono):
    return TEXTOS.get(tono, TEXTOS[DEFAULT])
