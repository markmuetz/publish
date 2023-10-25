#!/usr/bin/env python
import argparse
import os
import sys
import importlib.util
import inspect
import subprocess as sp
from pathlib import Path
from pprint import pprint
import shutil
from typing import Union

import publish.example_settings as example_settings
import publish.settings_template as settings_template
from publish.publish_settings_schema import PublishSettings, CommonSettings

# https://stackoverflow.com/a/9562273/54557
# Doesn't write __pycache__ files.
sys.dont_write_bytecode = True


def build_parser():
    parser = argparse.ArgumentParser(
        prog='ProgramName', description='What the program does', epilog='Text at the bottom of help'
    )
    parser.add_argument('destination', nargs='?', default='draft')
    parser.add_argument('-N', '--dry-run', action='store_true')
    parser.add_argument('-P', '--print-settings', action='store_true')
    parser.add_argument('-S', '--settings-file', default='publish_settings.py')

    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument('-V', '--validate-only', action='store_true')
    group.add_argument('-E', '--print-example-settings', action='store_true')
    group.add_argument('-G', '--generate', action='store_true')

    fmap = {
        'version': ('v', dict(choices=['git_describe', 'user_supplied'])),
        'overwrite': ('o', dict(action='store_true')),
    }

    for field, value in CommonSettings.__fields__.items():
        if field in fmap:
            short_name, kwargs = fmap[field]
            field = field.replace('_', '-')
            if 'default' not in kwargs:
                kwargs['default'] = None
            parser.add_argument(f'-{short_name}', f'--{field}', **kwargs)
        else:
            field = field.replace('_', '-')
            parser.add_argument(f'--{field}', default=None, action='store_true')
    return parser


def format_path(path, **kwargs):
    return Path(str(path).format(**kwargs))


def load_module(local_filename: Union[str, Path]):
    """Use Python internals to load a Python module from a filename.

    :param local_filename: name of module to load
    :return: module
    """
    module_path = Path.cwd() / local_filename
    if not module_path.exists():
        raise Exception(f'Module file {module_path} does not exist')

    # No longer needed due to sys.modules line below.
    # Make sure any local imports in the module script work.
    sys.path.append(str(module_path.parent))
    module_name = Path(local_filename).stem

    try:
        # See: https://stackoverflow.com/a/50395128/54557
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except SyntaxError:
        print(f'Bad syntax in module file {module_path}')
        raise

    return module


def runcmd(cmd):
    return sp.run(cmd, shell=True, stdout=sp.PIPE, check=True, encoding='utf8')


def main():
    parser = build_parser()
    args = parser.parse_args()
    publish_settings_path = Path(args.settings_file)

    if args.print_example_settings:
        # Validate example settings.
        settings = PublishSettings(**example_settings.SETTINGS).dict()
        # pprint(settings, sort_dicts=False)
        # Print actual code.
        print(inspect.getsource(example_settings))
        sys.exit(0)

    if args.validate_only:
        settings_dict = load_module(publish_settings_path).SETTINGS
        # Validate settings using the schema.
        settings = PublishSettings(**settings_dict).dict()
        print('Settings file is valid')
        sys.exit(0)

    if args.generate:
        if publish_settings_path.exists() and input(f'"{publish_settings_path}" exists. Overwrite [y/n]? ') != 'y':
            print('Not writing')
            sys.exit(0)

        publish_settings_path.write_text(inspect.getsource(settings_template))
        print(f'Written "{publish_settings_path}"')
        sys.exit(0)

    if not publish_settings_path.exists():
        msg = (
            f'There must be a file named "{publish_settings_path}" in the current directory\n'
            'You can generate one using `publish -G`'
        )
        raise Exception(msg)

    if args.dry_run:

        def run_active_cmd(cmd):
            print(cmd)

    else:

        def run_active_cmd(cmd):
            runcmd(cmd)

    settings_dict = load_module(publish_settings_path).SETTINGS
    # Validate settings using the schema.
    pub_settings = PublishSettings(**settings_dict).dict()

    destinations = pub_settings.pop('destinations')
    if len(destinations) == 0:
        msg = 'At least one destination must be defined in settings'
        raise Exception(msg)
    # if len(destinations) != len(pub_settings['destinations']):
    #     msg = ('Duplicate keys detected:\n' +
    #            ', '.join([d['destination'] for d in pub_settings['destinations']]))
    #     raise Exception(msg)

    destination = args.destination
    if destination not in destinations:
        msg = f'Destination name "{destination}" not recognized\n' f'Must be one of: {", ".join(destinations.keys())}'
        raise Exception(msg)

    args_settings = vars(args)
    dest_settings = destinations[destination]
    # Filter out values of None.
    args_settings = {k: v for k, v in args_settings.items() if v is not None}
    dest_settings = {k: v for k, v in dest_settings.items() if v is not None}

    # Final settings is worked out from args_settings, dest_settings, pub_settings
    # with precedence in that order.
    settings = pub_settings.copy()

    def update_settings_set_by(sdict, sname):
        return {k: (sdict.get(k, False), sname) for k in CommonSettings.__fields__.keys() if k in sdict}

    settings_set_by = {}
    settings_set_by.update(update_settings_set_by(pub_settings, str(publish_settings_path)))

    settings.update(dest_settings)
    settings_set_by.update(
        update_settings_set_by(dest_settings, f'{publish_settings_path}:dest_settings:{destination}')
    )

    settings.update(args_settings)
    settings_set_by.update(update_settings_set_by(args_settings, 'args'))

    # settings.pop('destinations')
    files = settings.pop('files')
    if args.print_settings:
        pprint(settings)
        print()
        pprint(settings_set_by)
        sys.exit(0)

    if settings.get('ensure_make', True):
        if not os.getenv('MAKELEVEL'):
            print('Not being called with make, exiting')
            sys.exit(1)

    git_status = runcmd('git status --porcelain').stdout
    if git_status:
        if not settings.get('git_allow_uncommitted', False):
            msg = 'Uncommitted changes! Cannot run\n' + git_status
            raise Exception(msg)
        else:
            print('WARNING: Uncommitted changes.')
            print(git_status)

    if settings['version'] == 'git_describe':
        try:
            version = runcmd('git describe --tags').stdout.strip()
        except sp.CalledProcessError as e:
            print('No tags found -- add a tag with "git tag"')
            sys.exit(1)
    elif settings['version'] == 'user_supplied':
        version = args.version

    user_prompt = settings['user_prompt']

    paths = []
    for source_path_tpl, target_path_tpl in [(f['source'], f['target']) for f in files]:
        source_path = format_path(source_path_tpl, destination=destination, version=version).expanduser()
        target_path = format_path(target_path_tpl, destination=destination, version=version).expanduser()
        if not args.overwrite and not settings.get('overwrite', False):
            assert not target_path.exists(), '{} already exists'.format(target_path)
        paths.append((source_path, target_path))

    for source_path, target_path in paths:
        r = input('Create new file: {} (y/[n]): '.format(target_path)) if user_prompt else 'y'
        if r.lower() in ['y', 'yes']:
            target_path.parent.mkdir(exist_ok=True, parents=True)
            if not args.dry_run:
                shutil.copy(source_path, str(target_path))
            print('Created file: {}'.format(target_path))
        else:
            print('Not created')

    if settings['archive']:
        asettings = settings['archive']
        archive_path = format_path(asettings['target'], destination=destination, version=version).expanduser()
        archive_format = asettings['format']
        prefix = asettings['prefix']
        branch = asettings['branch']
        r = input('Create archive file: {} (y/[n]): '.format(archive_path)) if user_prompt else 'y'
        if r.lower() in ['y', 'yes']:
            archive_path.parent.mkdir(exist_ok=True, parents=True)
            cmd = f'git archive --format={archive_format} --prefix="{prefix}" -o {archive_path} {branch}'
            run_active_cmd(cmd)
            print('Created archive: {}'.format(archive_path))
