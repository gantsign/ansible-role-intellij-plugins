import pytest

from testinfra.utils.ansible_runner import AnsibleRunner

testinfra_hosts = AnsibleRunner('.molecule/ansible_inventory').get_hosts('all')


@pytest.mark.parametrize('plugin_dir_path', [
    '/home/test_usr/.IdeaIC2016.2/config/plugins/google-java-format',
    '/home/test_usr/.IdeaIC2016.2/config/plugins/lombok-plugin',
    '/home/test_usr/.IdeaIC2016.2/config/plugins/Go'
])
def test_plugins_installed(File, plugin_dir_path):
    plugin_dir = File(plugin_dir_path)

    assert plugin_dir.exists
    assert plugin_dir.is_directory
    assert plugin_dir.user == 'test_usr'
    assert plugin_dir.group == 'test_usr'
    assert oct(plugin_dir.mode) == '0755'
