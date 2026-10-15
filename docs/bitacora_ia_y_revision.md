# Bitácora de IA y revisión
La IA asistió en borradores de especificaciones, código de API, pruebas y documentación. Las decisiones se revisan con pruebas reproducibles, sin tomar salidas de IA como verdad automática.
1. Riesgo de doble reserva: se incorporó BEGIN IMMEDIATE y una prueba concurrente; ejecutar de nuevo tras cambios.
2. Recursos inexistentes: se agregaron pruebas de errores 404.
3. Estados duplicados: se añadieron pruebas de errores 409.
4. Conexiones SQLite: se utiliza contextlib.closing.
5. Aprobación de recomendaciones: requiere llamada explícita /review con identidad de la persona; no implica que exista una aprobación real previa de las specs.
**Pendiente de registro humano real:** nombres de revisores, fecha, defectos corregidos y aceptación de HU. Sin pruebas documentadas no afirmar validación.