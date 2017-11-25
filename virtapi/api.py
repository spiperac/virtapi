import libvirt, xmltodict, json, random, uuid
import logging

from libvirt import *
from virtapi.controller.host_ctrl import VirtHost
from virtapi.model.template import Templates
from virtapi.model.plan import Plans
from virtapi.model.host import Hosts
from virtapi import settings
from virtapi.utilities import create_config

class VirtAPI(object):
        def __init__(self, auth=None, memory_tresh=90):
            self.auth = auth
            self.max_memory_usage = memory_tresh
            self.host = None
            logging.basicConfig(filename='virtapi.log', level=logging.DEBUG)
            
            try:
                self.load_configurations()
            except Exception as e:
                create_config()
                self.load_configurations()

            # virthost setup
            self.host = self.Hosts.get_active()
            if self.host is None:
                self.VirtHost = VirtHost(host=None)
            self.VirtHost = VirtHost(host=self.host)

        def load_configurations(self):
            self.Templates = Templates()
            self.Plans = Plans()
            self.Hosts = Hosts()

