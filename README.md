VirtAPI [![Build Status](https://travis-ci.org/spiperac/virtapi.svg?branch=master)](https://travis-ci.org/spiperac/virtapi)
-----


VirtAPI is awrapper and CLI tool(vatool) for automation of KVM/Libvirt machines.
It can be used to create/delete/{start,stop,restart}/clone/migrate virtual machines(domains) on local/remote KVM servers.
* It's also working in nested envinroments, you can try it by creating VM inside digitalocean droplet for example."

Instalation
-----

You will need few more dependencies before installing actual virtapi package.
I'll give an example for Ubuntu here:

  sudo apt install libvirt-bin libvirt-dev openssl libssl-dev -y

After dependencies are satistfied, you can then install package from this reposutiry by running:

  sudo python setup.py install

Or by installing it directly from PyPI ( for stable versions go with this):

  sudo pip install virtapi


Features & TODO
-----

Futures:
- Connect to the KVM local or remote host ( get host data/info/metrics)
- Create new domain(virtual machine) from predefined templates in QCOW2 format or image, and based on selected plan size.
- Delete domain and all of it resources ( disks attached etc...)
- Clone/Migrate existing domain and it specifications.
- Add/Delete templates for domain(VM) creation.
- Add/Delete Plans for domain(vm), think of them as a digitalocean, aws plans. For example small plan is: 512MB for ram, 1 VCPU, and 15GB hdd drive space.
- Manage additional disks and drives. You can "hot plug" them too.

You can use it as a CLI tool (vatool binary), but also you can plug it in your application as an API.
After installing it as a package you will have vatool binary in your path.

TODO:
- Add more options for managing KVM/Libvirt Host.
- Add ansible for provision of the hosts.
- Better error handling.
- Better logging.
- In the future cover few more cloud APIs.


Demo
-----
[![asciicast](https://asciinema.org/a/bBVzd6jvwVKTj8efqg6v83VEq.png)](https://asciinema.org/a/bBVzd6jvwVKTj8efqg6v83VEq)


Development
-----

There are always things to be fixed or added, or simply forgoten things. So any suggestions/pull requests/issues are welcome, since i'm developing this
in my free time.

Requirements for development are in requirements.txt file inside package.


Contact
-----

You can find me on twitter @0xbadarg
or you can hit me an email at spiperac@denkei.org
