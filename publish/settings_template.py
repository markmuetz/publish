SETTINGS = {
    # Optional, with defaults to these values.
    'ensure_make': True,
    'user_prompt': True,
    'git_allow_uncommitted': False,
    'version': 'git_describe',
    # At least one required.
    'destinations': [
        {
            'destination': 'draft',
            'files': [{
                'source': '<enter_path_here>',
                'target': '<enter_path_here>',
            }]
        },
        {
            'destination': 'release',
            'files': [{
                'source': '<enter_path_here>',
                'target': '<enter_path_here>',
            }]
        },
    ],
    # Optional.
    'archive': {
        'branch': 'main',
        'format': 'tgz',
        'prefix': '<enter_prefix_here>',
        'target': '<enter_path_here>',
    }
}
