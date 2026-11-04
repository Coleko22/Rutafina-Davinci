/*
 * Mejoras progresivas del sitio. Todo funciona sin JavaScript; esto solo
 * agrega comodidades:
 *   - [data-autosubmit]: los <select> envían su formulario al cambiar (ordenar comercios).
 *   - [data-pago]: muestra los datos de tarjeta solo si el medio elegido es Tarjeta.
 *   - [data-tarjeta-numero]/[data-vencimiento]: formatea número de tarjeta y MM/AA mientras se escribe.
 *   - [data-foto-input]: vista previa de la foto de perfil antes de guardar.
 *   - Cierra el menú de dirección del header al hacer clic afuera.
 */
(function () {
    'use strict';

    document.addEventListener('change', function (e) {
        var el = e.target;
        if (el.matches('[data-autosubmit]') && el.form) {
            el.form.submit();
        }
        if (el.matches('[data-pago]')) {
            actualizarPago();
        }
        if (el.matches('[data-foto-input]') && el.files && el.files[0]) {
            var destino = document.querySelector('[data-foto-preview]');
            if (destino) {
                var img = document.createElement('img');
                img.alt = '';
                img.src = URL.createObjectURL(el.files[0]);
                destino.textContent = '';
                destino.appendChild(img);
            }
        }
    });

    function actualizarPago() {
        var elegido = document.querySelector('[data-pago]:checked');
        var datos = document.querySelector('[data-datos-tarjeta]');
        if (!datos) { return; }
        var esTarjeta = !elegido || elegido.value === 'Tarjeta';
        datos.hidden = !esTarjeta;
        datos.querySelectorAll('input').forEach(function (input) {
            input.disabled = !esTarjeta;
        });
    }

    document.addEventListener('input', function (e) {
        var el = e.target;
        if (el.matches('[data-tarjeta-numero]')) {
            var digitos = el.value.replace(/\D/g, '').slice(0, 19);
            el.value = digitos.replace(/(.{4})/g, '$1 ').trim();
        }
        if (el.matches('[data-vencimiento]')) {
            var v = el.value.replace(/\D/g, '').slice(0, 4);
            el.value = v.length > 2 ? v.slice(0, 2) + '/' + v.slice(2) : v;
        }
    });

    document.addEventListener('click', function (e) {
        document.querySelectorAll('details.rb-direccion[open]').forEach(function (menu) {
            if (!menu.contains(e.target)) { menu.removeAttribute('open'); }
        });
    });

    document.addEventListener('DOMContentLoaded', function () {
        actualizarPago();
        document.querySelectorAll('[data-autosubmit-btn]').forEach(function (b) { b.hidden = true; });
    });
})();
