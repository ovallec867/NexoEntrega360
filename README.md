# NexoEntrega 360 — Proyecto SDD con asistencia de IA
Equipo: Natalia Baena Torres, Ricardo Lora Gutiérrez, Samuel Ortega Carrascal, Carlos Ovalle Castaño y Valeria Patrón García.

Prototipo académico de API para solicitudes, inventario, reservas, entregas y recomendaciones automatizadas con aprobación humana. Las recomendaciones actuales utilizan reglas explícitas; no son un LLM. Requiere contrastar contra la rúbrica oficial.

## Ejecutar
Python 3.10+ sin dependencias adicionales.
```bash
python -m unittest discover -s tests -v
python -m app.server
```
Servidor: http://localhost:8000. Consultas GET: /health, /products, /requests, /deliveries, /decisions.

## Demostración
```bash
curl -X POST http://localhost:8000/products -H 'Content-Type: application/json' -d '{"name":"Caja","stock":10}'
curl -X POST http://localhost:8000/requests -H 'Content-Type: application/json' -d '{"customer":"Ana","product_id":1,"quantity":2}'
curl -X POST http://localhost:8000/requests/1/reserve -H 'Content-Type: application/json' -d '{}'
curl -X POST http://localhost:8000/deliveries -H 'Content-Type: application/json' -d '{"request_id":1,"assignee":"Luis"}'
curl -X POST http://localhost:8000/requests/1/suggest -H 'Content-Type: application/json' -d '{}'
curl -X POST http://localhost:8000/decisions/1/review -H 'Content-Type: application/json' -d '{"reviewer":"Ana","approved":true}'
```
## Documentación
Ver specs/HU-01..05.md, docs/architecture.md, docs/bitacora_ia_y_revision.md y docs/acta_revision_humana.md. Las aprobaciones y contribuciones deben ser reales. No usar este prototipo como servicio de producción: no incluye autenticación.
