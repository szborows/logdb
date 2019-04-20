from utils import merge_dicts

def compare_dicts(actual, expected, path=None):
    def mkpath(p, *args):
        return '.'.join(p + list(args))
    path = path or []
    for key in expected:
        if key in actual:
            if isinstance(actual[key], dict) and isinstance(expected[key], dict):
                compare_dicts(actual[key], expected[key], path + [str(key)])
            else:
                if actual[key] != expected[key]:
                    raise RuntimeError('mismatch at {0}'.format(mkpath(path, key)))
        else:
            raise RuntimeError('missing key ' + mkpath(path, key))

def test_merge_dict():
    compare_dicts(merge_dicts({}, {}), {})
    compare_dicts(merge_dicts({'def': 'ault'}, {}), {'def': 'ault'})
    compare_dicts(merge_dicts({'def': 'ault'}, {'def': 'other'}), {'def': 'other'})
    compare_dicts(
        merge_dicts({'nested': {'def': 'ault', 'other': 'option'}}, {'nested': {'def': 'other'}}),
        {'nested': {'def': 'other', 'other': 'option'}}
    )
