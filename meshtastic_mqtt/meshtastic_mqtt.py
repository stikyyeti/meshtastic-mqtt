# python3.6
# Comments assume subfolder: 'mesh_tastic_mqtt' is copied
# and is a subfolder of appdaemon/apps in Home Assistant Supervisor

# App Daemon config needs to be updated with requirements.txt

# swap for AppDaemon
# import portnums_pb2 as portnums_pb2
# from portnums_pb2 import ENVIRONMENTAL_MEASUREMENT_APP, POSITION_APP
import meshtastic_mqtt.portnums_pb2 as portnums_pb2
from meshtastic_mqtt.portnums_pb2 import ENVIRONMENTAL_MEASUREMENT_APP, POSITION_APP

import random
import json

# add for AppDaemon
# from google.protobuf.json_format import MessageToJson

# swap for AppDaemon
# import mesh_pb2 as mesh_pb2
# import mqtt_pb2 as mqtt_pb2
# import environmental_measurement_pb2
import meshtastic_mqtt.mesh_pb2 as mesh_pb2
import meshtastic_mqtt.mqtt_pb2 as mqtt_pb2
import meshtastic_mqtt.environmental_measurement_pb2 as environmental_measurement_pb2

from paho.mqtt import client as mqtt_client

import requests

from paho.mqtt import client as mqtt_client


#uncomment for AppDaemon
#import hassapi as hass

#swap for AppDaemon
#class MeshtasticMQTT(hass.Hass=None):
class MeshtasticMQTT():

    broker = '10.147.253.250'
    username = 'user'
    password = 'pass'
    port = 1883
    topic = "msh/1/c/#"
    # generate client ID with pub prefix randomly
    client_id = f'meshtastic-mqtt-{random.randint(0, 100)}'
    
    prefix = "meshtastic/"

    traccarHost = '10.147.253.250'


    def connect_mqtt(self) -> mqtt_client:
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                print("Connected to MQTT Broker!")
            else:
                print("Failed to connect, return code %d\n", rc)

        client = mqtt_client.Client(self.client_id)
        client.username_pw_set(self.username, self.password)
        client.on_connect = on_connect
        client.connect(self.broker, self.port)
        return client


    def subscribe(self, client: mqtt_client):
        def on_message(client, userdata, msg):
            #print(f"Received `{msg.payload.decode()}` from `{msg.topic}` topic")
            se = mqtt_pb2.ServiceEnvelope()
            se.ParseFromString(msg.payload)

            print(se)
            mp = se.packet
            if mp.decoded.portnum == portnums_pb2.POSITION_APP:
                pos = mesh_pb2.Position()
                pos.ParseFromString(mp.decoded.payload)
                print(getattr(mp, "from"))
                print(pos)
                owntracks_payload = {
                    "_type": "location",
                    "lat": pos.latitude_i * 1e-7,
                    "lon": pos.longitude_i * 1e-7,
                    "tst": pos.time,
                    "batt": pos.battery_level,
                    "alt": pos.altitude
                }
                if owntracks_payload["lat"] != 0 and owntracks_payload["lon"] != 0:
                    #client.publish("owntracks/"+str(getattr(mp, "from"))+"/meshtastic_node", json.dumps(owntracks_payload))
                    client.publish(self.prefix+str(getattr(mp, "from"))+"/position", json.dumps(owntracks_payload))
                    if len(self.traccarHost) > 0:
                        traccarURL = "http://"+self.traccarHost+":5055?id="+str(getattr(mp, "from"))+"&lat="+str(pos.latitude_i * 1e-7)+"&lon="+str(pos.longitude_i * 1e-7)+"&altitude="+str(pos.altitude)+"&battery_level="+str(pos.battery_level)+"&hdop="+str(pos.PDOP)+"&accuracy="+str(pos.PDOP*0.03)
                        print(traccarURL)
                        submitted = requests.get(traccarURL)
                        print(submitted)
                #lets also publish the battery directly
                if pos.battery_level > 0:
                    client.publish(self.prefix+str(getattr(mp, "from"))+"/battery", pos.battery_level)
            elif mp.decoded.portnum == ENVIRONMENTAL_MEASUREMENT_APP:
                env = environmental_measurement_pb2.EnvironmentalMeasurement()
                env.ParseFromString(mp.decoded.payload)
                print(env)
                client.publish(self.prefix+str(getattr(mp, "from"))+"/temperature", env.temperature)
                client.publish(self.prefix+str(getattr(mp, "from"))+"/relative_humidity", env.relative_humidity)
            elif mp.decoded.portnum == portnums_pb2.NODEINFO_APP:
                info = mesh_pb2.User()
                info.ParseFromString(mp.decoded.payload)
                #print(MessageToJson(info))
                client.publish(self.prefix+str(getattr(mp, "from"))+"/user", MessageToJson(info))
            elif mp.decoded.portnum == portnums_pb2.TEXT_MESSAGE_APP:
                text = {
                    "message": mp.decoded.payload.decode("utf-8"),
                    "from": getattr(mp, "from"),
                    "to": mp.to
                }
                client.publish(self.prefix+str(getattr(mp, "from"))+"/text_message", json.dumps(text))

        client.subscribe(self.topic)
        client.on_message = on_message


    def run(self): #on appdaemon remove the argument here
        client = self.connect_mqtt()
        self.subscribe(client)
        client.loop_forever()

    def initialize(self):
        self.run(self)

def main():
    mm = MeshtasticMQTT()
    mm.run()


#in appdaemon comment this block out
if __name__ == '__main__':
    main()
