import yaml
import os 
from os.path import expanduser

dir_path = os.path.dirname(os.path.realpath(__file__))
user_home_dir = expanduser("~")
# Global settings

SETTINGS = {}

SETTINGS['RESOURCESDIR'] = '{}/.vatool'.format(user_home_dir)
SETTINGS['DEFAULTPOOL'] = 'default'
SETTINGS['DEFAULTPOOLPATH']='/var/lib/libvirt/images/'
SETTINGS['TEMPLATESPATH'] = '/var/lib/libvirt/images/'
SETTINGS['TEMPLATESFILE'] = '{}/templates.yml'.format(SETTINGS['RESOURCESDIR'])
SETTINGS['PLANSFILE'] = '{}/plans.yml'.format(SETTINGS['RESOURCESDIR'])
SETTINGS['HOSTSFILE'] = '{}/hosts.yml'.format(SETTINGS['RESOURCESDIR'])
SETTINGS['DEFAULTKEYFILE'] = '{}/keys/private.key'.format(SETTINGS['RESOURCESDIR'])

# TEMPLATE CONFIG FILES

SETTINGS['TEMPLATE_HOSTS_FILE'] = '{}/resources/config/hosts.yml'.format(dir_path)
SETTINGS['TEMPLATE_TEMPLATES_FILE'] = '{}/resources/config/templates.yml'.format(dir_path)
SETTINGS['TEMPLATE_PLANS_FILE'] = '{}/resources/config/plans.yml'.format(dir_path)

# HW DEFAULTS

SETTINGS['DEFAULT_RAM'] = 1
SETTINGS['DEFAULT_VCPU'] = 1
SETTINGS['DEFAULT_DISKSIZE'] = 10

# VIRT Defs

VIRT_CONN_SSH = 'qemu+ssh'
VIRT_CONN_LIBSSH2 = 'qemu+libssh2'
VIRT_CONN_TCP = 'qemu+tcp'


# Misc

LOGO = """
 __      __  _______          _ 
 \ \    / /\|__   __|        | |
  \ \  / /  \  | | ___   ___ | |
   \ \/ / /\ \ | |/ _ \ / _ \| |
    \  / ____ \| | (_) | (_) | |
     \/_/    \_\_|\___/ \___/|_|
                                
"""

UPLOAD_DISCLAIMER = """
Scince this is the first time you are using this template, download into KVM host is needed so VATool can create a template VM.
Please be patient, scince this can take a while depending on your upload/download speed. There are plans to improve his in future,
with remote downloader agent service.
"""
