#!/usr/bin/env python
try:
    import polyinterface,logging
except ImportError:
    import pgc_interface as polyinterface
import sys
from urllib.request import urlopen
import xml.etree.ElementTree as ET
import time
"""
Import the polyglot interface module. This is in pypy so you can just install it
normally. Replace pip with pip3 if you are using python3.

Virtualenv:
pip install polyinterface

Not Virutalenv:
pip install polyinterface --user

*I recommend you ALWAYS develop your NodeServers in virtualenv to maintain
cleanliness, however that isn't required. I do not condone installing pip
modules globally. Use the --user flag, not sudo.
"""

LOGGER = polyinterface.LOGGER
#LOGGER.setLevel(logging.WARNING)
#LOGGER.setLevel(logging.INFO)
LOGGER.setLevel(logging.DEBUG)
_PARM_IP_ADDRESS_NAME = "NeurioIP"

"""
polyinterface has a LOGGER that is created by default and logs to:
logs/debug.log
You can use LOGGER.info, LOGGER.warning, LOGGER.debug, LOGGER.error levels as needed.
"""

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
        cts = []
        channels = []
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
                                                elif columnIndex == 2:
                                                        reactivePower = column.text
                                                        ctNodeAddr = "ct"+str(rowIndex-1)
                                                        LOGGER.debug('nodes[{}].reactivePower = {}'.format(ctNodeAddr, reactivePower))
                                                        self.nodes[ctNodeAddr].setDriver('GV1', reactivePower)
                                                elif columnIndex == 3:
                                                        voltage = column.text
                                                        newCT = CT(power, reactivePower, voltage)
                                                        cts.append(newCT)
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
                                                        newChannel = Channel(power, imported, exported, reactivePower, voltage)
                                                        channels.append(newChannel)
                                                        channelNodeAddr = "channel"+str(rowIndex-1)
                                                        LOGGER.debug('nodes[{}].voltage = {}'.format(channelNodeAddr, voltage))
                                                        self.nodes[channelNodeAddr].setDriver('GV2', voltage)
                                columnIndex += 1
                        rowIndex += 1
                tableIndex += 1
        return cts, channels

class Controller(polyinterface.Controller):
    """
    The Controller Class is the primary node from an ISY perspective. It is a Superclass
    of polyinterface.Node so all methods from polyinterface.Node are available to this
    class as well.

    Class Variables:
    self.nodes: Dictionary of nodes. Includes the Controller node. Keys are the node addresses
    self.name: String name of the node
    self.address: String Address of Node, must be less than 14 characters (ISY limitation)
    self.polyConfig: Full JSON config dictionary received from Polyglot for the controller Node
    self.added: Boolean Confirmed added to ISY as primary node
    self.config: Dictionary, this node's Config

    Class Methods (not including the Node methods):
    start(): Once the NodeServer config is received from Polyglot this method is automatically called.
    addNode(polyinterface.Node, update = False): Adds Node to self.nodes and polyglot/ISY. This is called
        for you on the controller itself. Update = True overwrites the existing Node data.
    updateNode(polyinterface.Node): Overwrites the existing node data here and on Polyglot.
    delNode(address): Deletes a Node from the self.nodes/polyglot and ISY. Address is the Node's Address
    longPoll(): Runs every longPoll seconds (set initially in the server.json or default 10 seconds)
    shortPoll(): Runs every shortPoll seconds (set initially in the server.json or default 30 seconds)
    query(): Queries and reports ALL drivers for ALL nodes to the ISY.
    getDriver('ST'): gets the current value from Polyglot for driver 'ST' returns a STRING, cast as needed
    runForever(): Easy way to run forever without maxing your CPU or doing some silly 'time.sleep' nonsense
                  this joins the underlying queue query thread and just waits for it to terminate
                  which never happens.
    """
    def __init__(self, polyglot):
        """
        Optional.
        Super runs all the parent class necessities. You do NOT have
        to override the __init__ method, but if you do, you MUST call super.
        """
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
        cts, channels = pollSensor(self)

        # for i, val in enumerate(cts):
        #         # LOGGER.debug('CT {} {} {} {}'.format(i, val.power, val.reactivePower, val.voltage))
        #         ctNodeAddr = "ct"+str(i+1)
        #         self.nodes[ctNodeAddr].updateValues(val.power, val.reactivePower, val.voltage)
        # for i, val in enumerate(channels):
        #         # LOGGER.debug('Channel {} {} {} {} {} {}'.format(i, val.power, val.imported, val.exported, val.reactivePower, val.voltage))
        #         channelNodeAddr = "channel"+str(i+1)
        #         self.nodes[channelNodeAddr].updateValues(val.power, val.reactivePower, val.voltage, val.imported, val.exported)
        LOGGER.debug('shortPoll - done checking Neurio status')

    def longPoll(self):
        """
        Optional.
        This runs every 30 seconds. You would probably update your nodes either here
        or shortPoll. No need to Super this method the parent version does nothing.
        The timer can be overriden in the server.json.
        """
        LOGGER.debug('longPoll')
        self.heartbeat()

    def query(self,command=None):
        """
        Optional.
        By default a query to the control node reports the FULL driver set for ALL
        nodes back to ISY. If you override this method you will need to Super or
        issue a reportDrivers() to each node manually.
        """
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
        """
        Example
        This is sent by Polyglot upon deletion of the NodeServer. If the process is
        co-resident and controlled by Polyglot, it will be terminiated within 5 seconds
        of receiving this message.
        """
        LOGGER.info('Oh God I\'m being deleted. Nooooooooooooooooooooooooooooooooooooooooo.')

    def stop(self):
        LOGGER.debug('NodeServer stopped.')

    def process_config(self, config):
        # this seems to get called twice for every change, why?
        # What does config represent?
        LOGGER.info("process_config: Enter config={}".format(config));
        check_params(self)
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
        default_numcts = 0
        default_numchannels = 0
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
                self.NumChannels = default_ip
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
                self.NumCTs = default_ip
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
        LOGGER.info('set_debug_level: command= {}'.format(command))
        LOGGER.info('set_debug_level: value  = {}'.format(command['value']))
        self.DebugLevel = int(command['value'])
        LOGGER.info('set_debug_level: logging.DEBUG   = {}'.format(logging.DEBUG))
        LOGGER.info('set_debug_level: logging.INFO    = {}'.format(logging.INFO))
        LOGGER.info('set_debug_level: logging.WARNING = {}'.format(logging.WARNING))
        LOGGER.setLevel(self.DebugLevel)
        self.setDriver('GV1', self.DebugLevel)

        # Make sure they are in the params
        self.addCustomParam({'DebugLevel': self.DebugLevel, 'NeurioIP': self.NeurioIP, 'NumChannels': self.NumChannels, 'NumCTs':self.NumCTs})

    """
    Optional.
    Since the controller is the parent node in ISY, it will actual show up as a node.
    So it needs to know the drivers and what id it will use. The drivers are
    the defaults in the parent Class, so you don't need them unless you want to add to
    them. The ST and GV1 variables are for reporting status through Polyglot to ISY,
    DO NOT remove them. UOM 2 is boolean.
    The id must match the nodeDef id="controller"
    In the nodedefs.xml
    """
    id = 'controller'
    commands = {
        'QUERY': query,
        'DISCOVER': discover,
        'UPDATE_PROFILE': update_profile,
        'REMOVE_NOTICES_ALL': remove_notices_all,
        'REMOVE_NOTICE_TEST': remove_notice_test,
        'SET_DEBUG_LEVEL': set_debug_level
    }
    drivers = [{'driver': 'ST',  'value': 1, 'uom': 2},
               {'driver': 'GV1', 'value': 0, 'uom': 25}]


class CTNode(polyinterface.Node):
    def __init__(self, controller, primary, address, name):
        super(CTNode, self).__init__(controller, primary, address, name)

    def start(self):
        # self.setDriver('ST', 1)
        # self.setDriver('GV0', 0)
        # self.setDriver('GV1', 0)
        # self.setDriver('GV2', 0)
        pass

    def updateValues(self, power, reactivePower, voltage, imported=0, exported=0):
        LOGGER.debug('Updating Values {} {} {}'.format(power, reactivePower, voltage))
        # self.setDriver('GV0', power)
        # self.setDriver('GV1', reactivePower)
        # self.setDriver('GV2', voltage)

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
        {'driver': 'ST', 'value': 0, 'uom': 2},
        {'driver': 'GV0', 'value': 1, 'uom': 73},
        {'driver': 'GV1', 'value': 2, 'uom': 0},
        {'driver': 'GV2', 'value': 3, 'uom': 72},
        {'driver': 'GV3', 'value': 3, 'uom': 33}
    ]
    id = 'ctnode'
    commands = {
        'DON': setOn, 'DOF': setOff
    }

class ChannelNode(polyinterface.Node):
    def __init__(self, controller, primary, address, name):
        super(ChannelNode, self).__init__(controller, primary, address, name)

    def start(self):
        # self.setDriver('ST', 1)
        # self.setDriver('GV0', 0)
        # self.setDriver('GV1', 0)
        # self.setDriver('GV2', 0)
        pass

    def updateValues(self, power, reactivePower, voltage, importedPower, exportedPower):
        LOGGER.debug('Updating Values {} {} {}'.format(power, reactivePower, voltage))
        # self.setDriver('GV0', power)
        # self.setDriver('GV1', reactivePower)
        # self.setDriver('GV2', voltage)
        # self.setDriver('GV3', importedPower)
        # self.setDriver('GV4', exportedPower)

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
        # {'driver': 'ST', 'value': 0, 'uom': 2},
        # {'driver': 'GV0', 'value': 1, 'uom': 30},
        # {'driver': 'GV1', 'value': 2, 'uom': 0},
        # {'driver': 'GV2', 'value': 3, 'uom': 72},
        # {'driver': 'GV3', 'value': 3, 'uom': 33},
        # {'driver': 'GV4', 'value': 3, 'uom': 33}
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