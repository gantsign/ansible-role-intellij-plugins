import pytest
import os

import testinfra.utils.ansible_runner

testinfra_hosts = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ['MOLECULE_INVENTORY_FILE']).get_hosts('all')


@pytest.mark.parametrize('plugin_dir_name', [
    'google-java-format',
    'lombok-plugin'
])
def test_plugins_installed(host, plugin_dir_name):
    plugins_dir_pattern = (
        '\\.(IdeaIC|IntelliJIdea)[0-9]+\\.[0-9]/config/plugins$')
    plugins_dir = host.check_output('find %s | grep --color=never -E %s',
                                    '/home/test_usr',
                                    plugins_dir_pattern)
    plugin_dir = host.file(plugins_dir + '/' + plugin_dir_name)

    assert plugin_dir.exists
    assert plugin_dir.is_directory
    assert plugin_dir.user == 'test_usr'
    assert plugin_dir.group == 'test_usr'
    assert plugin_dir.mode == 0o755


def test_jar_plugin_installed(host):
    config_dir_pattern = '\\.(IdeaIC|IntelliJIdea)[0-9]+\\.[0-9]/config$'
    config_home = host.check_output('find %s | grep --color=never -E %s',
                                    '/home/test_usr',
                                    config_dir_pattern)

    plugins_dir = config_home + '/plugins/'

    sa_plugin_pattern = 'intellij-plugin-save-actions-v?[0-9\\.\\+]+.jar'
    plugin_path = host.check_output('find %s | grep --color=never -E %s',
                                    plugins_dir,
                                    sa_plugin_pattern)

    plugin_file = host.file(plugin_path)

    assert plugin_file.exists
    assert plugin_file.is_file
    assert plugin_file.user == 'test_usr'
    assert plugin_file.group == 'test_usr'
    assert plugin_file.mode == 0o664
