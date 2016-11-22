import pytest

from testinfra.utils.ansible_runner import AnsibleRunner

testinfra_hosts = AnsibleRunner('.molecule/ansible_inventory').get_hosts('all')


@pytest.mark.parametrize('plugin_dir_name', [
    'google-java-format',
    'lombok-plugin',
    'Go'
])
def test_plugins_installed(Command, File, plugin_dir_name):
    plugins_dir_pattern = '\\.IdeaIC[0-9]+\\.[0-9]/config/plugins$'
    plugins_dir = Command.check_output('find %s | grep --color=never -E %s',
                                       '/home/test_usr',
                                       plugins_dir_pattern)
    plugin_dir = File(plugins_dir + '/' + plugin_dir_name)

    assert plugin_dir.exists
    assert plugin_dir.is_directory
    assert plugin_dir.user == 'test_usr'
    assert plugin_dir.group == 'test_usr'
    assert oct(plugin_dir.mode) == '0755'
