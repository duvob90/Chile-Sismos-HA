# Chile Alerta Sismo

**Chile Alerta Sismo** es una integración personalizada para Home Assistant que permite monitorear en tiempo real el último sismo registrado a través de la API pública de [GAEL](https://api.gael.cloud/general/public/sismos).  

Ideal para usuarios en Chile o interesados en actividad sísmica en la región.

---

## ✨ Características
- Consulta automática cada **60 segundos**.
- Crea sensores con:
  - Magnitud
  - Hora local del evento
  - Referencia geográfica
  - Latitud y longitud
  - Profundidad
- Envía notificaciones push en la app móvil de Home Assistant si el sismo tiene magnitud **≥ 7.0**.
- Incluye una cámara que muestra un **mapa estático** del epicentro.
- Configuración 100% vía UI (sin YAML).
