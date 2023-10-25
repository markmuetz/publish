EXAMPLE_SETTINGS = {
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
            '~/Dropbox/Academic/Projects/COSMIC/Writeups/intraseasonal_srp/' 'archive/intraseasonal_srp_{version}.tgz'
        ),
    },
}
