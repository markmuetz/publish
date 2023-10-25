publish
=======

Simple tool to publish files from git repositories to various locations. Files are written out with `git describe --tags` so that they are versioned according to the git commits and tags (the repository must have at least one tag). The version is injected into the output paths through string formatting. Optionally, the repository can be archived to a backed-up location. Settings can be applied at the command line, the `destination` level or the `publish_settings.py` level, with that order or precedence. Multiple destinations allow for outputting of separate files within the repository, or to separate targets (potentially with different settings). A `pydantic` schema validates the settings.

example
=======

`publish_settings.py`:

```python
SETTINGS = {
    'ensure_make': True,
    'user_prompt': True,
    'git_allow_uncommitted': False,
    'version': 'git_describe',
    'destinations': {
        'draft': {
            'files': [
                {
                    'source': 'intraseasonal_srp_erl/_build/intraseasonal_srp.pdf',
                    'target': (
                        '~/Dropbox/Academic/Projects/COSMIC/Writeups/intraseasonal_srp/'
                        '{destination}/intraseasonal_srp_{version}.pdf'
                    ),
                }
            ]
        },
        'release': {
            'files': [
                {
                    'source': 'intraseasonal_srp_erl/_build/intraseasonal_srp.pdf',
                    'target': (
                        '~/Dropbox/Academic/Projects/COSMIC/Writeups/intraseasonal_srp/'
                        '{destination}/intraseasonal_srp_{version}.pdf'
                    ),
                }
            ]
        },
    },
    'archive': {
        'branch': 'main',
        'format': 'tgz',
        'prefix': 'intraseasonal_srp',
        'target': (
            '~/Dropbox/Academic/Projects/COSMIC/Writeups/intraseasonal_srp/archive/intraseasonal_srp_{version}.tgz'
        ),
    },
}
```

```bash
$ publish draft
```
