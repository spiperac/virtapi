"""
Host methods and calls
__author__ = Strahinja Piperac <spiperac@denkei.org>
"""

import xml.etree.ElementTree as ET
import xmltodict, json, random, uuid, requests
import libvirt, os, string, re
import shutil, logging
from virtapi import utilities

import subprocess
from time import sleep
from lxml import etree
from lxml.builder import E, ElementMaker

from virtapi.settings import *
from virtapi.model.template import Templates
from virtapi.model.host import Hosts
from virtapi.controller.domain_ctrl import VirtDomain


KB = 1024 * 1024
MB = 1024 * KB

class VirtHost(object):

    def __init__(self, host=None):
        self.conn = None
        self.host = 'localhost'
        self.debug = True
        self.host_manager = Hosts()
        self.template_manager = Templates()
        self.conn_status = False

        self.host = host
        if self.host is not None:
            self.host_url = self.host['connection']
            self.host_protocol = self.host['protocol']
            self.host_username = self.host['username']
            self.host_password = self.host['password']
            self.host_key = self.host['key']
            self.conn_status = True
        
    def request_cred(self, credentials, user_data):
        for credential in credentials:
            if credential[0] == libvirt.VIR_CRED_AUTHNAME:
                credential[4] = self.host_username
            elif credential[0] == libvirt.VIR_CRED_PASSPHRASE:
                credential[4] = self.host_password
        return 0

    def handler(self, stream, data, file_):
        return file_.read(data)

    def connect(self):
        """
        Returns None in case of failed connection.
        """
        conn = None
        if self.conn_status is False:
            return False
        

        if self.host_protocol == 'libssh2':
            self.auth = [[libvirt.VIR_CRED_AUTHNAME, libvirt.VIR_CRED_PASSPHRASE], self.request_cred, None]
            if self.host_url == None:
                conn = libvirt.open("qemu:///system")
            else:
                url = "{}://{}/?sshauth=password".format(VIRT_CONN_LIBSSH2, self.host_url)
                conn = libvirt.openAuth(url, self.auth, 0)

        elif self.host_protocol == 'ssh':
            if self.host_url == None:
                conn = libvirt.open("qemu:///system")
            else:
                url = "{}://{}@{}/system?socket=/var/run/libvirt/libvirt-sock&keyfile={}".format(VIRT_CONN_SSH, self.host_username, 
                                                                                                                    self.host_url, 
                                                                                                                    self.host_key)
                conn = libvirt.open(url)

        elif self.host_protocol == 'qemu':
            conn = libvirt.open("qemu:///system")

        if conn == None:
            logging.error('Connection to hypervisor failed!')
            return False
        else:
            logging.info('Connection succesfull.')
            self.conn = conn
            SETTINGS['connection'] = self.conn

    def get_conn(self):
        return self.conn

    def get_all_domains(self):
        """
        Returns a list of domain names, with UUIDString for each.
        """
        all_domains_list = self.conn.listAllDomains()
        response = []
        if all_domains_list == None:
            return False
        else:
            for domain in all_domains_list:
                    response.append( { "name": domain.name(), "uuid":  domain.UUIDString(), "state": domain.isActive() })
            return json.dumps(response)
    
    def get_all_domains_objects(self):
        """
        Returns a list of domain objects.
        """
        return self.conn.listAllDomains()

    def get_domain_object_by_uuid(self, domain_uuid):
        """
        Helper function for getting a domain object
        """
        domain = self.conn.lookupByUUIDString(domain_uuid)
        if domain is not None:
            return domain
        else:
            return None

    def get_domain_object_by_name(self, name):
        """
        Return domain object.
        """
        domain = self.conn.lookupByName(name)
        if domain is not None:
            return domain
        else:
            return None

    def get_host_info(self):
        """
        Returns some basic info about Host machine.
        """
        info = self.conn.getInfo()
        response = {}
        response['arch'] = info[0]
        response['ram'] = info[1]
        response['cpu_cores'] = info[2]
        return json.dumps(response)

    def get_host_memory_stats(self):
        """
        Returns stats for ram memory of the host.
        """
        memory = self.conn.getMemoryStats(0)
        return json.dumps(memory)

    def get_host_cpu_stats(self):
        """
        Returns stats for CPU cores.
        Format is { cpu_core_number: stats }
        """
        cores = self.conn.getInfo()[2]
        stats = []
        for core in range(1,cores):
                stats.append({core: self.conn.getCPUStats(core)})
        return json.dumps(stats)

    def get_host_creation_availability(self):
        memory = self.conn.getMemoryStats(0)
        all_memory = json.dumps(memory)
        free_memory = memory['free']
        total_memory = memory['total']
        tresh_hold = self.max_memory_usage
        available_status = False
            
        if free_memory > total_memory - ((total_memory / 100) * tresh_hold):
            available_status = True
        
        creation_status = {}
        creation_status['available'] = available_status
        creation_status['free_memory'] = free_memory
        return json.dumps(creation_status)

    def calculate_if_creation_is_posible(self, wanted_ram, wanted_cpu):
        memory = self.conn.getMemoryStats(0)
        all_memory = json.dumps(memory)
        free_memory = memory['free']
        total_memory = memory['total']
        tresh_hold = self.max_memory_usage
        available_status = False

        if free_memory - wanted_ram > total_memory - ((total_memory / 100 ) * tresh_hold):
            available_status = True

        return available_status

    def get_all_storage_pools_objects(self):
        """
        Returns storage pools objects.
        """
        return self.conn.listAllStoragePools(0)
    
    def get_pool_by_name(self, name):
        """
        Gets pool object based on the name parameter.
        """
        for pool in  self.get_all_storage_pools_objects():
            if pool.name() == name:
                return pool
    
    def get_pool_state(self, name):
        '''
        Returns pool state.
        '''
        pool = self.get_pool_by_name(name)
        return pool.isActive()

    def create_storage_pool(self, name, size=None):
        '''
        Creates a new storage pool.
        '''
        xmlDesc = """
        <pool type='dir'>
            <name>{}</name>
            <target>
                <path>/var/lib/libvirt/{}</path>
            </target>
        </pool>
        """.format(name, name)
        self.host_manager.ssh_exec('mkdir /var/lib/libvirt/{}'.format(name))
        pool = self.conn.storagePoolDefineXML(xmlDesc, 0)
        pool.create(0)
        pool.setAutostart(1)
        return pool

    def delete_storage_pool(self, name):
        """
        Starts given pool.
        """
        pool_deleted = False
        pool = self.get_pool_by_name(name)
        if pool.isActive():
            self.stop_storage_pool(name)

        if pool.undefine():
            pool_deleted=True
        return pool_deleted

    def start_storage_pool(self, name):
        """
        Starts given pool.
        """
        pool_started = False
        pool = self.get_pool_by_name(name)
        if pool.create(0):
            pool_started=True
        return pool_started

    def stop_storage_pool(self, name):
        """
        Stops given pool.
        """
        pool_stoped = False
        pool = self.get_pool_by_name(name)
        if pool.destroy():
            pool_stoped=True
        return pool_stoped
    
  
    def create_domain_from_template(self, template, params, cloudinit=True, start=True):
        
        # Checking if templates exists in template list file
        if self.template_manager.exists(template) is False:
            logging.info('Template selected does not exist.')
            print("Template selected does not exist")
            return None

        try:
            template_vm = self.conn.lookupByName(template)
        except Exception as e:
            logging.info('Template missing, creating one from template description.')
            logging.info(UPLOAD_DISCLAIMER)
            print(UPLOAD_DISCLAIMER)
            temp = self.template_manager.get_template_by_name(template)
            self.create_template(temp)
            template_vm = self.conn.lookupByName(template)

        template_xml = template_vm.XMLDesc(0)
        tree = ET.fromstring(template_xml)
        
        # check hw params
        if 'ram' in params:
            if params['ram'] == None:
                params['ram'] = SETTINGS['DEFAULT_RAM']
        else:
            params['ram'] = SETTINGS['DEFAULT_RAM']
        
        if 'vcpu' in params:
            if params['vcpu'] == None:
                params['vcpu'] = SETTINGS['DEFAULT_VCPU']
        else:
            params['vcpu'] = SETTINGS['DEFAULT_VCPU']

        if 'diskSize' in params:
            if params['diskSize'] == None:
                params['diskSize'] = SETTINGS['DEFAULT_DISKSIZE']
        else:
            params['diskSize'] = SETTINGS['DEFAULT_DISKSIZE']

        # uuid removal
        uuid = tree.getiterator('uuid')[0]
        tree.remove(uuid)

        # setting up a new name
        for vmname in tree.getiterator('name'):
            vmname.text = params['name']
       
        # setting up a ram memory

        for ram in tree.getiterator('memory'):
            if isinstance(float(params['ram']), float):
                ram.set('unit', 'MB')
                mem = str(int(float(params['ram']) * 1024))
                ram.text = mem
            else:
                ram.set('unit', 'GB')
                ram.text = str(params['ram'])

        for ram in tree.getiterator('currentMemory'):
            if isinstance(float(params['ram']), float):
                ram.set('unit', 'MB')
                mem = str(int(float(params['ram']) * 1024))
                ram.text = mem
            else:
                ram.set('unit', 'GB')
                ram.text = str(params['ram'])
          
        # setting up number of virtual cpus
        for vcpu in tree.getiterator('vcpu'):
            vcpu.text= str(params['vcpu'])
        
        # setting up cloud init
        cloudinit_disk = "{}-ds.iso".format(params['name'])
        if cloudinit:
            utilities.cloudinit(cloudinit_disk)
            cloudinit_image_path = self._uploadimage(cloudinit_disk,cloudinit_disk)
        
        cloudinit_volume = ET.Element("disk", type = 'file', device = 'disk')
        ET.SubElement(cloudinit_volume, "driver", name = 'qemu', type = 'raw')
        ET.SubElement(cloudinit_volume, "source", file = "{}".format(cloudinit_image_path))
        ET.SubElement(cloudinit_volume, "target", dev = 'vdb', bus = 'virtio')
        
        # disk/volume creation
        firstdisk = True
        full=False
        volumes = []
        volumes.append(cloudinit_image_path)

        for disk in tree.getiterator('disk'):
            if firstdisk or full:
                source = disk.find('source')
                oldpath = source.get('file')
                backingstore = disk.find('backingStore')
                backing = None
                if backingstore:
                    for b in backingstore.getiterator():
                        backingstoresource = b.find('source')
                        if backingstoresource is not None:
                            backing = backingstoresource.get('file')
                else:
                    backing = None
                old_name = os.path.basename(oldpath)
                newpath = oldpath.replace(old_name, params['name'])
                source.set('file', newpath)
                oldvolume = self.conn.storageVolLookupByPath(oldpath)
                oldinfo = oldvolume.info()
                oldvolumesize = (float(oldinfo[1]) / MB)
                newvolumesize = float(params['diskSize'])
                newvolumexml = self._xmlvolume(newpath, newvolumesize, backing=oldpath)
                pool = oldvolume.storagePoolLookupByVolume()
                pool.createXML(newvolumexml, 0)
                
                volumes.append(newpath)
                firstdisk = False
            else:
                devices = tree.getiterator('devices')[0]
                devices.remove(disk)

        for element in tree.getiterator('devices'):
            element.append(cloudinit_volume)

        for interface in tree.getiterator('interface'):
            mac = interface.find('mac')
            interface.remove(mac)
        newxml = ET.tostring(tree)
        try:
            self.conn.defineXML(newxml)
        except Exception as e:
            logging.error('Domain creation failed: {}.'.format(e))
            print("Creation failed, cleaning up resources.")
            for volume in volumes:
                vol = self.conn.storageVolLookupByPath(volume)
                vol.delete(0)
            return None

        vm = self.conn.lookupByName(params['name'])
        new_domain = VirtDomain(domain=vm)
        if start:
            vm.setAutostart(1)
            vm.create()
            while new_domain.get_ip(self.conn) == None:
                sleep(1)
        logging.info('Domain {} created!'.format(params['name']))
        return vm

    def clone_domain(self, template, params, start=False):

        try:
            template_vm = self.conn.lookupByName(template)
        except:
            temp = self.template_manager.get_template_by_name(template)
            self.create_template(temp)
            template_vm = self.conn.lookupByName(template)

        
        template_info = json.loads(VirtDomain(domain=template_vm).get_info(self.conn))
        template_xml = template_vm.XMLDesc(0)
        tree = ET.fromstring(template_xml)
        
        # disk/volume creation
        firstdisk = True
        full=False
        for disk in tree.getiterator('disk'):
            if firstdisk or full:
                source = disk.find('source')
                oldpath = source.get('file')
                backingstore = disk.find('backingStore')
                backing = None
                if backingstore:
                    for b in backingstore.getiterator():
                        backingstoresource = b.find('source')
                        if backingstoresource is not None:
                            backing = backingstoresource.get('file')
                else:
                    backing = None
                old_name = os.path.basename(oldpath)
                newpath = oldpath.replace(old_name, params['name'])
                source.set('file', newpath)
                oldvolume = self.conn.storageVolLookupByPath(oldpath)
                oldinfo = oldvolume.info()
                oldvolumesize = (float(oldinfo[1]) / MB)
                newvolumesize = oldvolumesize
                newvolumexml = self._xmlvolume(newpath, newvolumesize, backing=oldpath)
                pool = oldvolume.storagePoolLookupByVolume()
                pool.createXML(newvolumexml, 0)
                firstdisk = False
            else:
                devices = tree.getiterator('devices')[0]
                devices.remove(disk)

        # uuid removal
        uuid = tree.getiterator('uuid')[0]
        tree.remove(uuid)

        # setting up a new name
        for vmname in tree.getiterator('name'):
            vmname.text = params['name']
       
        # setting up a ram memory

        for ram in tree.getiterator('memory'):
            ram.set('unit', 'GB')
            ram.text = str(template_info['ram']/KB)
        
        # setting up number of virtual cpus
        for vcpu in tree.getiterator('vcpu'):
            vcpu.text= str(template_info['vcpu'])

        for interface in tree.getiterator('interface'):
            mac = interface.find('mac')
            interface.remove(mac)
        
        newxml = ET.tostring(tree)
        try:
            self.conn.defineXML(newxml)
        except Exception as e:
            logging.error('Cloning domain failed: {}.'.format(e))
            return None
        vm = self.conn.lookupByName(params['name'])
        new_domain = VirtDomain(domain=vm)
        if start:
            vm.setAutostart(1)
            vm.create()
            while new_domain.get_ip(self.conn) == None:
                sleep(1)
        logging.info('Domain {} cloned!'.format(params['name']))
        return vm



    def _uploadimage(self, name, newname, pool='default', origin='/tmp', suffix='.iso'):
        name = "%s" % (name)
        _pool = self.conn.storagePoolLookupByName(pool)
        poolxml = _pool.XMLDesc(0)
        root = ET.fromstring(poolxml)
        for element in root.getiterator('path'):
            poolpath = element.text
            break
        imagepath = "%s/%s" % (poolpath, newname)
        imagexml = self._xmlvolume(path=imagepath, size=0, diskformat='raw')
        _pool.createXML(imagexml, 0)
        imagevolume = self.conn.storageVolLookupByPath(imagepath)
        stream = self.conn.newStream(0)
        imagevolume.upload(stream, 0, 0)
        with open("%s/%s" % (origin, name)) as ori:
            stream.sendAll(self.handler, ori)
            stream.finish()
        return imagepath

    def fetch_image(self, url, newname, pool='default', origin='/tmp', suffix='.iso'):
        _pool = self.conn.storagePoolLookupByName(pool)
        poolxml = _pool.XMLDesc(0)
        root = ET.fromstring(poolxml)
        for element in root.getiterator('path'):
            poolpath = element.text
            break
        imagepath = "%s/%s" % (poolpath, newname)
        imagexml = self._xmlvolume(path=imagepath, size=0, diskformat='raw')
        _pool.createXML(imagexml, 0)
        imagevolume = self.conn.storageVolLookupByPath(imagepath)
        stream = self.conn.newStream(0)
        imagevolume.upload(stream, 0, 0)
        http_image = urlopen(url)
        print("Fetching image from stream.")
        #for chunk in http_image.iter_content(chunk_size=1024): 
        stream.sendAll(self.handler, http_image)
        stream.finish()
        return imagepath

    def _xmldisk(self, diskpath, diskdev, diskbus='virtio', diskformat='qcow2', shareable=False):
        if shareable:
            sharexml = '<shareable/>'
        else:
            sharexml = ''
        diskxml = """<disk type='file' device='disk'>
        <driver name='qemu' type='%s' cache='none'/>
        <source file='%s'/>
        <target bus='%s' dev='%s'/>
        %s
        </disk>""" % (diskformat, diskpath, diskbus, diskdev, sharexml)
        return diskxml

    def _xmlvolume(self, path, size, pooltype='file', backing=None, diskformat='qcow2'):
        size = int(size) * MB
        if int(size) == 0:
            size = 500 * 1024
        name = os.path.basename(path)
        if pooltype == 'block':
            volume = """<volume type='block'>
                        <name>%s</name>
                        <capacity unit="bytes">%d</capacity>
                        <target>
                        <path>%s</path>
                        <compat>1.1</compat>
                      </target>
                    </volume>""" % (name, size, path)
            return volume
        if backing is not None:
            backingstore = """
            <backingStore>
            <path>%s</path>
            <format type='%s'/>
            </backingStore>""" % (backing, diskformat)
        else:
            backingstore = "<backingStore/>"
        volume = """
        <volume type='file'>
        <name>%s</name>
        <capacity unit="bytes">%d</capacity>
        <target>
        <path>%s</path>
        <format type='%s'/>
        <permissions>
        <mode>0644</mode>
        </permissions>
        <compat>1.1</compat>
        </target>
        %s
        </volume>""" % (name, size, path, diskformat, backingstore)
        return volume

    def create_template(self, template):
        template_dl = self.template_manager.fetch_template(template['os'], template['version'])
        if template_dl is not None:
            name = str(template['os']) + str(template['version'])
            domain_iso = self._uploadimage(template_dl, name)

#        template_dl = self.fetch_image(template['iso'], template['name'])
#        domain_iso_path = SETTINGS['DEFAULTPOOLPATH'] + template['name']
 
        params = {}
        params['ram'] = 1
        params['vcpu'] = 1
        params['name'] = name
        self.create_domain(params, domain_iso)

    def create_domain(self, parms, domain_iso_path):
        """
        Creates a new domain based on XML description provided.
        """
        # TODO: Implement a XML for domain creating, based on images service which will provide XML configuration based on preconfigured XML's stored on server 
        xmldomain = """
        <domain type='kvm'>
        <name>{}</name>
        <memory unit='KiB'>{}</memory>
        <vcpu placement='static'>{}</vcpu>
        <os>                                                                      
            <type>hvm</type>                                                        
        </os>  
        <clock offset='utc'/>
        <features>                                                                
            <acpi/>                                                                 
            <apic/>                                                                 
            <pae/>                                                                  
        </features>   
        <on_poweroff>destroy</on_poweroff>
        <on_reboot>restart</on_reboot>
        <on_crash>destroy</on_crash>
        <devices>
                <disk type='file' device='disk'>
                    <source file='{}'/>
                    <driver name='qemu' type='qcow2'/>
                    <target dev='vda' bus='virtio'/>
                </disk>
                
                <interface type="network">
                    <source network="default" />
                    <model type='virtio'/>
                </interface>
                
                  <graphics type='vnc' port='-1' autoport='yes' listen='0.0.0.0'>       
                    <listen type='address' address='0.0.0.0'/>                          
                  </graphics>   
        </devices>
        </domain>
        """.format(parms['name'], int(parms['ram']) * KB, parms['vcpu'], domain_iso_path)

        domain = self.conn.defineXML(xmldomain)
        if domain == None:
            return None
        else:
            return domain


    def create_volume(pool, name): 
        # THIS IS JUST EXAMPLE
            stpVolXml = """
            <volume>
            <name>"""+name+""".img</name>
            <allocation>0</allocation>
            <capacity unit="G">10</capacity>
            <target>
                <path>/path/to/guest_images/"""+name+""".img</path>
                <permissions>
                <owner>107</owner>
                <group>107</group>
                <mode>0744</mode>
                <label>virt_image_t</label>
                </permissions>
            </target>
            </volume>"""

            stpVol = pool.createXML(stpVolXml, 0)   
            return stpVol


    def create_disk(self, name, size, pool=None, thin=True, template=None):
        diskformat = 'qcow2'
        if size < 1:
            print("Incorrect size.Leaving...")
            return
        if not thin:
            diskformat = 'raw'
        if pool is not None:
            pool = self.conn.storagePoolLookupByName(pool)
            poolxml = pool.XMLDesc(0)
            poolroot = ET.fromstring(poolxml)
            pooltype = poolroot.getiterator('pool')[0].get('type')
            for element in poolroot.getiterator('path'):
                poolpath = element.text
                break
        else:
            logging.error('Attempted creating a new disk on non existing pool, failed!')
            print("Pool not found. Leaving....")
            return
        if template is not None:
            volumes = {}
            for p in self.get_all_storage_pools_objects():
                poo = self.conn.storagePoolLookupByName(p)
                for vol in poo.listAllVolumes():
                    volumes[vol.name()] = vol.path()
            if template not in volumes and template not in volumes.values():
                print("Invalid template %s.Leaving..." % template)
            if template in volumes:
                template = volumes[template]
        pool.refresh(0)
        diskpath = "%s/%s" % (poolpath, name)
        if pooltype == 'logical':
            diskformat = 'raw'
        volxml = self._xmlvolume(path=diskpath, size=size, pooltype=pooltype,
                                 diskformat=diskformat, backing=template)
        pool.createXML(volxml, 0)
        return diskpath

    def add_disk(self, name, size, pool=None, thin=True, template=None, shareable=False, existing=None):
        diskformat = 'qcow2'
        diskbus = 'virtio'
        if size < 1:
            print("Incorrect size.Leaving...")
            return
        if not thin:
            diskformat = 'raw'
        try:
            vm = self.conn.lookupByName(name)
            xml = vm.XMLDesc(0)
            root = ET.fromstring(xml)
        except:
            print("[-] VM {} not found [-]".format(name))
            return
        currentdisk = 0
        for element in root.getiterator('disk'):
            disktype = element.get('device')
            if disktype == 'cdrom':
                continue
            currentdisk = currentdisk + 1
        diskindex = currentdisk + 1
        diskdev = "vd%s" % string.ascii_lowercase[currentdisk]
        if existing is None:
            storagename = "%s_%d.img" % (name, diskindex)
            diskpath = self.create_disk(name=storagename, size=size, pool=pool, thin=thin, template=template)
        else:
            diskpath = existing
        diskxml = self._xmldisk(diskpath=diskpath, diskdev=diskdev, diskbus=diskbus, diskformat=diskformat, shareable=shareable)
        vm.attachDevice(diskxml)
        vm = self.conn.lookupByName(name)
        vmxml = vm.XMLDesc(0)
        self.conn.defineXML(vmxml)
        logging.info('New disk added to the {} domain!'.format(name))
        print('[+] New disk of size {) added to the {} domain, in {} pool! [+]'.format(name, size, pool))

    def delete_disk(self, name, diskname):
        conn = self.conn
        try:
            vm = conn.lookupByName(name)
            xml = vm.XMLDesc(0)
            root = ET.fromstring(xml)
        except:
            print("VM %s not found" % name)
            return 1
        for element in root.getiterator('disk'):
            disktype = element.get('device')
            diskdev = element.find('target').get('dev')
            diskbus = element.find('target').get('bus')
            diskformat = element.find('driver').get('type')
            if disktype == 'cdrom':
                continue
            diskpath = element.find('source').get('file')
            volume = self.conn.storageVolLookupByPath(diskpath)
            if volume.name() == diskname or volume.path() == diskname:
                diskxml = self._xmldisk(diskpath=diskpath, diskdev=diskdev, diskbus=diskbus, diskformat=diskformat)
                vm.detachDevice(diskxml)
                volume.delete(0)
                vm = conn.lookupByName(name)
                vmxml = vm.XMLDesc(0)
                conn.defineXML(vmxml)
                return
        print("[-] Disk {} not found in {} domain [-]".format(diskname, name))

    def list_disks(self):
        volumes = {}
        for p in self.get_all_storage_pools_objects():
            poo = self.conn.storagePoolLookupByName(p)
            for volume in poo.listAllVolumes():
                volumes[volume.name()] = {'pool': poo.name(), 'path': volume.path()}
        return volumes

    def create_network(self, name, cidr, dhcp=True, nat=True):
        conn = self.conn
        networks = self.list_networks()
        cidrs = [network['cidr'] for network in networks.values()]
        if name in networks:
            return {'result': 'failure', 'reason': "Network %s already exists" % name}
        try:
            range = IpRange(cidr)
        except TypeError:
            return {'result': 'failure', 'reason': "Invalid Cidr %s" % cidr}
        if IPNetwork(cidr) in cidrs:
            return {'result': 'failure', 'reason': "Cidr %s already exists" % cidr}
        netmask = IPNetwork(cidr).netmask
        gateway = range[1]
        if dhcp:
            start = range[2]
            end = range[-2]
            dhcpxml = """<dhcp>
                    <range start='%s' end='%s'/>
                    </dhcp>""" % (start, end)
        else:
            dhcpxml = ''
        if nat:
            natxml = "<forward mode='nat'><nat><port start='1024' end='65535'/></nat></forward>"
        else:
            natxml = ''
        networkxml = """<network><name>%s</name>
                    %s
                    <domain name='%s'/>
                    <ip address='%s' netmask='%s'>
                    %s
                    </ip>
                    </network>""" % (name, natxml, name, gateway, netmask, dhcpxml)
        new_net = conn.networkDefineXML(networkxml)
        new_net.setAutostart(True)
        new_net.create()
        return {'result': 'success'}

    def add_nic(self, name, network):
        conn = self.conn
        networks = {}
        for interface in self.conn.listAllInterfaces():
            networks[interface.name()] = 'bridge'
        for net in self.conn.listAllNetworks():
            networks[net.name()] = 'network'
        try:
            vm = self.conn.lookupByName(name)
        except:
            print("VM %s not found" % name)
            return
        if network not in networks:
            print("Network %s not found" % network)
            return
        else:
            networktype = networks[network]
            source = "<source %s='%s'/>" % (networktype, network)
        nicxml = """<interface type='%s'>
                    %s
                    <model type='virtio'/>
                    </interface>""" % (networktype, source)
        vm.attachDevice(nicxml)
        vm = self.conn.lookupByName(name)
        vmxml = vm.XMLDesc(0)
        self.conn.defineXML(vmxml)

    def delete_nic(self, name, interface):
        conn = self.conn
        networks = {}
        nicnumber = 0
        for n in self.conn.listAllInterfaces():
            networks[n.name()] = 'bridge'
        for n in self.conn.listAllNetworks():
            networks[n.name()] = 'network'
        try:
            vm = self.conn.lookupByName(name)
            xml = vm.XMLDesc(0)
            root = ET.fromstring(xml)
        except:
            print("VM %s not found" % name)
            return 1
        for element in root.getiterator('interface'):
            device = "eth%s" % nicnumber
            if device == interface:
                mac = element.find('mac').get('address')
                networktype = element.get('type')
                if networktype == 'bridge':
                    network = element.find('source').get('bridge')
                    source = "<source %s='%s'/>" % (networktype, network)
                else:
                    network = element.find('source').get('network')
                    source = "<source %s='%s'/>" % (networktype, network)
                break
            else:
                nicnumber += 1
        nicxml = """<interface type='%s'>
                    <mac address='%s'/>
                    %s
                    <model type='virtio'/>
                    </interface>""" % (networktype, mac, source)
        print(nicxml)
        vm.detachDevice(nicxml)
        vm = conn.lookupByName(name)
        vmxml = vm.XMLDesc(0)
        conn.defineXML(vmxml)




    def report(self):
        conn = self.conn
        hostname = conn.getHostname()
        cpus = conn.getCPUMap()[0]
        memory = conn.getInfo()[1]
        print("Host:%s Cpu:%s Memory:%sMB\n" % (hostname, cpus, memory))
        for pool in self.get_all_storage_pools_objects():
            pool = conn.storagePoolLookupByName(pool.name())
            poolxml = pool.XMLDesc(0)
            root = ET.fromstring(poolxml)
            pooltype = root.getiterator('pool')[0].get('type')
            if pooltype == 'dir':
                poolpath = root.getiterator('path')[0].text
            else:
                poolpath = root.getiterator('device')[0].get('path')
            s = pool.info()
            used = "%.2f" % (float(s[2]) / MB)
            available = "%.2f" % (float(s[3]) / MB)
            # Type,Status, Total space in Gb, Available space in Gb
            used = float(used)
            available = float(available)
            print("Storage:%s Type:%s Path:%s Used space:%sGB Available space:%sGB" % (pool.name(), pooltype, poolpath, used, available))
        
        for interface in conn.listAllInterfaces():
            interfacename = interface.name()
            if interfacename == 'lo':
                continue
            print("Network:%s Type:bridged" % (interfacename))

        for network in conn.listAllNetworks():
            networkname = network.name()
            netxml = network.XMLDesc(0)
            cidr = 'N/A'
            root = ET.fromstring(netxml)
            ip = root.getiterator('ip')
            if ip:
                attributes = ip[0].attrib
                firstip = attributes.get('address')
                netmask = attributes.get('netmask')
                if netmask is None:
                    netmask = attributes.get('prefix')
                try:
                    ip = IPNetwork('%s/%s' % (firstip, netmask))
                    cidr = ip.cidr
                except:
                    cidr = "N/A"
            dhcp = root.getiterator('dhcp')
            if dhcp:
                dhcp = True
            else:
                dhcp = False
            print("Network:%s Type:routed Cidr:%s Dhcp:%s" % (networkname, cidr, dhcp))

    def delete_domain(self, name):
        """
        Deleting domain and all of it's parts ( disks, volumes, #TODO: networks).
        """
        try:
            domain = self.conn.lookupByName(name)
            virtual_domain = VirtDomain(domain)
        except:
            print("Domain not found")
            return 1
        # chekcing status
        if domain.isActive():
            domain.destroy()

        # cleaning snapshots if exists
        if domain.snapshotListNames():
            for snapshot in domain.snapshotListNames():
                snap = domain.snapshotLookupByName(snapshot)
                snap.delete()
        
        # Deleting disks and volumes
        domain_xml = domain.XMLDesc(0)
        root = ET.fromstring(domain_xml)
        disks = virtual_domain.get_disks()

        for disk in disks:
            disk.delete(0)

        domain.undefine()
        logging.info('Domain {} deleted!'.format(name))

    def randomMAC(self):
        mac = [ 0x00, 0x16, 0x3e,
        random.randint(0x00, 0x7f),
        random.randint(0x00, 0xff),
        random.randint(0x00, 0xff) ]
        return str(':'.join(map(lambda x: "%02x" % x, mac)))


