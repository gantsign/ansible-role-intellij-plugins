Ansible Role: IntelliJ Plugins
==============================

[![Tests](https://github.com/gantsign/ansible-role-intellij-plugins/workflows/Tests/badge.svg)](https://github.com/gantsign/ansible-role-intellij-plugins/actions?query=workflow%3ATests)
[![Ansible Galaxy](https://img.shields.io/badge/ansible--galaxy-gantsign.intellij--plugins-blue.svg)](https://galaxy.ansible.com/gantsign/intellij-plugins)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](https://raw.githubusercontent.com/gantsign/ansible-role-intellij-plugins/master/LICENSE)

Role to download and install
[IntelliJ IDEA](https://www.jetbrains.com/idea) plugins.

**Warning:** this role relies on internal IntelliJ IDEA APIs and should be
considered experimental at this time.

Requirements
------------

* Ansible >= 2.8

* Linux Distribution

    * Debian Family

        * Ubuntu

            * Xenial (16.04)
            * Bionic (18.04)

    * RedHat Family

        * CentOS

            * 7

    * Note: other versions are likely to work but have not been tested.

Role Variables
--------------

The following variables will change the behavior of this role (default values
are shown below):

```yaml
# Home directory of IntelliJ IDEA installation
intellij_plugins_intellij_home: '{{ ansible_local.intellij.general.home }}'

# Directory containing IntelliJ IDEA plugins (relative to user home)
intellij_plugins_intellij_user_plugins_dir: '{{ ansible_local.intellij.general.user_plugins_dir }}'

# Directory to store files downloaded for IntelliJ IDEA installation
intellij_plugins_download_dir: "{{ x_ansible_download_dir | default(ansible_env.HOME + '/.ansible/tmp/downloads') }}"

# URL for IntelliJ IDEA plugin manager web service
intellij_plugins_manager_url: 'https://plugins.jetbrains.com/pluginManager/'

# List of users to configure IntelliJ IDEA for
users: []
```

Users are configured as follows:

```yaml
users:
  - username: # Unix user name
    intellij_plugins:
      - # Plugin ID of plugin to install
```

Example Playbooks
-----------------

Minimal playbook:

```yaml
- hosts: servers
  roles:
    - role: gantsign.intellij-plugins
      users:
        - username: vagrant
          intellij_plugins:
            - CheckStyle-IDEA
```

Playbook with IntelliJ home and user dirname specified:

```yaml
- hosts: servers
  roles:
    - role: gantsign.intellij-plugins
      intellij_plugins_intellij_home: '/opt/idea/idea-community-2016.2.5'
      intellij_plugins_intellij_user_dirname: '.IdeaIC2016.2'
      users:
        - username: vagrant
          intellij_plugins:
            - CheckStyle-IDEA
```

More Roles From GantSign
------------------------

You can find more roles from GantSign on
[Ansible Galaxy](https://galaxy.ansible.com/gantsign).

Development & Testing
---------------------

This project uses [Molecule](http://molecule.readthedocs.io/) to aid in the
development and testing; the role is unit tested using
[Testinfra](http://testinfra.readthedocs.io/) and
[pytest](http://docs.pytest.org/).

To develop or test you'll need to have installed the following:

* Linux (e.g. [Ubuntu](http://www.ubuntu.com/))
* [Docker](https://www.docker.com/)
* [Python](https://www.python.org/) (including python-pip)
* [Ansible](https://www.ansible.com/)
* [Molecule](http://molecule.readthedocs.io/)

Because the above can be tricky to install, this project includes
[Molecule Wrapper](https://github.com/gantsign/molecule-wrapper). Molecule
Wrapper is a shell script that installs Molecule and it's dependencies (apart
from Linux) and then executes Molecule with the command you pass it.

To test this role using Molecule Wrapper run the following command from the
project root:

```bash
./moleculew test
```

Note: some of the dependencies need `sudo` permission to install.

License
-------

MIT

Author Information
------------------

John Freeman

GantSign Ltd.
Company No. 06109112 (registered in England)
