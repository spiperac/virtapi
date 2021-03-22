from setuptools import setup

setup(name='virtapi',
      version='1.3.5',
      description='VirtAPI is powerful libvirt/kvm wrapper with plugable API and bonus CLI tool out of the box.',
      url='http://github.com/spiperac/virtapi',
      author='Strahinja Piperac',
      author_email='spiperac@denkei.org',
      license='BSD',
      packages=['virtapi', 'virtapi.controller', 'virtapi.model', 'virtapi.tests'],
      include_package_data=True,
      scripts=['vatool'],
      install_requires=[
	'libvirt-python',
	'lxml==4.6.3',
	'paramiko>=2.2.4',
	'prettytable==0.7.2',
	'xmltodict==0.10.1',
	'pyyaml==3.12',
	'requests>=2.20.0',
	'tqdm==4.19.4',
      ],
      zip_safe=False)
