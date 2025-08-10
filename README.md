Chile Alerta Sismo – Integración para Home Assistant
Esta integración personalizada permite mostrar en Home Assistant información en tiempo real de los últimos sismos reportados por el Centro Sismológico Nacional (CSN) de Chile, usando los datos de la API de ShakeMaps.
A diferencia de la API de GAEL, esta entrega latitud y longitud, lo que permite mostrar el evento en un mapa.

Características
Obtiene automáticamente los últimos sismos registrados en Chile.

Muestra magnitud, referencia geográfica, fecha y hora.

Incluye latitud y longitud para integración con tarjetas de mapa en Home Assistant.

Actualización automática cada 60 segundos.

Compatible con tarjetas Mushroom Template para personalización visual.

Colores dinámicos según magnitud:

Verde: Magnitud menor a 6.

Amarillo: Magnitud entre 6 y 7.

Naranja: Magnitud mayor o igual a 7.

Instalación
Copia la carpeta chile_alerta_sismo dentro de:

arduino
Copiar
Editar
/config/custom_components/
Reinicia Home Assistant.

Ve a Settings > Devices & Services > Add Integration.

Busca Chile Alerta Sismo y agrégala.

Sensores creados
Entidad	Descripción
sensor.chile_alerta_sismo_magnitud	Magnitud del último sismo.
sensor.chile_alerta_sismo_referencia	Lugar de referencia del sismo.
sensor.chile_alerta_sismo_hora	Fecha y hora UTC del evento.
sensor.chile_alerta_sismo_latitud	Latitud del epicentro.
sensor.chile_alerta_sismo_longitud	Longitud del epicentro.

Ejemplo de tarjeta Mushroom Template
yaml
Copiar
Editar
type: custom:mushroom-template-card
entity: sensor.chile_alerta_sismo_magnitud
icon: mdi:earthquake
primary: >
  {{ states('sensor.chile_alerta_sismo_magnitud') }} Mw
secondary: >
  {{ states('sensor.chile_alerta_sismo_referencia') }} ·
  {{ as_datetime(states('sensor.chile_alerta_sismo_hora')).
     strftime('%d-%m-%Y %H:%M') }}
icon_color: >
  {% set m = states('sensor.chile_alerta_sismo_magnitud') | float %}
  {% if m < 6 %}
    lightgreen
  {% elif m < 7 %}
    yellow
  {% else %}
    orange
  {% endif %}
multiline_secondary: true
fill_container: true
card_mod:
  style: |
    ha-card {
      background: white;
    }
Ejemplo de tarjeta de mapa
yaml
Copiar
Editar
type: map
entities:
  - entity: sensor.chile_alerta_sismo_magnitud
    name: Último Sismo
    latitude: "{{ states('sensor.chile_alerta_sismo_latitud') }}"
    longitude: "{{ states('sensor.chile_alerta_sismo_longitud') }}"
default_zoom: 6
hours_to_show: 1
Fuente de datos
Los datos provienen de la API pública de ShakeMaps del Centro Sismológico Nacional de Chile:
🔗 https://shakemaps.csn.uchile.cl/

