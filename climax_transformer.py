'''Receives raw xml data from climax devices and transforms into readable data for our system'''
import html
import logging
import asyncio
import slixmpp
import xmltodict


RECEIVER_JID = 'receive@inteli-xmpp'
RECEIVER_PASS = 'receive'
SEND_TO_JID = ['mike@inteli-xmpp', 'test@inteli-xmpp', 'translate@inteli-xmpp', 'guy@inteli-xmpp', 'kieran@inteli-xmpp']
SERVER = 'inteli-xmpp.australiaeast.cloudapp.azure.com'
DOMAIN = 'inteli-xmpp'

class EchoBot(slixmpp.ClientXMPP):
    '''Runs XMPP client which listens to incoming messages'''
    def __init__(self, jid, password):
        slixmpp.ClientXMPP.__init__(self, jid, password)
        print('Authenticated User')

        self.add_event_handler("session_start", self.start)
        self.add_event_handler("message", self.message)

    async def start(self, event):
        print('Starting..')
        self.send_presence()
        await self.get_roster()
        print('Starting Echobot')
        for i in SEND_TO_JID:
            self.send_message(mto=i, mbody="Echobot Running....")


    def translate_xml(self, xml, user):
        '''Translates Raw XML data to dict format'''
        x = xmltodict.parse(xml)['p']

        mac = x['mac']['@v']
        action = {'Referer': x['cmds']['referer']['@v'], 'Commands': {'act': x['cmds']['cmd']['@a'], 'ret': x['cmds']['cmd']['ret'], 'code': x['cmds']['cmd']['code'], 'M': x['cmds']['cmd']['m']}}
        com = action['Commands']['act']
        key = list(x['cmds']['cmd']['x'].keys())[0]
        other = x['cmds']['cmd']['x'][str(key)]

        transform = ''
        if com == 'getDeviceStatus':
            #Motion Sensor or Room Sensor
            key = list(other.keys())
            num = other['ty']['@v']
            if num == '4': #Door Sensor
                transform = {
                      'User': user + '-' + mac,
                      'EventTime': other['status_time']['@v'],
                      'FriendlyName': other['n']['@v'],
                      'SensorId': other['id']['@v'],
                      'DeviceType': 'DoorSensor',
                      'AreaNum': other['area']['@v'],
                      'ZoneNum': other['no']['@v'],
                      'SignalStrength': other['status_rssi']['@v'],
                      'DoorOpenStatus': other['status_open']['@v']
                      }
            elif num == '9': #Motion Sensor
                transform = {
                      'User': user + '-' + mac,
                      'EventTime': other['status_time']['@v'],
                      'FriendlyName': other['n']['@v'],
                      'SensorId': other['id']['@v'],
                      'DeviceType': 'MotionSensor',
                      'AreaNum': other['area']['@v'],
                      'ZoneNum': other['no']['@v'],
                      'SignalStrength': other['status_rssi']['@v'],
                      'MotionStatus': other['status_motion']['@v'],
                      }
            elif num == '40': #Temperature Sensor
                transform = {
                      'User': user + '-' + mac,
                      'EventTime': other['status_time']['@v'],
                      'FriendlyName': other['n']['@v'],
                      'SensorId': other['id']['@v'],
                      'DeviceType': 'TemperatureSensor',
                      'AreaNum': other['area']['@v'],
                      'ZoneNum': other['no']['@v'],
                      'SignalStrength': other['status_rssi']['@v'],
                      'Temperature': other['status_temp']['@v']
                      }
            elif num == '48': #Power Sensor
                transform = {
                      'User': user + '-' + mac,
                      'EventTime': other['status_time']['@v'],
                      'FriendlyName': other['n']['@v'],
                      'SensorId': other['id']['@v'],
                      'DeviceType': 'PowerSensor',
                      'AreaNum': other['area']['@v'],
                      'ZoneNum': other['no']['@v'],
                      'SignalStrength': other['status_rssi']['@v'],
                      'PowerUsage': other['status_power']['@v']
                      }
            elif num == '54': #MultiSensor
                transform = {
                        'User': user + '-' + mac,
                        'EventTime': other['status_time']['@v'],
                        'FriendlyName': other['n']['@v'],
                        'SensorId': other['id']['@v'],
                        'DeviceType': 'MultiSensor',
                        'AreaNum': other['area']['@v'],
                        'ZoneNum': other['no']['@v'],
                        'SignalStrength': other['status_rssi']['@v']
                        }
                if 'status_temp' in key:
                    transform['Temperature'] = other['status_temp']['@v']
                if 'status_humi' in key:
                    transform['Humidity'] = other['status_humi']['@v']
                if 'status_lux' in key:
                    transform['Brightness'] = other['status_lux']['@v']
            else:
                transform = 'New Sensor Type = ' + num + '\n'
                transform += str(x)
        else:  #Generic Printout
            key = list(x['cmds']['cmd']['x'].keys())
            transform = {
                  'User': user + '-' + mac,
                  'Command': com
                  }
            try:
                for i in other:
                    transform[i] = other[i]['@v']
            except:
                for i in key:
                  transform[i] = x['cmds']['cmd']['x'][i]['@v']
        return str(transform)+'\n'


    def message(self, msg):
        print('Message Recieved')
        fromuser = str(msg).split('from="')[1].split(str('@'+DOMAIN))[0]
        split = str(msg).split('<body>')
        f_msg = split[1].split('</body>')[0]
        f_msg = html.unescape(f_msg)

        if '<?xml version="1.0" encoding="UTF-8"?>' in f_msg:
            print('Translating Message')
            f_msg = self.translate_xml(f_msg, fromuser)
            for i in SEND_TO_JID:
                print('Sending Translation to:', i)
                self.send_message(mto=i, mbody=f_msg)

        if '/exitnow' in str(msg):
            print('Disconnecting...')
            self.disconnect()



if __name__ == '__main__':

    print('Starting up......................................')
    # Setup logging.
    logging.basicConfig(level=logging.DEBUG,
                        format='%(levelname)-8s %(message)s')

    logging.basicConfig(filename="log_file_test.log",
                                filemode='a',
                                format='%(levelname)-8s %(message)s',
                                level=logging.DEBUG)


    xmpp = EchoBot(RECEIVER_JID, RECEIVER_PASS)
    xmpp.register_plugin('xep_0030') # Service Discovery
    xmpp.register_plugin('xep_0004') # Data Forms
    xmpp.register_plugin('xep_0060') # PubSub
    xmpp.register_plugin('xep_0092') # Respond to openfire

    xmpp.register_plugin('xep_0199') # XMPP Ping

    # Connect to the XMPP server and start processing XMPP stanzas.
    xmpp.connect((SERVER,5222))
    xmpp.process(forever=False)
