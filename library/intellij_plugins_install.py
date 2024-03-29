#!/usr/bin/python

# Make coding more python3-ish
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import hashlib
import json
import os
import pwd
import re
import shutil
import socket
import tempfile
import time
import traceback
import zipfile
from distutils.version import LooseVersion

import ansible.module_utils.six.moves.urllib.error as urllib_error
from ansible.module_utils._text import to_native
from ansible.module_utils.basic import AnsibleModule, get_distribution
from ansible.module_utils.six import PY3
from ansible.module_utils.urls import ConnectionError, NoSSLError, open_url

try:
    import httplib
except ImportError:
    # Python 3
    import http.client as httplib

try:
    from lxml import etree
    HAS_LXML = True
except ImportError:
    HAS_LXML = False

try:
    from ansible.module_utils.six.moves.urllib.parse import urlencode, urljoin
    HAS_URLPARSE = True
except BaseException:
    HAS_URLPARSE = False


def mkdirs(module, path, owner, mode):
    stack = []
    current_path = path
    owner_details = pwd.getpwnam(owner)

    while current_path != '' and not os.path.exists(current_path):
        stack.insert(0, os.path.basename(current_path))

        current_path = os.path.dirname(current_path)

    for dirname in stack:
        if not os.path.isdir(current_path):
            module.fail_json(
                msg='Unable to create directory "%s": invalid path %s' % (
                    path, current_path))

        current_path = os.path.join(current_path, dirname)
        os.mkdir(current_path, mode)
        os.chown(current_path, owner_details.pw_uid, owner_details.pw_gid)


def get_root_dirname_from_zip(module, zipfile_path):
    if not os.path.isfile(zipfile_path):
        module.fail_json(msg='File not found: %s' % zipfile_path)

    with zipfile.ZipFile(zipfile_path, 'r') as z:
        files = z.namelist()

    if len(files) == 0:
        module.fail_json(msg='Plugin is empty: %s' % zipfile_path)

    return files[0].split('/')[0]


def extract_zip(module, output_dir, zipfile_path, owner):
    if not os.path.isfile(zipfile_path):
        module.fail_json(msg='File not found: %s' % zipfile_path)

    owner_details = pwd.getpwnam(owner)
    uid = owner_details.pw_uid
    gid = owner_details.pw_gid

    with zipfile.ZipFile(zipfile_path, 'r') as z:
        z.extractall(output_dir)
        files = z.namelist()

    for file_entry in files:
        absolute_file = os.path.join(output_dir, file_entry)
        while not os.path.samefile(absolute_file, output_dir):
            os.chown(absolute_file, uid, gid)
            absolute_file = os.path.normpath(
                os.path.join(absolute_file, os.pardir))


def fetch_url(module, url, method=None, timeout=10, follow_redirects=True):

    if not HAS_URLPARSE:
        module.fail_json(msg='urlparse is not installed')

    # ensure we use proper tempdir
    old_tempdir = tempfile.tempdir
    tempfile.tempdir = module.tmpdir

    r = None
    info = dict(url=url, status=-1)
    try:
        r = open_url(url,
                     method=method,
                     timeout=timeout,
                     follow_redirects=follow_redirects)
        # Lowercase keys, to conform to py2 behavior, so that py3 and py2 are
        # predictable
        info.update(dict((k.lower(), v) for k, v in r.info().items()))

        # Don't be lossy, append header values for duplicate headers
        # In Py2 there is nothing that needs done, py2 does this for us
        if PY3:
            temp_headers = {}
            for name, value in r.headers.items():
                # The same as above, lower case keys to match py2 behavior, and
                # create more consistent results
                name = name.lower()
                if name in temp_headers:
                    temp_headers[name] = ', '.join((temp_headers[name], value))
                else:
                    temp_headers[name] = value
            info.update(temp_headers)

        # finally update the result with a message about the fetch
        info.update(
            dict(msg='OK (%s bytes)' %
                 r.headers.get('Content-Length', 'unknown'),
                 url=r.geturl(),
                 status=r.code))
    except NoSSLError as e:
        distribution = get_distribution()
        if distribution is not None and distribution.lower() == 'redhat':
            module.fail_json(
                msg='%s. You can also install python-ssl from EPEL' %
                to_native(e), **info)
        else:
            module.fail_json(msg='%s' % to_native(e), **info)
    except (ConnectionError, ValueError) as e:
        module.fail_json(msg=to_native(e), **info)
    except urllib_error.HTTPError as e:
        try:
            body = e.read()
        except AttributeError:
            body = ''

        # Try to add exception info to the output but don't fail if we can't
        try:
            # Lowercase keys, to conform to py2 behavior, so that py3 and py2
            # are predictable
            info.update(dict((k.lower(), v) for k, v in e.info().items()))
        except Exception:
            pass

        info.update({'msg': to_native(e), 'body': body, 'status': e.code})

    except urllib_error.URLError as e:
        code = int(getattr(e, 'code', -1))
        info.update(dict(msg='Request failed: %s' % to_native(e), status=code))
    except socket.error as e:
        info.update(
            dict(
                msg='Connection failure: %s' %
                to_native(e),
                status=-
                1))
    except httplib.BadStatusLine as e:
        info.update(
            dict(
                msg=('Connection failure: connection was closed before a valid'
                     ' response was received: %s') %
                to_native(
                    e.line),
                status=-
                1))
    except Exception as e:
        info.update(dict(msg='An unknown error occurred: %s' % to_native(e),
                         status=-1),
                    exception=traceback.format_exc())
    finally:
        tempfile.tempdir = old_tempdir

    return r, info


def get_build_number_from_xml(module, intellij_home, xml):
    info_doc = etree.parse(xml)
    build = info_doc.find('./build/[@number]')
    if build is None:
        build = info_doc.find(
            './{http://jetbrains.org/intellij/schema/application-info}build/'
            '[@number]'
        )
    if build is None:
        module.fail_json(
            msg=('Unable to determine IntelliJ version from path: %s '
                 '(unsupported schema - missing build element)') %
            intellij_home)

    build_number = build.get('number')
    if build_number is None:
        module.fail_json(
            msg=('Unable to determine IntelliJ version from path: %s '
                 '(unsupported schema - missing build number value)') %
            intellij_home)

    return build_number


def get_build_number_from_jar(module, intellij_home):
    resources_jar = os.path.join(intellij_home, 'lib', 'resources.jar')

    if not os.path.isfile(resources_jar):
        return None

    with zipfile.ZipFile(resources_jar, 'r') as resource_zip:
        try:
            with resource_zip.open('idea/IdeaApplicationInfo.xml') as xml:
                return get_build_number_from_xml(module, intellij_home, xml)
        except KeyError:
            try:
                with resource_zip.open('idea/ApplicationInfo.xml') as xml:
                    return get_build_number_from_xml(
                        module, intellij_home, xml)
            except KeyError:
                module.fail_json(
                    msg=('Unable to determine IntelliJ version from path: %s '
                         '(XML info file not found in "lib/resources.jar")') %
                    intellij_home)


def get_build_number_from_json(module, intellij_home):
    product_info_path = os.path.join(intellij_home, 'product-info.json')

    if not os.path.isfile(product_info_path):
        module.fail_json(
            msg=('Unable to determine IntelliJ version from path: %s '
                 '("product-info.json" not found)') %
            intellij_home)

    with open(product_info_path) as product_info_file:
        product_info = json.load(product_info_file)
        return product_info['buildNumber']


def get_build_number(module, intellij_home):
    return get_build_number_from_jar(
        module, intellij_home) or get_build_number_from_json(
        module, intellij_home)


def get_plugin_info(module, plugin_manager_url, intellij_home, plugin_id):

    build_number = get_build_number(module, intellij_home)

    params = {'action': 'download', 'build': build_number, 'id': plugin_id}

    query_params = urlencode(params)

    url = '%s?%s' % (plugin_manager_url, query_params)
    for _ in range(0, 3):
        resp, info = fetch_url(
            module, url, method='HEAD', timeout=3, follow_redirects=False)
        if resp is not None:
            resp.close()
        status_code = info['status']
        if status_code == 404:
            module.fail_json(
                msg='Unable to find plugin "%s" for build "%s"' %
                (plugin_id, build_number))
        if status_code > -1 and status_code < 400:
            break
        # 3 retries 5 seconds appart
        time.sleep(5)

    if status_code == -1 or status_code >= 400:
        module.fail_json(
            msg='Error querying url "%s": %s' %
            (url, info['msg']))

    location = info.get('location')
    if location is None:
        location = info.get('Location')
    if location is None:
        module.fail_json(
            msg='Unsupported HTTP response for: %s (status=%s)' %
            (url, status_code))

    if location.startswith('http'):
        plugin_url = location
    else:
        plugin_url = urljoin(plugin_manager_url, location)

    jar_pattern = re.compile(r'/(?P<file_name>[^/]+\.jar)(?:\?.*)$')
    jar_matcher = jar_pattern.search(plugin_url)

    if jar_matcher:
        file_name = jar_matcher.group('file_name')
    else:
        versioned_pattern = re.compile(
            r'(?P<plugin_id>[0-9]+)/(?P<update_id>[0-9]+)/'
            r'(?P<file_name>[^/]+)(?:\?.*)$'
        )

        versioned_matcher = versioned_pattern.search(plugin_url)
        if versioned_matcher:
            file_name = '%s-%s-%s' % (versioned_matcher.group('plugin_id'),
                                      versioned_matcher.group('update_id'),
                                      versioned_matcher.group('file_name'))
        else:
            hash_object = hashlib.sha256(plugin_url)
            file_name = '%s-%s.zip' % (plugin_id, hash_object.hexdigest())

    return plugin_url, file_name


def download_plugin(module, plugin_url, file_name, download_cache):
    if not os.path.isdir(download_cache):
        os.makedirs(download_cache, 0o775)

    download_path = os.path.join(download_cache, file_name)

    if os.path.isfile(download_path):
        return download_path

    for _ in range(0, 3):
        resp, info = fetch_url(module,
                               plugin_url,
                               method='GET',
                               timeout=20,
                               follow_redirects=True)
        status_code = info['status']

        if status_code >= 200 and status_code < 300:
            tmp_dest = getattr(module, 'tmpdir', None)

            fd, b_tempname = tempfile.mkstemp(dir=tmp_dest)

            f = os.fdopen(fd, 'wb')
            try:
                shutil.copyfileobj(resp, f)
            except Exception as e:
                os.remove(b_tempname)
                resp.close()
                module.fail_json(
                    msg='Failed to create temporary content file: %s' %
                    to_native(e))
            f.close()
            resp.close()

            module.atomic_move(to_native(b_tempname), download_path)

            return download_path

        if resp is not None:
            resp.close()

    module.fail_json(msg='Error downloading url "%s": %s' % (plugin_url,
                                                             info['msg']))


def install_plugin(module, plugin_manager_url, intellij_home, plugins_dir,
                   username, plugin_id, download_cache):
    plugin_url, file_name = get_plugin_info(module, plugin_manager_url,
                                            intellij_home, plugin_id)

    plugin_path = download_plugin(
        module, plugin_url, file_name, download_cache)

    if not module.check_mode:
        mkdirs(module, plugins_dir, username, 0o775)

    owner_details = pwd.getpwnam(username)
    if plugin_path.endswith('.jar'):
        dest_path = os.path.join(plugins_dir, os.path.basename(plugin_path))

        if os.path.exists(dest_path):
            return False

        if not module.check_mode:
            shutil.copy(plugin_path, dest_path)
            os.chown(dest_path, owner_details.pw_uid, owner_details.pw_gid)
            os.chmod(dest_path, 0o664)
        return True
    else:
        root_dirname = get_root_dirname_from_zip(module, plugin_path)
        plugin_dir = os.path.join(plugins_dir, root_dirname)

        if os.path.exists(plugin_dir):
            return False

        if not module.check_mode:
            extract_zip(module, plugins_dir, plugin_path, username)
        return True


def run_module():

    module_args = dict(
        plugin_manager_url=dict(type='str', required=True),
        intellij_home=dict(type='path', required=True),
        intellij_user_plugins_dir=dict(type='path', required=True),
        username=dict(type='str', required=True),
        plugin_id=dict(type='str', required=True),
        download_cache=dict(type='path', required=True))

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    plugin_manager_url = module.params['plugin_manager_url']
    intellij_home = os.path.expanduser(module.params['intellij_home'])
    username = module.params['username']
    intellij_user_plugins_dir = os.path.expanduser(os.path.join(
        '~' + username, module.params['intellij_user_plugins_dir']))
    plugin_id = module.params['plugin_id']
    download_cache = os.path.expanduser(module.params['download_cache'])

    # Check if we have lxml 2.3.0 or newer installed
    if not HAS_LXML:
        module.fail_json(
            msg='The xml ansible module requires the lxml python library '
            'installed on the managed machine')
    elif LooseVersion('.'.join(
            to_native(f) for f in etree.LXML_VERSION)) < LooseVersion('2.3.0'):
        module.fail_json(
            msg='The xml ansible module requires lxml 2.3.0 or newer '
            'installed on the managed machine')
    elif LooseVersion('.'.join(
            to_native(f) for f in etree.LXML_VERSION)) < LooseVersion('3.0.0'):
        module.warn(
            'Using lxml version lower than 3.0.0 does not guarantee '
            'predictable element attribute order.'
        )

    changed = install_plugin(module, plugin_manager_url, intellij_home,
                             intellij_user_plugins_dir, username, plugin_id,
                             download_cache)

    if changed:
        msg = 'Plugin %s has been installed' % username
    else:
        msg = 'Plugin %s was already installed' % username

    module.exit_json(changed=changed, msg=msg)


def main():
    run_module()


if __name__ == '__main__':
    main()
