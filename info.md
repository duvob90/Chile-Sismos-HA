# Chile Alerta Sismo

**Chile Alerta Sismo** es una integración personalizada para Home Assistant que permite monitorear en tiempo real el último sismo registrado a través de la API pública de [Chile Alerta](https://github.com/TBMSP/Chile-Alerta-API). Esta integración está diseñada para usuarios en Chile o interesados en sismos en la región de Chile.

## Características
- **Consulta automática**: La integración consulta cada minuto el último sismo registrado utilizando la API de Chile Alerta (con `user=demo` por defecto). No requiere configuración manual de horarios ni automatizaciones para la actualización.
- **Sensores de datos sísmicos**: Al instalar la integración, se crean automáticamente varios sensores que muestran la información del último sismo:
  - Magnitud del sismo.
  - Hora local del evento (hora de Chile continental).
  - Ubicación de referencia (descripción geográfica proporcionada).
  - Latitud y longitud del epicentro.
  - Escala de magnitud reportada (por ejemplo, Mw, ML, Mb).
  - Profundidad del sismo en kilómetros.
- **Notificaciones push**: Si el sismo supera la magnitud 7.0, la integración envía una notificación push a la app móvil de Home Assistant para alertar inmediatamente al usuario. De forma predeterminada, si no se configura un servicio de notificador específico, se utiliza una **Notificación Persistente** en Home Assistant (lo que genera una alerta visible en la app). El usuario puede configurar en las opciones de la integración qué servicio de notificación móvil desea utilizar (por ejemplo, su dispositivo móvil específico).
- **Mapa del epicentro**: La integración incluye una entidad de cámara que muestra un mapa estático con la ubicación del epicentro del último sismo. Esta imagen se genera automáticamente (utilizando mapas de OpenStreetMap) y es especialmente útil para visualizar la ubicación cuando ocurre un sismo de gran magnitud (>= 7.0). El mapa puede añadirse en el panel Lovelace como una tarjeta de imagen o cámara para su visualización.
- **Configuración vía UI**: No es necesario editar archivos YAML. La integración se instala vía HACS como repositorio personalizado y luego se añade desde la interfaz de Integraciones de Home Assistant. Se puede proporcionar opcionalmente un nombre de usuario de la API de Chile Alerta si se dispone de uno propio (de lo contrario, se usa el demo por defecto). También se pueden ajustar las opciones (servicio de notificación para push) desde la interfaz.

## Instalación
1. **Añadir a HACS**: En HACS, agregar este repositorio personalizado (`chile_alerta_sismo`) como integración.
2. **Instalar la integración**: Buscar "Chile Alerta Sismo" en HACS e instalarla.
3. **Agregar la integración en Home Assistant**: Ir a *Configuración -> Dispositivos y Servicios -> Añadir Integración* y buscar "Chile Alerta Sismo". Seleccionarla y completar el flujo de configuración (por defecto no requiere más que confirmar).
4. **Configurar notificaciones (opcional)**: Después de agregar la integración, puede ir a las opciones de la integración para especificar el servicio de notificador móvil de Home Assistant al cual enviar alertas (por ejemplo `notify.mobile_app_mi_telefono`). Si no se especifica, se usarán notificaciones persistentes.

Una vez configurada, los sensores aparecerán automáticamente. Puede agregar tarjetas en su tablero Lovelace para mostrar estos sensores (por ejemplo, una tarjeta de entidades listando magnitud, profundidad, etc., y una tarjeta de mapa/cámara mostrando el epicentro).

## Notas
- El **usuario demo** de la API tiene un límite de 1 solicitud por minuto. La integración cumple con este límite consultando cada 60 segundos. Si tiene una cuenta propia de la API de Chile Alerta (recomendado para uso intensivo), puede ingresarla en la configuración.
- El mapa del epicentro utiliza mapas de OpenStreetMap de forma estática. Se muestra siempre el último sismo, pero puede resultar especialmente útil ante eventos mayores. Puede ocultar o mostrar esta tarjeta según sus preferencias.
- Esta integración es una iniciativa de la comunidad y no es una integración oficial de Home Assistant.

¡Disfruta de un monitoreo sísmico actualizado directamente en tu Home Assistant!
