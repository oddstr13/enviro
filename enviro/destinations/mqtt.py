from enviro import logging
from enviro.constants import UPLOAD_SUCCESS, UPLOAD_FAILED
from enviro.mqttsimple import MQTTClient
import ujson
import config

def log_destination():
  logging.info(f"> uploading cached readings to MQTT broker: {config.mqtt_broker_address}")

def upload_reading(reading):
  server = config.mqtt_broker_address
  username = config.mqtt_broker_username
  password = config.mqtt_broker_password
  nickname = reading["nickname"]
  
  try:
    if config.mqtt_broker_ca_file:
    # Using SSL
      f = open("ca.crt")
      ssl_data = f.read()
      f.close()
      mqtt_client = MQTTClient(reading["uid"], server, user=username, password=password, keepalive=60,
                               ssl=True, ssl_params={'cert': ssl_data})
    else:
    # Not using SSL
      mqtt_client = MQTTClient(reading["uid"], server, user=username, password=password, keepalive=60)
    # Now continue with connection and upload
    mqtt_client.connect()
    mqtt_client.publish(f"enviro/{nickname}", ujson.dumps(reading).encode("uft-8"), retain=True)
    mqtt_client.disconnect()
    return UPLOAD_SUCCESS

  # Try disconneting to see if it prevents hangs on this typew of errors recevied so far
  except (OSError, IndexError) as exc:
    try:
      import sys, io
      buf = io.StringIO()
      sys.print_exception(exc, buf)
      logging.debug(f"  - an exception occurred when uploading.", buf.getvalue())
      mqtt_client.disconnect()
    except Exception as exc:
      import sys, io
      buf = io.StringIO()
      sys.print_exception(exc, buf)
      logging.debug(f"  - an exception occurred when disconnecting mqtt client.", buf.getvalue())

  except Exception as exc:
    import sys, io
    buf = io.StringIO()
    sys.print_exception(exc, buf)
    logging.debug(f"  - an exception occurred when uploading.", buf.getvalue())

  return UPLOAD_FAILED

def hass_discovery(board_type):
  mqtt_discovery("Temperature", "temperature", "°C", "temperature", board_type) # Temperature
  mqtt_discovery("Pressure", "pressure", "hPa", "pressure", board_type) # Pressure
  mqtt_discovery("Humidity", "humidity", "%", "humidity", board_type) # Humidity
  mqtt_discovery("Voltage", "voltage", "V", "voltage", board_type) # Voltage
  if (board_type == "weather"):
    mqtt_discovery("Luminance", "illuminance", "lx", "luminance", board_type) # Luminance
    mqtt_discovery("Wind Speed", "wind_speed", "m/s", "wind_speed", board_type) # Wind Speed
    mqtt_discovery("Rain", "precipitation", "mm", "rain", board_type) # Rain
    mqtt_discovery("Rain Per Second", "precipitation_intensity", "mm/s", "rain_per_second", board_type) # Rain Per Second
    mqtt_discovery("Wind Direction", None, "°", "wind_direction", board_type, icon="mdi:compass-rose") # Wind Direction 
  elif (board_type == "grow"):
    mqtt_discovery("Luminance", "illuminance", "lx", "luminance", board_type) # Luminance
    mqtt_discovery("Moisture A", "humidity", "%", "moisture_a", board_type) # Moisture A
    mqtt_discovery("Moisture B", "humidity", "%", "moisture_b", board_type) # Moisture B
    mqtt_discovery("Moisture C", "humidity", "%", "moisture_c", board_type) # Moisture C
  elif (board_type == "indoor"):
    mqtt_discovery("Luminance", "illuminance", "lx", "luminance", board_type) # Luminance
    mqtt_discovery("Gas Resistance", None, "Ω", "gas_resistance", board_type, icon="mdi:gas-cylinder") # Gas Resistance
    mqtt_discovery("AQI", "aqi", "&", "aqi", board_type) # AQI
    mqtt_discovery("Colour Temperature", "temperature", "K", "color_temperature", board_type) # Colo(u)r Temperature
  elif (board_type == "urban"):
    mqtt_discovery("Noise", "voltage", "V", "noise", board_type) # Noise
    mqtt_discovery("PM1", "pm1", "µg/m³", "pm1", board_type) # PM1
    mqtt_discovery("PM2.5", "pm25", "µg/m³", "pm2_5", board_type) # PM2_5
    mqtt_discovery("PM10", "pm10", "µg/m³", "pm10", board_type) # PM10
  

def mqtt_discovery(name, device_class, unit, value_name, model, icon=None):
  server = config.mqtt_broker_address
  username = config.mqtt_broker_username
  password = config.mqtt_broker_password
  nickname = config.nickname
  from ucollections import OrderedDict
  obj = OrderedDict({
    "dev":
    {
      "ids":[nickname],
      "name":nickname,
      "mdl":"Enviro " + model,
      "mf":"Pimoroni"
    },
    "unit_of_meas":unit,
    "val_tpl":"{{ value_json.readings." + value_name +" }}",
    "state_cla": "measurement",
    "stat_t":"enviro/" + nickname,
    "name":name,
    "uniq_id":"sensor." + nickname + "." + value_name,
    "force_update":True,
    "expire_after":config.reading_frequency * config.upload_frequency * 60 * 3,
  })
  if icon is not None:
    obj["icon"] = icon
  if device_class is not None:
    obj["dev_cla"] = device_class
  try:
    # attempt to publish reading
    mqtt_client = MQTTClient(nickname, server, user=username, password=password, keepalive=60)
    mqtt_client.connect()
    mqtt_client.publish(f"homeassistant/sensor/{nickname}/{value_name}/config", ujson.dumps(obj).encode("utf-8"), retain=True, qos=1)
    mqtt_client.disconnect()
    return UPLOAD_SUCCESS
  except:
    logging.debug(f"  - an exception occurred when uploading")
    
