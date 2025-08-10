# Chile Alerta Sismo

Integración personalizada para [Home Assistant](https://www.home-assistant.io/) que obtiene información en tiempo real del último sismo reportado en Chile usando la API pública de [GAEL](https://api.gael.cloud/general/public/sismos).

## ✨ Funcionalidades

- Consulta automáticamente cada 60 segundos el último sismo registrado en Chile.
- Crea sensores automáticos con:
  - **Magnitud**
  - **Hora local del evento**
  - **Referencia geográfica**
  - **Latitud y longitud**
  - **Profundidad**
- Notificación push a la app móvil de Home Assistant si la magnitud es mayor a 7.0.
- Entidad de cámara que muestra un **mapa estático del epicentro**.
- Configuración 100% desde la interfaz de Home Assistant (no requiere YAML).
