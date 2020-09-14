import collections

Post = collections.namedtuple("Post", ['username', 'game', 'image', 'editorial', 'coins', 'time', 'id', 'comments', 'completed', 'voted', 'gameSlug', 'display_name', 'tags'])
Comment = collections.namedtuple("Comment", ['username', 'text', 'time', 'id', 'color', 'display_name'])

