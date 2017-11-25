"""
Network methods and calls
__author__ = Strahinja Piperac <spiperac@denkei.org>
"""

import xmltodict, json, random, uuid

def get_network_object(self, network_uuid):
    """
    Helper function for getting a network object by UUID string.
    """
    network = self.conn.networkLookupByUUIDString(network_uuid)
    if network != None:
        return network
    else:
        return None

def get_all_networks(self):
    """
    Returns list of defined networks on KVM host.
    """
    networks = self.conn.listAllNetworks()
    response = []
    if networks != None:
        for network in networks:
                response.append({"name": network.name(), "uuid": network.UUIDString()})
        return json.dumps(response)

def set_autostart_network(self, network_uuid, state):
    """
    Chaning autostart value for the selected network. Values: True - On, False - Off)
    """
    network = self.get_network_object(network_uuid)
    if network != None:
        network.setAutostart(int(state))
    else:
        return False
