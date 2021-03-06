def merge_dicts(a, b, path=None):
    path = path or []
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                merge_dicts(a[key], b[key], path + [str(key)])
            else:
                a[key] = b[key]
        else:
            a[key] = b[key]
    return a

class RaftState:
    FOLLOWER = 0
    CANDIDATE = 1
    LEADER = 2

