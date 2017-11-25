"""
Domain methods and calls
__author__ = Strahinja Piperac <spiperac@denkei.org>
"""
from xml.etree import ElementTree
import xml.etree.ElementTree as ET
import xmltodict, json, random, uuid
from virtapi import settings

class VirtDomain(object):

    def __init__(self, domain=None, name=None):
        if domain is not None:
            self.domain = domain
        
        if name is not None:
            self.domain = None #TODO implement get by name

        self.xml = ElementTree.fromstring(self.domain.XMLDesc(0))
        self.conn = settings.SETTINGS['connection']

    def get_uuid(self):
        response = {}

        if self.domain == None:
            return False
        else:
            response['uuid'] = self.domain.UUIDString()
            return json.dumps(response)

    def get_info(self, conn):
        """
        Returns basic info of the domain like ram, cpu, name and uuid.
        """
        response = {}

        if self.domain == None:
            return False
        else:
            response['name'] = self.domain.name()
            response['uuid'] = self.domain.UUIDString()
            response['state'] = self.domain.isActive()
            response['ram'] = self.domain.maxMemory()
            response['vcpu'] = self.domain.info()[3]
            response['ip'] = self.get_ip(conn)
            return json.dumps(response)

    def get_disks(self):
        """
        Return a list of all the Disks attached to this VM
        The disks are returned in a sham.storage.volumes.Volume
        object
        """
        disks = [disk for disk in self.xml.iter('disk')]
        disk_objs = []
        for disk in disks:
            source = disk.find('source')
            if source is None:
                continue
            path = source.attrib['file']
            diskobj = self.conn.storageVolLookupByPath(path)
            disk_objs.append(diskobj)
        return disk_objs
    
    def get_domain_network_interfaces(self):
        """
        Returns a list of all network interfaces attached to the domain.
        """
        #network_interfaces = self.domain.
        pass

    def start_domain(self):
        """
        Poweron( Start) given domain object.
        """
        if self.domain == None:
            return None
        else:
            return self.domain.create()

    def stop_domain(self):
        """
        Poweroff given domain object.
        """
        if self.domain == None:
            return None
        else:
            return self.domain.shutdown()
    
    def force_stop(self, name):
        """
        Force shutdowns domain.
        """
        if self.domain == None:
            return None
        else:
            return self.domain.destroy()

    def suspend(self, name):
        self.domain.suspend()

    def resume(self, name):
        self.domain.resume()

    def reboot_domain(self):
        """
        Restarts a given domain object.
        """
        if self.domain == None:
            return None
        else:
            return self.domain.reboot()

    def delete_domain(self):
        """
        Method deletes domain, permanent. Be careful, and think twice, before using this method.
        """
        if self.domain == None:
            return None
        else:
            self.domain.undefine()

    def set_autostart_domain(self, state):
        """
        Changes autostart to on/off. This method accept boolean value( True - on, False -off)
        """
        if self.domain != None:
            self.domain.setAutostart(int(state))

    def delete_disk(self):
        disks = self.get_disk_device()
        for disk in disks:
            vol = self.get_volume_by_path(disk.get('path'))
            vol.delete(0)

    
    def randomMAC(self):
        mac = [ 0x00, 0x16, 0x3e,
        random.randint(0x00, 0x7f),
        random.randint(0x00, 0xff),
        random.randint(0x00, 0xff) ]
        return str(':'.join(map(lambda x: "%02x" % x, mac)))

    def get_ip(self, conn):
        leases = {}
        if conn == None:
            pass

        for network in conn.listAllNetworks():
            for lease in network.DHCPLeases():
                ip = lease['ipaddr']
                mac = lease['mac']
                leases[mac] = ip
        try:
            vm = self.domain
            xml = vm.XMLDesc(0)
            root = ET.fromstring(xml)
        except:
            return None
        nic = root.getiterator('interface')[0]
        mac = nic.find('mac').get('address')
        if vm.isActive() and mac in leases:
            return leases[mac]
        else:
            return None

    def get_volumes(self, conn, iso=False):
        isos = []
        templates = []
        if conn == None:
            pass

        for storage in conn.listStoragePools():
            storage = conn.storagePoolLookupByName(storage)
            storage.refresh(0)
            storagexml = storage.XMLDesc(0)
            root = ET.fromstring(storagexml)
            for element in root.getiterator('path'):
                storagepath = element.text
                break
            for volume in storage.listVolumes():
                if volume.endswith('iso'):
                    isos.append("%s/%s" % (storagepath, volume))

        if iso:
            return isos

