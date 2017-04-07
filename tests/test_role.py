import pytest

from testinfra.utils.ansible_runner import AnsibleRunner

testinfra_hosts = AnsibleRunner('.molecule/ansible_inventory').get_hosts('all')


@pytest.mark.parametrize('plugin_dir_name', [
    'google-java-format',
    'lombok-plugin',
    'Go'
])
def test_plugins_installed(Command, File, plugin_dir_name):
    plugins_dir_pattern = (
        '\\.(IdeaIC|IntelliJIdea)[0-9]+\\.[0-9]/config/plugins$')
    plugins_dir = Command.check_output('find %s | grep --color=never -E %s',
                                       '/home/test_usr',
                                       plugins_dir_pattern)
    plugin_dir = File(plugins_dir + '/' + plugin_dir_name)

    assert plugin_dir.exists
    assert plugin_dir.is_directory
    assert plugin_dir.user == 'test_usr'
    assert plugin_dir.group == 'test_usr'
    assert oct(plugin_dir.mode) == '0755'


def test_jar_plugin_installed(Command, File):
    config_dir_pattern = '\\.(IdeaIC|IntelliJIdea)[0-9]+\\.[0-9]/config$'
    config_home = Command.check_output('find %s | grep --color=never -E %s',
                                       '/home/test_usr',
                                       config_dir_pattern)

    plugins_dir = config_home + '/plugins/'

    plugin_path = Command.check_output('find %s | grep --color=never -E %s',
                                       plugins_dir,
                                       'save-actions_[0-9\\.]+.jar')

    plugin_file = File(plugin_path)

    assert plugin_file.exists
    assert plugin_file.is_file
    assert plugin_file.user == 'test_usr'
    assert plugin_file.group == 'test_usr'
    assert oct(plugin_file.mode) == '0664'
