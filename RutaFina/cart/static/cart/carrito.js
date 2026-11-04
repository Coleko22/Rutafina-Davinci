/*
 * Mejora progresiva del carrito: los formularios con [data-carrito-form] se
 * envían con fetch y el servidor devuelve solo el panel del carrito (ver
 * cart/views.py). Si algo falla o JavaScript está desactivado, los formularios
 * funcionan igual como POST normal con redirect.
 */
(function () {
    'use strict';

    document.addEventListener('submit', function (evento) {
        var form = evento.target;
        if (!form.matches || !form.matches('[data-carrito-form]')) {
            return;
        }
        evento.preventDefault();

        var aviso = form.getAttribute('data-confirm');
        if (aviso && !window.confirm(aviso)) {
            return;
        }

        var boton = form.querySelector('button[type="submit"]');
        var foco = boton && boton.getAttribute('data-foco');
        if (boton) {
            boton.disabled = true;
        }

        fetch(form.action, {
            method: 'POST',
            body: new FormData(form),
            credentials: 'same-origin',
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        })
            .then(function (respuesta) {
                if (!respuesta.ok) {
                    throw new Error('HTTP ' + respuesta.status);
                }
                return respuesta.text();
            })
            .then(function (html) {
                var panel = document.getElementById('carrito');
                panel.outerHTML = html;
                // El botón que se apretó se reemplazó: devolvemos el foco al equivalente (teclado).
                var nuevo = foco && document.querySelector('[data-foco="' + foco + '"]');
                if (nuevo) {
                    nuevo.focus();
                }
                if (boton) {
                    boton.disabled = false; // por si era un botón de la carta (no se reemplaza)
                }
            })
            .catch(function () {
                form.submit(); // plan B: POST normal (submit() no vuelve a disparar este listener)
            });
    });
})();
