#!/usr/bin/env python
try:
    import polyinterface,logging
except ImportError:
    import pgc_interface as polyinterface
import sys
from urllib.request import urlopen
import xml.etree.ElementTree as ET
import time

LOGGER = polyinterface.LOGGER
#LOGGER.setLevel(logging.WARNING)
#LOGGER.setLevel(logging.INFO)
LOGGER.setLevel(logging.DEBUG)
_PARM_IP_ADDRESS_NAME = "NeurioIP"

class CT:
    def __init__(self, power, reactivePower, voltage):
        self.power = power
        self.reactivePower = reactivePower
        self.voltage = voltage

class Channel:
    def __init__(self, power, imported, exported, reactivePower, voltage):
        self.power = power
        self.imported = imported
        self.exported = exported
        self.reactivePower = reactivePower
        self.voltage = voltage

def pollSensor(self):
        url = 'http://%s/both_tables.html' % self.NeurioIP
        LOGGER.info('shortPoll - going to check Neurio stats @ {}'.format(url))
        with urlopen(url) as response:
                response_content = "<outer>"+response.read().decode("utf-8")+"</outer>"
        # LOGGER.debug('Neurio reply: {}'.format(response_content))
        root = ET.fromstring(response_content)
        tableIndex=0
        for table in root:
                rowIndex = 0
                for row in table:
                        columnIndex = 0;
                        power = 0
                        reactivePower = 0
                        voltage = 0
                        imported = 0
                        exported = 0
                        for column in row:
                                # LOGGER.debug("tableIndex = {}, columnIndex = {}, rowIndex = {}".format(tableIndex, columnIndex, rowIndex))
                                if rowIndex > 1:
                                        if tableIndex == 0:
                                                if columnIndex == 1:
                                                        power = column.text
                                                        ctNodeAddr = "ct"+str(rowIndex-1)
                                                        LOGGER.debug('nodes[{}].power = {}'.format(ctNodeAddr, power))
                                                        self.nodes[ctNodeAddr].setDriver('GV0', power)
                                                        self.nodes[ctNodeAddr].setDriver('ST', 1)
                                                elif columnIndex == 2:
                                                        reactivePower = column.text
                                                        ctNodeAddr = "ct"+str(rowIndex-1)
                                                        LOGGER.debug('nodes[{}].reactivePower = {}'.format(ctNodeAddr, reactivePower))
                                                        self.nodes[ctNodeAddr].setDriver('GV1', reactivePower)
                                                elif columnIndex == 3:
                                                        voltage = column.text
                                                        ctNodeAddr = "ct"+str(rowIndex-1)
                                                        LOGGER.debug('voltage - ctNodeAddr = {}'.format(ctNodeAddr))
                                                        self.nodes[ctNodeAddr].setDriver('GV2', voltage)
                                                        LOGGER.debug('nodes[{}].voltage = {}'.format(ctNodeAddr, voltage))
                                        else:
                                                if columnIndex == 1:
                                                        power = float(column.text)
                                                        channelNodeAddr = "channel"+str(rowIndex-1)
                                                        LOGGER.debug('nodes[{}].power = {}'.format(channelNodeAddr, power))
                                                        self.nodes[channelNodeAddr].setDriver('GV0', power)
                                                        self.nodes[channelNodeAddr].setDriver('ST', 1)
                                                elif columnIndex == 2:
                                                        imported = column.text
                                                        channelNodeAddr = "channel"+str(rowIndex-1)
                                                        LOGGER.debug('nodes[{}].imported = {}'.format(channelNodeAddr, imported))
                                                        self.nodes[channelNodeAddr].setDriver('GV3', imported)
                                                elif columnIndex == 3:
                                                        exported = column.text
                                                        channelNodeAddr = "channel"+str(rowIndex-1)
                                                        LOGGER.debug('nodes[{}].exported = {}'.format(channelNodeAddr, exported))
                                                        self.nodes[channelNodeAddr].setDriver('GV4', exported)
                                                elif columnIndex == 4:
                                                        reactivePower = column.text
                                                        channelNodeAddr = "channel"+str(rowIndex-1)
                                                        LOGGER.debug('nodes[{}].reactivePower = {}'.format(channelNodeAddr, reactivePower))
                                                        self.nodes[channelNodeAddr].setDriver('GV1', reactivePower)
                                                elif columnIndex == 5:
                                                        voltage = column.text
                                                        channelNodeAddr = "channel"+str(rowIndex-1)
                                                        LOGGER.debug('nodes[{}].voltage = {}'.format(channelNodeAddr, voltage))
                                                        self.nodes[channelNodeAddr].setDriver('GV2', voltage)
                                columnIndex += 1
                        rowIndex += 1
                tableIndex += 1
        return

class Controller(polyinterface.Controller):
    def __init__(self, polyglot):
        super(Controller, self).__init__(polyglot)
        self.name = 'Neurio Controller'
        self.poly.onConfig(self.process_config)

    def start(self):
        # This grabs the server.json data and checks profile_version is up to date
        serverdata = self.poly.get_server_data()
        LOGGER.info('Started Neurio NodeServer {}'.format(serverdata['version']))
        LOGGER.debug('GV1=%s',self.getDriver('GV1'))
        self.setDriver('GV2', 10)
        LOGGER.debug('GV1=%s',self.getDriver('GV1'))
        self.heartbeat(0)
        self.check_params()
        self.discover()
        self.poly.add_custom_config_docs("")
        pollSensor(self)

    def shortPoll(self):
        pollSensor(self)
        LOGGER.debug('shortPoll - done checking Neurio status')

    def longPoll(self):
        LOGGER.debug('longPoll')
        self.heartbeat()

    def query(self,command=None):
        self.check_params()
        for node in self.nodes:
            self.nodes[node].reportDrivers()

    def discover(self, *args, **kwargs):
        # add nodes
        for i in range(1, int(self.NumCTs)+1):
                LOGGER.debug('Adding CT {}'.format(i))
                ctaddr = "ct"+str(i)
                ctname = "CT"+str(i)
                self.addNode(CTNode(self, self.address, ctaddr, ctname))
          
        for i in range(1, int(self.NumChannels)+1):
                LOGGER.debug('Adding Channel {}'.format(i))
                channeladdr = "channel"+str(i)
                channelname = "Channel"+str(i)
                self.addNode(ChannelNode(self, self.address, channeladdr, channelname))
          
    def delete(self):
        LOGGER.info('Oh God I\'m being deleted. Nooooooooooooooooooooooooooooooooooooooooo.')

    def stop(self):
        LOGGER.debug('NodeServer stopped.')

    def process_config(self, config):
        # this seems to get called twice for every change, why?
        # What does config represent?
        LOGGER.info("process_config: Enter config={}".format(config));
        LOGGER.info("process_config: Exit");

    def heartbeat(self,init=False):
        LOGGER.debug('heartbeat: init={}'.format(init))
        if init is not False:
            self.hb = init
        LOGGER.debug('heartbeat: hb={}'.format(self.hb))
        if self.hb == 0:
            self.reportCmd("DON",2)
            self.hb = 1
        else:
            self.reportCmd("DOF",2)
            self.hb = 0

    def check_params(self):
        default_ip = "0.0.0.0"
        default_numcts = 4
        default_numchannels = 6
        self.removeNoticesAll()

        if 'DebugLevel' in self.polyConfig['customParams']:
            LOGGER.debug('DebugLevel found in customParams')
            self.DebugLevel = self.polyConfig['customParams']['DebugLevel']
            LOGGER.debug('check_params: DebugLevel is: {}'.format(self.DebugLevel))
            if self.DebugLevel == '':
                LOGGER.debug('check_params: DebugLevel is empty')
                self.DebugLevel = int(logging.INFO)
                LOGGER.debug('check_params: DebugLevel is defined in customParams, but is blank - please update it.  Using {}'.format(self.DebugLevel))
                self.addNotice('Set \'DebugLevel\' and then restart')
                st = False
        else:
            LOGGER.debug('check_params: DebugLevel does not exist self.polyCconfig: {}'.format(self.polyConfig))
            self.DebugLevel = int(logging.INFO)
            LOGGER.debug('check_params: DebugLevel not defined in customParams, setting to {}'.format(self.DebugLevel))
            st = False

        # convert string to int
        self.DebugLevel = int(self.DebugLevel)

        # Set the debug level based on parameter
        LOGGER.setLevel(self.DebugLevel)
        LOGGER.warning('Setting debug level to {}'.format(self.DebugLevel))
        self.setDriver('GV1', self.DebugLevel)
        LOGGER.warning('Done setting debug level to {}'.format(self.DebugLevel))

        if 'NeurioIP' in self.polyConfig['customParams']:
            LOGGER.debug('NeurioIP found in customParams')
            self.NeurioIP = self.polyConfig['customParams']['NeurioIP']
            LOGGER.debug('check_params: NeurioIP is: {}'.format(self.NeurioIP))
            if self.NeurioIP == '':
                LOGGER.debug('check_params: NeurioIP is empty')
                self.NeurioIP = default_ip
                LOGGER.debug('check_params: NeurioIP is defined in customParams, but is blank - please update it.  Using {}'.format(self.NeurioIP))
                self.addNotice('Set \'NeurioIP\' and then restart')
                st = False
        else:
            LOGGER.debug('check_params: NeurioIP does not exist self.polyCconfig: {}'.format(self.polyConfig))
            self.NeurioIP = default_ip
            LOGGER.debug('check_params: NeurioIP not defined in customParams, please update it.  Using {}'.format(self.NeurioIP))
            self.addNotice('Set \'NeurioIP\' and then restart')
            st = False

        if 'NumChannels' in self.polyConfig['customParams']:
            LOGGER.debug('NumChannels found in customParams')
            self.NumChannels = self.polyConfig['customParams']['NumChannels']
            LOGGER.debug('check_params: NumChannels is: {}'.format(self.NumChannels))
            if self.NumChannels == '':
                LOGGER.debug('check_params: NumChannels is empty')
                self.NumChannels = default_numchannels
                LOGGER.debug('check_params: NumChannels is defined in customParams, but is blank - please update it.  Using {}'.format(self.NumChannels))
                self.addNotice('Set \'NumChannels\' and then restart')
                st = False
        else:
            LOGGER.debug('check_params: NumChannels does not exist self.polyCconfig: {}'.format(self.polyConfig))
            self.NumChannels = default_numchannels
            LOGGER.debug('check_params: NumChannels not defined in customParams, please update it.  Using {}'.format(self.NumChannels))
            self.addNotice('Set \'NumChannels\' and then restart')
            st = False

        if 'NumCTs' in self.polyConfig['customParams']:
            LOGGER.debug('NumCTs found in customParams')
            self.NumCTs = self.polyConfig['customParams']['NumCTs']
            LOGGER.debug('check_params: NumCTs is: {}'.format(self.NumCTs))
            if self.NumCTs == '':
                LOGGER.debug('check_params: NumCTs is empty')
                self.NumCTs = default_cts
                LOGGER.debug('check_params: NumCTs is defined in customParams, but is blank - please update it.  Using {}'.format(self.NumCTs))
                self.addNotice('Set \'NumCTs\' and then restart')
                st = False
        else:
            LOGGER.debug('check_params: NumCTs does not exist self.polyCconfig: {}'.format(self.polyConfig))
            self.NumCTs = default_numcts
            LOGGER.debug('check_params: NumCTs not defined in customParams, please update it.  Using {}'.format(self.NumCTs))
            self.addNotice('Set \'NumCTs\' and then restart')
            st = False

        if self.NumChannels == 0:
            self.addNotice('Set \'NumChannels\' and then restart')

        if self.NumCTs == 0:
            self.addNotice('Set \'NumCTs\' and then restart')

        LOGGER.debug('Done checking: NeurioIP = {}'.format(self.NeurioIP))

        # Make sure they are in the params
        self.addCustomParam({'DebugLevel': self.DebugLevel, 'NeurioIP': self.NeurioIP, 'NumChannels': self.NumChannels, 'NumCTs':self.NumCTs})

    def remove_notice_test(self,command):
        LOGGER.info('remove_notice_test: notices={}'.format(self.poly.config['notices']))
        # Remove all existing notices
        self.removeNotice('test')

    def remove_notices_all(self,command):
        LOGGER.info('remove_notices_all: notices={}'.format(self.poly.config['notices']))
        # Remove all existing notices
        self.removeNoticesAll()

    def update_profile(self,command):
        LOGGER.info('update_profile:')
        st = self.poly.installprofile()
        return st

    def set_debug_level(self,command):
        self.DebugLevel = int(command['value'])
        self.setDriver('GV1', self.DebugLevel)

        # Make sure they are in the params
        self.addCustomParam({'DebugLevel': self.DebugLevel, 'NeurioIP': self.NeurioIP, 'NumChannels': self.NumChannels, 'NumCTs':self.NumCTs})

    id = 'controller'
    commands = {
        'QUERY': query,
        'DISCOVER': discover,
        'UPDATE_PROFILE': update_profile,
        'REMOVE_NOTICES_ALL': remove_notices_all,
        'REMOVE_NOTICE_TEST': remove_notice_test,
        'SET_DEBUG_LEVEL': set_debug_level
    }
    drivers = [{'driver': 'ST',  'value': 0, 'uom': 2},
               {'driver': 'GV1', 'value': 0, 'uom': 25}]


class CTNode(polyinterface.Node):
    def __init__(self, controller, primary, address, name):
        super(CTNode, self).__init__(controller, primary, address, name)

    def start(self):
        pass

    def shortPoll(self):
        LOGGER.debug('CTNode - shortPoll')

    def longPoll(self):
        LOGGER.debug('CTNode - longPoll')

    def setOn(self, command):
        self.setDriver('ST', 1)

    def setOff(self, command):
        self.setDriver('ST', 0)

    def query(self,command=None):
        self.reportDrivers()

    # hint = [1,2,3,4]
    drivers = [
        {'driver':  'ST', 'value': 0, 'uom': 2},
        {'driver': 'GV0', 'value': 0, 'uom': 73},
        {'driver': 'GV1', 'value': 0, 'uom': 0},
        {'driver': 'GV2', 'value': 0, 'uom': 72},
        {'driver': 'GV3', 'value': 0, 'uom': 33}
    ]
    id = 'ctnode'
    commands = {
        'DON': setOn, 'DOF': setOff
    }

class ChannelNode(polyinterface.Node):
    def __init__(self, controller, primary, address, name):
        super(ChannelNode, self).__init__(controller, primary, address, name)

    def start(self):
        pass

    def shortPoll(self):
        LOGGER.debug('ChannelNode - shortPoll')

    def longPoll(self):
        LOGGER.debug('ChannelNode - longPoll')

    def setOn(self, command):
        self.setDriver('ST', 1)

    def setOff(self, command):
        self.setDriver('ST', 0)

    def query(self,command=None):
        self.reportDrivers()

    # hint = [1,2,3,4]
    drivers = [
        {'driver':  'ST', 'value': 0, 'uom': 2},
        {'driver': 'GV0', 'value': 0, 'uom': 73},
        {'driver': 'GV1', 'value': 0, 'uom': 0},
        {'driver': 'GV2', 'value': 0, 'uom': 72},
        {'driver': 'GV3', 'value': 0, 'uom': 33},
        {'driver': 'GV4', 'value': 0, 'uom': 33}
    ]
    id = 'channelnode'
    commands = {
        'DON': setOn, 'DOF': setOff
    }

if __name__ == "__main__":
    try:
        polyglot = polyinterface.Interface('NeurioNS')
        """
        Instantiates the Interface to Polyglot.
        The name doesn't really matter unless you are starting it from the
        command line then you need a line Template=N
        where N is the slot number.
        """
        polyglot.start()
        """
        Starts MQTT and connects to Polyglot.
        """
        control = Controller(polyglot)
        """
        Creates the Controller Node and passes in the Interface
        """
        control.runForever()
        """
        Sits around and does nothing forever, keeping your program running.
        """
    except (KeyboardInterrupt, SystemExit):
        LOGGER.warning("Received interrupt or exit...")
        """
        Catch SIGTERM or Control-C and exit cleanly.
        """
        polyglot.stop()
    except Exception as err:
        LOGGER.error('Excption: {0}'.format(err), exc_info=True)
    sys.exit(0)
