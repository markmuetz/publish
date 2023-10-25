#!/usr/bin/env python
import argparse
import importlib.util
import inspect
import os
import shutil
import subprocess as sp
import sys
from pathlib import Path
from pprint import pprint
from typing import Union

import publish.example_settings as example_settings
import publish.settings_template as settings_template
from publish.publish_settings_schema import CommonSettings, PublishSettings

# https://stackoverflow.com/a/9562273/54557
# Doesn't write __pycache__ files.
sys.dont_write_bytecode = True


class PublisherError(Exception):
    def __init__(self, msg, settings_key=None):
        super().__init__(msg)
        self.settings_key = settings_key


def build_parser():
    parser = argparse.ArgumentParser(
        prog='ProgramName', description='What the program does', epilog='Text at the bottom of help'
    )
    parser.add_argument('destination', nargs='?', default='draft')
    parser.add_argument('-X', '--raise-exception', action='store_true')
    parser.add_argument('-N', '--dry-run', action='store_true')
    parser.add_argument('-P', '--print-settings', action='store_true')
    parser.add_argument('-S', '--settings-file', default='publish_settings.py')

    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument('-V', '--validate-settings-only', action='store_true')
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
        raise PublisherError(f'Module file {module_path} does not exist')

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


class Publisher:
    def __init__(self, args_settings=None):
        if not args_settings:
            parser = build_parser()
            args = parser.parse_args([])
            args_settings = vars(args)
        self.args_settings = args_settings
        self.publish_settings_path = Path(args_settings.get('settings_file', 'publish_settings.py'))

    def load_settings(self):
        module = load_module(self.publish_settings_path)
        if not hasattr(module, 'SETTINGS'):
            msg = f'module {module} has no settings variable'
            raise PublisherError(msg)

        args_settings = self.args_settings

        settings_dict = module.SETTINGS
        # Validate settings using the schema.
        pub_settings = PublishSettings(**settings_dict).dict()

        destinations = pub_settings['destinations']
        destination = args_settings['destination']
        if destination not in destinations:
            msg = f'Destination name "{destination}" not recognized\nMust be one of: {", ".join(destinations.keys())}'
            raise PublisherError(msg)

        dest_settings = destinations[destination]

        # Filter out values of None.
        args_settings = {k: v for k, v in args_settings.items() if v is not None}
        dest_settings = {k: v for k, v in dest_settings.items() if v is not None}
        # Final settings is worked out from args_settings, dest_settings, pub_settings
        # with precedence in that order. (Set by insertion order into dict).
        settings_locs = {
            str(self.publish_settings_path): pub_settings,
            f'{self.publish_settings_path}:dest_settings:{destination}': dest_settings,
            'args': args_settings,
        }

        settings = {}
        settings_set_by = {}
        def update_settings_set_by(sdict, sname):
            # return {k: (sdict.get(k, False), sname) for k in CommonSettings.__fields__.keys() if k in sdict}
            return {k: (v, sname) for k, v in sdict.items()}

        for sloc, s in settings_locs.items():
            settings.update(s)
            settings_set_by.update(update_settings_set_by(s, sloc))

        self.settings = settings
        self.settings_set_by = settings_set_by

    def dispatch(self):
        if not self.args_settings['print_example_settings'] and not self.publish_settings_path.exists():
            msg = (
                f'There must be a file named "{publish_settings_path}" in the current directory\n'
                'You can generate one using `publish -G`'
            )
            raise PublisherError(msg)

        for argkey in ['print_example_settings', 'validate_settings_only', 'generate']:
            if self.args_settings[argkey]:
                dispatch_method = getattr(self, argkey)
                dispatch_method()
                return
        self.load_settings()
        if self.args_settings['print_settings']:
            self.print_settings()
            return

        self.validate_calling_env()

        if self.args_settings['dry_run']:

            def run_active_cmd(cmd):
                print(cmd)

        else:

            def run_active_cmd(cmd):
                runcmd(cmd)

        self.publish(run_active_cmd)

    def publish(self, run_active_cmd):
        destination = self.settings['destination']
        user_prompt = self.settings['user_prompt']
        version = self.get_version_str()

        files = self.settings['files']
        paths = []
        for source_path_tpl, target_path_tpl in [(f['source'], f['target']) for f in files]:
            source_path = format_path(source_path_tpl, destination=destination, version=version).expanduser()
            target_path = format_path(target_path_tpl, destination=destination, version=version).expanduser()
            if not self.settings['overwrite'] and not self.settings.get('overwrite', False):
                assert not target_path.exists(), '{} already exists'.format(target_path)
            paths.append((source_path, target_path))

        for source_path, target_path in paths:
            r = input('Create new file: {} (y/[n]): '.format(target_path)) if user_prompt else 'y'
            if r.lower() in ['y', 'yes']:
                target_path.parent.mkdir(exist_ok=True, parents=True)
                if not self.settings['dry_run']:
                    shutil.copy(source_path, str(target_path))
                print('Created file: {}'.format(target_path))
            else:
                print('Not created')

        if self.settings['archive']:
            asettings = self.settings['archive']
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

    def get_version_str(self):
        if self.settings['version'] == 'git_describe':
            try:
                version = runcmd('git describe --tags').stdout.strip()
            except sp.CalledProcessError as e:
                raise PublisherError('No tags found -- add a tag with "git tag"')
        elif settings['version'] == 'user_supplied':
            version = args.version
        return version

    def print_example_settings(self):
        # Validate example settings.
        settings = PublishSettings(**example_settings.SETTINGS).dict()
        # Print actual code.
        print(inspect.getsource(example_settings))

    def validate_settings_only(self):
        settings_dict = load_module(self.publish_settings_path).SETTINGS
        # Validate settings using the schema.
        settings = PublishSettings(**settings_dict).dict()
        print('Settings file is valid')

    def generate(self):
        if (
            self.publish_settings_path.exists()
            and input(f'"{self.publish_settings_path}" exists. Overwrite [y/n]? ') != 'y'
        ):
            print('Not writing')
            return

        self.publish_settings_path.write_text(inspect.getsource(settings_template))
        print(f'Written "{self.publish_settings_path}"')

    def print_settings(self):
        print('Full settings')
        print('=============')
        pprint(self.settings, sort_dicts=False)
        print()
        print('Settings set by')
        print('===============')
        pprint(self.settings_set_by, sort_dicts=False)

    def validate_calling_env(self):
        if self.settings.get('ensure_make', True):
            if not os.getenv('MAKELEVEL'):
                raise PublisherError('Not being called with make, exiting', 'ensure_make')

        git_status = runcmd('git status --porcelain').stdout
        if git_status:
            if not self.settings.get('git_allow_uncommitted', False):
                msg = 'Uncommitted changes! Cannot run\n' + git_status
                raise PublisherError(msg, 'git_allow_uncommitted')
            else:
                print('WARNING: Uncommitted changes.')
                print(git_status)


def main():
    parser = build_parser()
    args = parser.parse_args()
    args_settings = vars(args)
    publisher = Publisher(args_settings)
    try:
        publisher.dispatch()
    except PublisherError as pe:
        msg = 'ERROR: ' + str(pe)
        print('=' * len(msg))
        print(msg)
        if pe.settings_key:
            print(f'{pe.settings_key} set by: {publisher.settings_set_by[pe.settings_key][1]}')
        print('=' * len(msg))
        if not args.raise_exception:
            sys.exit(1)
        else:
            raise

    if not args.raise_exception:
        sys.exit(0)
