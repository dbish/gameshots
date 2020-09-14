import boto3
import pymysql
import constants
from post import *
import uuid

aws_session = boto3.Session(
    aws_access_key_id = constants.AWS_PUBLIC_KEY,
    aws_secret_access_key = constants.AWS_SERVER_SECRET_KEY
)


def getColor(name):
    colors  = ['Aqua', 'Aquamarine', 'Blue', 'BlueViolet', 'Chartreuse', 'Coral', 'CornflowerBlue', 'Crimson',
        'Cyan', 'DarkMagenta', 'DarkOrange', 'Fuchsia', 'ForestGreen', 'Gold', 'GreenYellow',
        'HotPink', 'Lavender', 'LawnGreen', 'Lime', 'Magenta', 'MediumSpringGreen', 'Red', 'RoyalBlue', 'Yellow']
    value = ord(name[0])*len(name)
    return colors[value%len(colors)];


def createSlug(name):
    punctuation_to_delete = '''!"#$%&()*+,./:;<=>?@[\]^_`{|}~'''
    name = name.replace("'", "-")
    name = name.translate(str.maketrans('', '', punctuation_to_delete)).lower().replace(" ", "-")
    return name


def userExists(username):
    dynamodb = aws_session.resource('dynamodb', region_name='us-west-2')
    table = dynamodb.Table('gg_users');
    response = table.get_item(
            Key={
                'username':username
                }
            )

    if 'Item' in response:
        return True
    else:
        return False


def getUserInfo(username, email):
    dynamodb = aws_session.resource('dynamodb', region_name='us-west-2')
    following = []
    followers = []
    games_following = []
    voted = []
    display_name = ''
    filtered_following = []
    table = dynamodb.Table('gg_users');
    response = table.get_item(
            Key={
                'username':username
                }
            )

    if 'Item' in response:
        if 'display_name' in response['Item']:
            display_name = response['Item']['display_name']
        if 'following' in response['Item']:
            following = response['Item']['following']
        if 'followers' in response['Item']:
            followers = response['Item']['followers']
        if 'voted' in response['Item']:
            voted = response['Item']['voted']
        if 'filtered_following' in response['Item']:
            filtered_following = response['Item']['filtered_following']
        if 'games_following' in response['Item']:
            games_following = response['Item']['games_following']
    else:
        response = table.put_item(
                Item={
                    'username':username,
                    'email':email,
                    'following':[],
                    'filtered_following':{},
                    'games_following':{},
                    'followers':[],
                    'voted':[]
                    }
                )
        addUserToIndex(username, '')
        flash('Welcome! New gameshots account created. Find some friends and share some great game memories :)', 'success')
    return following, followers, voted, filtered_following, display_name, games_following


def getRDSCon():
    rds_con = pymysql.connect(constants.rds_host, user=constants.rds_user, port=constants.rds_port, passwd=constants.rds_password, db=constants.rds_dbname, charset='utf8mb4')
    return rds_con


def uploadToRDS(query, data_tuple):
    rds_con = getRDSCon() 

    try:
        with rds_con:
            cur = rds_con.cursor()
            cur.execute(query, data_tuple)
        rds_con.commit()
    except Exception as e:
        print(e)

    rds_con.close()

def getFromRDS(query, data_tuple=[]):
    rds_con = getRDSCon() 
    try: 
        with rds_con:
            cur = rds_con.cursor()
            cur.execute(query, data_tuple)
    except Exception as e:
        print(e)

    rds_con.close()
    
    return cur.fetchall()

def createComment(user, text, postID):
    commentID = str(uuid.uuid4())
    query = f"INSERT INTO COMMENTS (commentID, user, postID, text) VALUES (%s, %s, %s, %s)"
    uploadToRDS(query, (commentID, user, postID, text))

    query = f"SELECT user from POSTS where postID='{postID}'"
    postOwner = getFromRDS(query)[0][0]
    if user != postOwner:
        addNotification(postOwner, url_for('viewPost', postid=postID), f"{user} commented on your post")
    return commentID


def addNotification(user, link, info):
    notificationID = str(uuid.uuid4())
    query = f"INSERT INTO NOTIFICATIONS (ID, user, link, info) VALUES (%s,%s,%s,%s)"
    vals = (notificationID, user, link, info)
    uploadToRDS(query, vals)

def getNewNotifications(user, timestamp):
    query = f"SELECT ID, link, info, createdtime, read_state FROM NOTIFICATIONS where user='{user}' and createdtime > '{timestamp}' ORDER BY createdtime DESC limit 100"
    notifications = getFromRDS(query)
    return notifications

def createTags(postID, tags):
    query = f"INSERT INTO Tags (postID, user) VALUES (%s,%s)"
    tags = list(set(tags))
    for tag in tags:
        vals = (postID, tag)
        uploadToRDS(query, vals)
        addNotification(tag, url_for('viewPost', postid=postID), f"you were tagged in a post!")

def updatePost(postID, game, info, completed, cur_tags, old_tags):
    slug = createSlug(game)
    query = f"UPDATE POSTS SET game=%s, info=%s, completed=%s where postID='{postID}'"
    deleted_tags = old_tags.difference(cur_tags)
    added_tags = cur_tags.difference(old_tags)
    comp_val = 0
    if completed:
        comp_val = 1

    vals = (game, info, comp_val)
    uploadToRDS(query, vals)

    if len(deleted_tags) > 0:
        placeholder = '%s'
        placeholders = ', '.join(placeholder for tag in deleted_tags)
        query = f"DELETE from Tags where postID='{postID}' and user in ({placeholders})"
        uploadToRDS(query, list(deleted_tags))

    if len(added_tags) > 0:
        query = f"INSERT INTO Tags (postID, user) VALUES (%s,%s)"
        for tag in added_tags:
            vals = (postID, tag)
            uploadToRDS(query, vals)
            addNotification(tag, url_for('viewPost', postid=postID), f"you were tagged in a post!")

def createPost(user, link, game, info, completed):
    postID = str(uuid.uuid4())
    slug = createSlug(game)
    comp_val = 0
    query = f"INSERT INTO POSTS (postID, user, picture, game, info, completed, slug) VALUES (%s,%s,%s,%s,%s,%s,%s)"
    if completed:
        comp_val = 1


    vals = (postID, user, link, game, info, comp_val, slug)
    uploadToRDS(query, vals)

    return postID

def getUserGames(username):
    query = f"SELECT DISTINCT game FROM POSTS where user='{username}'"
    games = []
    game_info = getFromRDS(query)
    games = [game[0] for game in game_info]
    

    query = f"SELECT DISTINCT game FROM POSTS where user='{username}' and completed=1"
    completed_games = getFromRDS(query)
    completed_games = [game[0] for game in completed_games]
    
    return games, completed_games

def getUserThumbnails(username, before):
    query = f"SELECT postID, picture, completed, createdtime FROM POSTS where user='{username}'"
    query += " and length(picture) > 0"
    if before:
        query += f" AND createdtime <= '{before}'"
    query += " ORDER BY createdtime DESC LIMIT 18"

    posts = []

    all_posts = getFromRDS(query)

    for row in all_posts: 
        posts.append((row[0], row[1], row[2], row[3]))

    return posts

def updateFilter(username, following, games, curFilter):
    dynamodb = aws_session.resource('dynamodb', region_name='us-west-2')
    table = dynamodb.Table('gg_users');
    response = table.update_item(
            Key = {
                'username':username
                },
            UpdateExpression="SET filtered_following.#f = :v",
            ExpressionAttributeNames = {'#f':following},
            ExpressionAttributeValues={
                ':v':games,
            }
            )
    curFilter[following] = games
    return curFilter

def getDisplayName(username, cachedNames):
    if username not in cachedNames:
        dynamodb = aws_session.resource('dynamodb', region_name='us-west-2')
        table = dynamodb.Table('gg_users');
        display_name = username
        response = table.get_item(
                Key={'username':username},
                AttributesToGet=['display_name'])
        if 'Item' in response:
            if 'display_name' in response['Item']:
                display_name = response['Item']['display_name']
        cachedNames[username] = display_name
    return cachedNames[username]

def getGamePosts(before, game, screen_name, following, voted, games_following):
    if game is None:
        games = games_following 
    else:
        games = [game]
    placeholder = '%s'
    placeholders = ', '.join(placeholder for game in games)

    query = f"SELECT postID, user, picture, game, info, createdtime, completed, coins FROM POSTS where slug in ({placeholders})"
    query += " and length(picture) > 0"
    if before:
        query += f" AND createdtime <= '{before}'"
    query += " ORDER BY createdtime DESC LIMIT 10"
    all_posts = getFromRDS(query, tuple(games))

    posts = getPostData(all_posts, voted)

    return posts


def getPostData(all_posts, voted):
    displayNames = {}
    postRefs = {}
    posts = []
    try:
        for row in all_posts:
            postID = row[0]
            game = row[3]
            user = row[1]
            display_name = getDisplayName(user, displayNames)
            newPost = Post(user, game, row[2], row[4], row[7], row[5].strftime("%Y-%m-%d %H:%M:%S"), postID, [], row[6], (postID in voted), createSlug(game), display_name, [])
            postRefs[postID] = newPost
            posts.append(newPost)


        if len(posts) > 0:
            placeholder = '%s'
            placeholders = ', '.join(placeholder for postID in postRefs.keys())
            query = f"SELECT postID, commentID, user, text, createdtime FROM COMMENTS where postID in ({placeholders}) ORDER BY createdtime ASC"

            all_comments = getFromRDS(query, tuple(postRefs.keys()))

            for row in all_comments:
                postID = row[0]
                user = row[2]
                display_name = getDisplayName(user, displayNames)
                comment = Comment(row[2], row[3], row[4], row[1], getColor(row[2]), display_name)
                postRefs[postID].comments.append(comment)

            query = f"SELECT postID, user FROM Tags where postID in ({placeholders})"

            all_tags = getFromRDS(query, tuple(postRefs.keys()))

            for row in all_tags:
                postID = row[0]
                user = row[1]
                postRefs[postID].tags.append(user)

    except Exception as e:
        print(e)

    return posts

def getPosts(before, screen_name, email, following, filtered_following, voted):
    users = following+[screen_name]
    placeholder = '%s'
    allParams = []

    #filtered users
    query = ''
    for user in filtered_following:
        filtered_games = filtered_following[user]
        if len(filtered_games) > 0:
            users.remove(user)
            placeholders = ', '.join(placeholder for game in filtered_games)
            allParams.append(user)
            allParams.extend(filtered_games)
            query += f"SELECT postID, user, picture, game, info, createdtime, completed, coins FROM POSTS where user=%s and game not in ({placeholders})"
            query += " and length(picture) > 0"
            query += "\n UNION \n"

    placeholders = ', '.join(placeholder for user in users)
    allParams.extend(users)
    query += f"SELECT postID, user, picture, game, info, createdtime, completed, coins FROM POSTS where user in ({placeholders})"
    query += " and length(picture) > 0"
    if before:
        query += f" AND createdtime <= '{before}'"
    query += " ORDER BY createdtime DESC LIMIT 10"
    all_posts = getFromRDS(query, tuple(allParams))
    posts = getPostData(all_posts, voted)
    return posts

