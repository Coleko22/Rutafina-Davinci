# 🛵 RutaFina Delivery

Plataforma web de pedidos y entregas estilo PedidosYa / Rappi desarrollada con Django y Python.

---

## 🏗️ Arquitectura del Sistema: Patrón MVT (MVC en Django)

El proyecto se estructura siguiendo el patrón **Model-View-Template (MVT)**, variante de la arquitectura **Model-View-Controller (MVC)** implementada por Django:

* **Modelo (`Model`):**
  * Representado en los archivos `models.py` de cada app modular (`users/`, etc.).
  * Gestiona las reglas de negocio, tipos de atributos, relaciones y persistencia mediante el ORM de Django sobre SQLite.
  * Define el usuario personalizado (`AbstractUser`) con roles (`Cliente`, `Repartidor`, `Comercio`, `Admin`).

* **Controlador / Vista (`View`):**
  * Representado en `views.py` y `forms.py`.
  * Controla el flujo de peticiones HTTP (GET y POST), valida entradas de formularios, maneja sesiones/tokens de autenticación y transfiere el contexto de datos hacia la capa de presentación.

* **Vista / Plantilla (`Template`):**
  * Aloja la capa visual en el directorio `templates/`.
  * Utiliza el motor de plantillas de Django con herencia modular (`base.html`), inyección dinámica de variables y estilos responsivos mediante Bootstrap 5.

* **Núcleo de Configuración (`RutaFinaCore/`):**
  * `settings.py`: Parámetros globales, middlewares, aplicaciones registradas y directivas de autenticación.
  * `urls.py`: Enrutador central que delega los endpoints a cada aplicación modular.

---

## 🛠️ Tecnologías Utilizadas

* **Lenguaje:** Python 3.12+
* **Framework:** Django 6.1+
* **Frontend:** HTML5, CSS3, Bootstrap 5, Django Template Language (DTL)
* **Base de datos:** SQLite (desarrollo local)
* **Control de versiones:** Git, GitHub Desktop