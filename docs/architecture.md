# Arquitectura y contratos
API HTTP en Python con ThreadingHTTPServer; lógica de negocio en app/server.py; persistencia SQLite.
Entidades: products(id,name,stock); requests(id,customer,product_id,quantity,status,created_at); deliveries(id,request_id,assignee,status); decisions(id,request_id,suggestion,rationale,approved,reviewer).
Relaciones: solicitud N:1 producto; entrega 1:1 solicitud; decisión N:1 solicitud.
Contratos: GET /health, /products, /requests, /deliveries, /decisions. POST /products, /requests, /requests/{id}/reserve, /deliveries, /deliveries/{id}/complete, /requests/{id}/suggest, /decisions/{id}/review.
Respuestas JSON y errores 400/404/409. Reserva atómica con BEGIN IMMEDIATE. No autenticación, despliegue solo local; riesgo: revisión de autorización y auditoría antes de producción.