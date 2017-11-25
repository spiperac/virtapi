import sys
from shutil import copy2

if sys.version_info[0] < 3:
	import urllib2
else:
	import urllib.request
import os, json, socket
import logging
import requests

from tqdm import tqdm
from getpass import getpass
import paramiko
import errno
from os import chmod
from distutils.spawn import find_executable
from virtapi.settings import dir_path, SETTINGS

# crypto
from cryptography.hazmat.primitives import serialization as crypto_serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend as crypto_default_backend

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise

def download(url, path):
    filename = os.path.basename(url)
    response = requests.get(url, stream=True)
    chunkSize = 1024

    print("Fetching %s" % filename)
    with open("/tmp/%s" % (filename), 'wb') as f:
        pbar = tqdm( unit="B", total=int( response.headers['Content-Length'] ) )
        for chunk in response.iter_content(chunk_size=chunkSize): 
            if chunk: # filter out keep-alive new chunks
                pbar.update (len(chunk))
                f.write(chunk)

        return filename

def create_config():
   mkdir_p(SETTINGS['RESOURCESDIR'])
   mkdir_p('{}/keys'.format(SETTINGS['RESOURCESDIR']))
   copy2(SETTINGS['TEMPLATE_HOSTS_FILE'], SETTINGS['RESOURCESDIR'])
   copy2(SETTINGS['TEMPLATE_TEMPLATES_FILE'], SETTINGS['RESOURCESDIR'])
   copy2(SETTINGS['TEMPLATE_PLANS_FILE'], SETTINGS['RESOURCESDIR'])

def get_free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('localhost', 0))
    addr, port = s.getsockname()
    s.close()
    return port

def cloudinit(name):
    logging.info('Creating CLOUD INIT iso for a new domain.')

    isocmd = 'mkisofs'
    if find_executable('genisoimage') is not None:
        isocmd = 'genisoimage'
    os.system("{} --quiet -o /tmp/{} --volid cidata --joliet --rock {}/resources/cloudinit-config/user-data {}/resources/cloudinit-config/meta-data".format(isocmd, name, dir_path, dir_path))

def generate_ssh_key():
    logging.info('NOTICE! Generating a new private/public key combination, be AWARE!')

    key = rsa.generate_private_key(
    backend=crypto_default_backend(),
    public_exponent=65537,
    key_size=2048
    )
    private_key = key.private_bytes(
        crypto_serialization.Encoding.PEM,
        crypto_serialization.PrivateFormat.PKCS8,
        crypto_serialization.NoEncryption())
    public_key = key.public_key().public_bytes(
        crypto_serialization.Encoding.OpenSSH,
        crypto_serialization.PublicFormat.OpenSSH
    )
    
    with open("{}/keys/private.key".format(SETTINGS['RESOURCESDIR']), 'w') as content_file:
        content_file.write(private_key)
        chmod("{}/keys/private.key".format(SETTINGS['RESOURCESDIR']), 0600)
    with open("{}/keys/public.key".format(SETTINGS['RESOURCESDIR']), 'w') as content_file:
        content_file.write(public_key)
    return public_key

def check_public_key_exists(public_key, auth_keys):
    logging.info('Checking if public key exists on the host.')

    if public_key in str(auth_keys):
        logging.info('Public key already exists.')
        return True
    else:
        return False

def ssh_copy_id(key, server, username, password):
    logging.info('Adding a virtapi public key to the remote host hypervisor.')

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(server, username=username, password=password)

    client.exec_command('mkdir -p ~/.ssh/')
    stdin, stdout, ssh_stderr = client.exec_command("cat ~/.ssh/authorized_keys")
    auth_keys = stdout.readlines()
    if check_public_key_exists(key, auth_keys[0]):
        print("SSH Key exists. Connected.")
        return None
    client.exec_command('echo "%s" >> ~/.ssh/authorized_keys' % key)
    client.exec_command('chmod 644 ~/.ssh/authorized_keys')
    client.exec_command('chmod 700 ~/.ssh/')

def ssh_copy_id_new_key(key, server, username, password, target_key, key_pass=None):
    logging.info('Adding a virtapi public key to the remote host hypervisor (NEW KEY).')
    
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    new_key = target_key

    try:
        paramiko_key = paramiko.RSAKey.from_private_key_file(key)
        client.connect(server, username=username, pkey=paramiko_key)
    except (paramiko.ssh_exception.PasswordRequiredException) as e:
        print("[-] Your key is encrypted, password is needed:")
        if key_pass is None:
            kpass = getpass()
        else:
            kpass = key_pass
        paramiko_key = paramiko.RSAKey.from_private_key_file(key, password=kpass)
        client.connect(server, username=username, pkey=paramiko_key)

    client.exec_command('mkdir -p ~/.ssh/')
    stdin, stdout, ssh_stderr = client.exec_command("cat ~/.ssh/authorized_keys")
    auth_keys = stdout.readlines()
    if check_public_key_exists(new_key, auth_keys[0]):
        print("SSH Key exists. Connected.")
        return None
    client.exec_command('echo "{}" >> ~/.ssh/authorized_keys'.format(new_key))
    client.exec_command('chmod 644 ~/.ssh/authorized_keys')
    client.exec_command('chmod 700 ~/.ssh/')

def get_public_key():
    key = None
    with open('{}/keys/public.key'.format(SETTINGS['RESOURCESDIR'])) as k:
        key = k.readlines()
    if key == None:
        key = generate_ssh_key()
        return key
    return key[0]

def pretty_mem(val):
    val = int(val)
    if val > (10 * 1024 * 1024):
        return "%2.2f GB" % (val / (1024.0 * 1024.0))
    else:
        return "%2.0f MB" % (val / 1024.0)

def pretty_bytes(val):
    val = int(val)
    if val > (1024 * 1024 * 1024):
        return "%2.2f GB" % (val / (1024.0 * 1024.0 * 1024.0))
    else:
        return "%2.2f MB" % (val / (1024.0 * 1024.0))

