import yaml
import os.path
import paramiko
from paramiko.ssh_exception import *
from virtapi.settings import *
from virtapi.utilities import ssh_copy_id, ssh_copy_id_new_key,  generate_ssh_key, get_public_key

class Hosts(object):

    def __init__(self):
        self.hosts = None
        self.load_hosts()

    def load_hosts(self):
        '''
        Loads hosts from configuration hosts file.
        '''
        with open(SETTINGS['HOSTSFILE'], 'r') as stream:
            try:
                self.hosts = yaml.load(stream)
            except yaml.YAMLError as exc:
                print(exc)

    def add_host(self, host):
        self.hosts.append(host)
        self.save_hosts()

    def delete_host(self, host):
        if self.exists(host):
            self.hosts.remove(self.get_host_by_name(host))
            self.save_hosts()

    def ssh_exec(self, cmd):
        """
        Execute shell command on the host.
        """
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        host = self.get_active()
        if host['key'] == SETTINGS['DEFAULTKEYFILE']:
            client.connect(host['connection'], username=host['username'], key_filename=host['key'], allow_agent=False)
        else:
            key_password = raw_input('Enter SSH key password: ')
            client.connect(host['connection'], username=host['username'], key_filename=host['key'], password=key_password)
        stdin, stdout, stderr = client.exec_command(cmd)
        return stdout
    
    def add_key(self, key):
        if key == 'default':
            try:
                host = self.get_active()
                ssh_copy_id(get_public_key(), host['connection'], host['username'], host['password'])
            except (BadHostKeyException, AuthenticationException, SSHException, socket.error) as e:
                print('[-] Unable to login with given credentials, trying with standard id_rsa key location. [-]')
                host = self.get_active()
                ssh_copy_id_new_key('~/.ssh/id_rsa', host['connection'], host['username'], host['password'], get_public_key())

    def save_hosts(self):
        '''
        Save hosts from hosts object.
        '''
        with open(SETTINGS['HOSTSFILE'], 'w') as stream:
            try:
                yaml.dump(self.hosts, stream)
            except yaml.YAMLError as exc:
                print(exc)

    def get_hosts(self):
        return self.hosts

    def set_active(self, name, add_key=False, key_path=None):
        pub_key = get_public_key()

        for host in self.hosts:
            if host['name'] == name:
                host['active'] = True
                if host['protocol'] == 'ssh':
                    if add_key==True:
                        ssh_copy_id(pub_key, host['connection'], host['username'], host['password'])
            else:
                host['active'] = False
        self.save_hosts()
    
    def get_active(self):
        for host in self.hosts:
            if host['active']:
                return host

    def is_active(self, name):
        for host in self.hosts:
            if host['name'] == name:
                if host['active']:
                    return True
                else:
                    return False

    def get_host_by_name(self, name):
        exists = False
        for host in self.hosts:
            if host['name'] == name:
                return host
        return None

    def exists(self, name):
        exists = False
        for host in self.hosts:
            if host['name'] == name:
                exists = True
        return exists
