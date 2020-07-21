from flask import Flask, render_template, redirect, url_for, jsonify, session, flash, request, _request_ctx_stack
import boto3
import os
import collections
from dotenv import load_dotenv, find_dotenv
from authlib.integrations.flask_client import OAuth
from six.moves.urllib.parse import urlencode
import constants
from werkzeug.exceptions import HTTPException
from functools import wraps
import pymysql
import uuid
from datetime import datetime
from jose import jwt
from flask_cors import cross_origin
from six.moves.urllib.request import urlopen
import json

AUTH0_CALLBACK_URL = constants.AUTH0_CALLBACK_URL
AUTH0_CLIENT_ID = constants.AUTH0_CLIENT_ID
AUTH0_CLIENT_SECRET = constants.AUTH0_CLIENT_SECRET
AUTH0_DOMAIN = constants.AUTH0_DOMAIN
AUTH0_BASE_URL = 'https://' + AUTH0_DOMAIN
AUTH0_AUDIENCE = constants.AUTH0_AUDIENCE



application = Flask(__name__)
SECRET_KEY = os.urandom(32)
application.config['SECRET_KEY'] = SECRET_KEY
app = application

Post = collections.namedtuple("Post", ['username', 'game', 'image', 'editorial', 'coins', 'time', 'id', 'comments', 'completed', 'voted', 'gameNormalized', 'display_name'])
Comment = collections.namedtuple("Comment", ['username', 'text', 'time', 'id', 'color', 'display_name'])

UPLOAD_FOLDER = "/tmp"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALGORITHMS=['RS256']


# Format error response and append status code
def get_token_auth_header():
    """Obtains the Access Token from the Authorization Header
    """
    auth = request.headers.get("Authorization", None)
    if not auth:
        raise AuthError({"code": "authorization_header_missing",
                        "description":
                            "Authorization header is expected"}, 401)

    parts = auth.split()

    if parts[0].lower() != "bearer":
        raise AuthError({"code": "invalid_header",
                        "description":
                            "Authorization header must start with"
                            " Bearer"}, 401)
    elif len(parts) == 1:
        raise AuthError({"code": "invalid_header",
                        "description": "Token not found"}, 401)
    elif len(parts) > 2:
        raise AuthError({"code": "invalid_header",
                        "description":
                            "Authorization header must be"
                            " Bearer token"}, 401)

    token = parts[1]
    return token

# Error handler
class AuthError(Exception):
    def __init__(self, error, status_code):
        self.error = error
        self.status_code = status_code

@app.errorhandler(AuthError)
def handle_api_auth_error(ex):
    response = jsonify(ex.error)
    response.status_code = ex.status_code
    return response

@app.errorhandler(Exception)
def handle_auth_error(ex):
    response = jsonify(message=str(ex))
    response.status_code = (ex.code if isinstance(ex, HTTPException) else 500)
    return response


oauth = OAuth(app)

auth0 = oauth.register(
    'auth0',
    client_id=AUTH0_CLIENT_ID,
    client_secret=AUTH0_CLIENT_SECRET,
    api_base_url=AUTH0_BASE_URL,
    access_token_url=AUTH0_BASE_URL + '/oauth/token',
    authorize_url=AUTH0_BASE_URL + '/authorize',
    client_kwargs={
        'scope': 'openid profile email',
    },
)

aws_session = boto3.Session(
    aws_access_key_id = constants.AWS_PUBLIC_KEY,
    aws_secret_access_key = constants.AWS_SERVER_SECRET_KEY
)


def getUserInfo(username, email):
    dynamodb = aws_session.resource('dynamodb', region_name='us-west-2')
    following = []
    followers = []
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
    else:
        response = table.put_item(
                Item={
                    'username':username,
                    'email':email,
                    'following':[],
                    'filtered_following':{},
                    'followers':[],
                    'voted':[]
                    }
                )
        flash('Welcome! New gameshots account created. Find some friends and share some great game memories :)')
    return following, followers, voted, filtered_following, display_name

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if constants.PROFILE_KEY not in session:
            return redirect('/login')
        return f(*args, **kwargs)

    return decorated

def api_requires_auth(f):
    """Determines if the Access Token is valid"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = get_token_auth_header()
        jsonurl = urlopen("https://"+AUTH0_DOMAIN+"/.well-known/jwks.json")
        print(token)
        jwks = json.loads(jsonurl.read())
        unverified_header = jwt.get_unverified_header(token)
        rsa_key = {}
        print('jwks:')
        print(jwks)
        for key in jwks["keys"]:
            if key["kid"] == unverified_header["kid"]:
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"]
                }
        print(rsa_key)
        if rsa_key:
            print('have rsa')
            try:
                AUTH0_AUDIENCE = 'http://gameshots.gg/api'
                print(AUTH0_AUDIENCE)
                print("https://"+AUTH0_DOMAIN+"/")
                payload = jwt.decode(
                    token,
                    rsa_key,
                    algorithms=ALGORITHMS,
                    audience=AUTH0_AUDIENCE,
                    issuer="https://"+AUTH0_DOMAIN+"/"
                )
            except jwt.ExpiredSignatureError:
                raise AuthError({"code": "token_expired",
                                "description": "token is expired"}, 401)
            except jwt.JWTClaimsError:
                raise AuthError({"code": "invalid_claims",
                                "description":
                                    "incorrect claims,"
                                    "please check the audience and issuer"}, 401)
            except Exception:
                raise AuthError({"code": "invalid_header",
                                "description":
                                    "Unable to parse authentication"
                                    " token."}, 401)

            _request_ctx_stack.top.current_user = payload
            return f(*args, **kwargs)
        raise AuthError({"code": "invalid_header",
                        "description": "Unable to find appropriate key"}, 401)
    return decorated

# This doesn't need authentication
@app.route("/api/public")
@cross_origin(headers=["Content-Type", "Authorization"])
def public():
    response = "Hello from a public endpoint! You don't need to be authenticated to see this."
    return jsonify(message=response)

# This needs authentication
@app.route("/api/private")
@cross_origin(headers=["Content-Type", "Authorization"])
@api_requires_auth
def private():
    response = "Hello from a private endpoint! You need to be authenticated to see this."
    return jsonify(message=response)

# This needs authentication
@app.route("/api/createPost", methods=['POST'])
@cross_origin(headers=["Content-Type", "Authorization"])
@api_requires_auth
def api_create_post():
    completed = False
    result = request.form
    print(result)
    try:
        print('files')
        print(request.files)
        username = request.form['username'] 
        if 'file' in request.files:
            file = request.files['file']
            print('found file')
            game = request.form['game']
            print(game)
            comment = request.form['comment']
            print('comment')
            filename = file.filename
            if 'completed' in request.form:
                completed = True
            print('got here')
            createPost(username, file, game, comment, completed)
            print('did not get here')
            return jsonify('post created')
        else:
            return jsonify('missing file')
    except:
        return jsonify('missing data')

def createComment(user, text, postID):
    rds_con = pymysql.connect(constants.rds_host, user=constants.rds_user, port=constants.rds_port, passwd=constants.rds_password, db=constants.rds_dbname)
    commentID = str(uuid.uuid4())

    query = f"INSERT INTO COMMENTS (commentID, user, postID, text) VALUES (%s, %s, %s, %s)"

    try:
        with rds_con:
            cur = rds_con.cursor()
            cur.execute(query, (commentID, user, postID, text))
        rds_con.commit()
    finally:
        rds_con.close()


    return commentID


def createPost(user, picture, game, info, completed):
    postID = str(uuid.uuid4())
    #upload to S3 and get link
    s3 = aws_session.resource('s3')
    bucket = s3.Bucket('gameshots.gg')
    prefix = str(uuid.uuid4())
    filename = picture.filename
    if len(filename) > 100:
        filename = filename[-100:]
    filename = prefix + filename
    print(filename)
    bucket.upload_fileobj(picture, filename, ExtraArgs={'ACL':'public-read'})
    s3_link = f'https://s3-us-west-2.amazonaws.com/gameshots.gg/{filename}'
    comp_val = 0
    query = f"INSERT INTO POSTS (postID, user, picture, game, info, completed) VALUES (%s,%s,%s,%s,%s,%s)"
    if completed:
        comp_val = 1

    
    rds_con = pymysql.connect(constants.rds_host, user=constants.rds_user, port=constants.rds_port, passwd=constants.rds_password, db=constants.rds_dbname)
    try:
        with rds_con:
            cur = rds_con.cursor()
            vals = (postID, user, s3_link, game, info, comp_val)
            cur.execute(query, vals) 
        rds_con.commit()
    finally:
        rds_con.close()

@app.route('/settings', methods=['POST', 'GET'])
@requires_auth
def settings():
    username = session[constants.PROFILE_KEY]['name']
    dynamodb = aws_session.resource('dynamodb', region_name='us-west-2')
    table = dynamodb.Table('gg_users');
    displayNames = {}
    getDisplayName(username, displayNames)
    print(displayNames)
    if request.method == 'POST':
        result = request.form
        display_name = request.form['display_name']
        response = table.update_item(
                Key={'username':username},
                UpdateExpression="SET display_name = :x",
                ExpressionAttributeValues={
                    ':x':display_name,
                    }
                )
        return redirect(url_for('home'))

    response = table.get_item(
            Key={
                'username':username
                }
            )

    if 'Item' in response:
        if 'display_name' in response['Item']:
            display_name = response['Item']['display_name']
        else:
            display_name = username
    
    return render_template('settings.html', username=username, display_name=display_name)
    
@app.route('/create', methods=['POST', 'GET'])
@requires_auth
def create():
    username = session[constants.PROFILE_KEY]['name']
    completed = False
    if request.method == 'POST':
        result = request.form
        if 'file' in request.files:
            file = request.files['file']
            game = request.form['game']
            comment = request.form['comment']
            filename = file.filename
            if 'completed' in request.form:
                completed = True
            createPost(username, file, game, comment, completed)
            #file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return redirect(url_for('home'))
    return render_template('create.html')

@app.route('/callback')
def callback_handling():
    auth0.authorize_access_token()
    resp = auth0.get('userinfo')
    userinfo = resp.json()

    following, followers, voted, filtered_following, display_name = getUserInfo(userinfo['name'], userinfo['email'])

    session[constants.JWT_PAYLOAD] = userinfo
    session[constants.PROFILE_KEY] = {
        'user_id': userinfo['sub'],
        'name': userinfo['name'],
        'email': userinfo['email'], 
        'following':following,
        'followers':followers,
        'filtered_following':filtered_following,
        'voted':voted,
        'display_name':display_name
    }
    return redirect('/')

def getUserGames(username):
    query = f"SELECT DISTINCT game FROM POSTS where user='{username}'"
    games = []

    rds_con = pymysql.connect(constants.rds_host, user=constants.rds_user, port=constants.rds_port, passwd=constants.rds_password, db=constants.rds_dbname)

    try:
        with rds_con:
            cur = rds_con.cursor()
            cur.execute(query)

        game_info = cur.fetchall()
        games = [game[0] for game in game_info]

        query = f"SELECT DISTINCT game FROM POSTS where user='{username}' and completed=1"

        with rds_con:
            cur = rds_con.cursor()
            cur.execute(query)
    finally:
        rds_con.close()

    completed_games = cur.fetchall() 
    completed_games = [game[0] for game in completed_games]

    return games, completed_games 

def getUserThumbnails(username):
    query = f"SELECT postID, picture, completed FROM POSTS where user='{username}' ORDER BY createdtime DESC"
    posts = []

    rds_con = pymysql.connect(constants.rds_host, user=constants.rds_user, port=constants.rds_port, passwd=constants.rds_password, db=constants.rds_dbname)

    try:
        with rds_con:
            cur = rds_con.cursor()
            cur.execute(query)
    finally:
        rds_con.close()

    for row in cur.fetchall():
        posts.append((row[0], row[1], row[2])) 

    return posts

@app.route('/gamer/<username>', methods=['GET', 'POST'])
@requires_auth
def viewProfile(username):
    games, completed_games = getUserGames(username)
    filtered_following = session[constants.PROFILE_KEY]['filtered_following']
    myusername = session[constants.PROFILE_KEY]['name']
    display_name = session[constants.PROFILE_KEY]['display_name']
    if request.method == 'POST':
        data = request.form
        all_games = games[:]
        for item in data:
            all_games.remove(item)
        if len(all_games) > 0 or (username in filtered_following):
            filtered_following = updateFilter(myusername, username, all_games, filtered_following)
            session[constants.PROFILE_KEY]['filtered_following'] = filtered_following 
            session.modified = True
        
    posts = getUserThumbnails(username)
    following = session[constants.PROFILE_KEY]['following']
    followers = session[constants.PROFILE_KEY]['followers']
    profile_following, profile_followers, *_ = getUserInfo(username, "placeholder")
    filtered_games = []
    if username in filtered_following:
        filtered_games = filtered_following[username]
    return render_template('profile.html', screen_name=myusername, username=username, games=games, posts=posts, following=following, followers=followers, myusername=myusername, profile_following=profile_following, profile_followers=profile_followers, completed_games=completed_games, filtered=filtered_games, display_name=getDisplayName(username, {})) 

@app.route('/post/<postid>')
@requires_auth
def viewPost(postid):
    username = session[constants.PROFILE_KEY]['name']
    voted = session[constants.PROFILE_KEY]['voted']

    query = f"SELECT user, picture, game, info, createdtime, completed, coins FROM POSTS where postid='{postid}'"

    rds_con = pymysql.connect(constants.rds_host, user=constants.rds_user, port=constants.rds_port, passwd=constants.rds_password, db=constants.rds_dbname)

    try:
        with rds_con:
            cur = rds_con.cursor()
            cur.execute(query)

        info = cur.fetchone()
        user = info[0]
        displayNames = {}
        display_name = getDisplayName(user, displayNames)
        post = Post(info[0], info[2], info[1], info[3], info[6], info[4], postid, [], info[5], (postid in voted), normalize(info[2]), display_name)

        query = f"SELECT commentID, user, text, createdtime FROM COMMENTS where postID='{postid}' ORDER BY createdtime ASC"
        with rds_con:
            cur = rds_con.cursor()
            cur.execute(query)

        for row in cur.fetchall():
            user = row[1]
            display_name = getDisplayName(user, displayNames)
            post.comments.append(Comment(row[1], row[2], row[3], row[0], getColor(row[1]), display_name))
    finally:
        rds_con.close()

    return render_template('post.html', post=post, screen_name=username)



@app.route('/login')
def login():
    return auth0.authorize_redirect(redirect_uri=AUTH0_CALLBACK_URL)


@app.route('/logout')
def logout():
    session.clear()
    params = {'returnTo': url_for('home', _external=True), 'client_id': AUTH0_CLIENT_ID}
    return redirect(auth0.api_base_url + '/v2/logout?' + urlencode(params))

@requires_auth
@app.route('/postComment', methods=['POST'])
def postComment():
    username = session[constants.PROFILE_KEY]['name']
    text = request.form['text']
    postID = request.form['postID']
    commentID = createComment(username, text, postID);
    
    return jsonify(commentID);

@requires_auth
@app.route('/deleteComment', methods=['POST'])
def deleteComment():
    username = session[constants.PROFILE_KEY]['name']
    commentID = request.form['commentID']

    query= f"SELECT user from COMMENTS where commentID='{commentID}'"
    rds_con = pymysql.connect(constants.rds_host, user=constants.rds_user, port=constants.rds_port, passwd=constants.rds_password, db=constants.rds_dbname)

    result = "failure"

    try:
        with rds_con:
            cur = rds_con.cursor()
            cur.execute(query)
            owner = cur.fetchone()[0]
            if owner == username:
                query = f"DELETE FROM COMMENTS where commentID='{commentID}'"
                cur.execute(query)
                result = "success"
    finally:
        rds_con.commit()
        rds_con.close()
        return jsonify(result)

@requires_auth
@app.route('/upvote', methods=['POST'])
def upvote():
    username = session[constants.PROFILE_KEY]['name']
    postID = request.form['postID']
    voted = session[constants.PROFILE_KEY]['voted']
    if postID not in voted:
        #update dynamodb
        dynamodb = aws_session.resource('dynamodb', region_name='us-west-2')
        table = dynamodb.Table('gg_users');
        response = table.update_item(
                Key={'username':username},
                UpdateExpression="SET voted = list_append(voted, :i)",
                ExpressionAttributeValues={
                    ':i':[postID],
                    }
                )



        #update RDS
        rds_con = pymysql.connect(constants.rds_host, user=constants.rds_user, port=constants.rds_port, passwd=constants.rds_password, db=constants.rds_dbname)
        query= f"UPDATE POSTS set coins=coins+1 where postID=%s"

        try:
            with rds_con:
                cur = rds_con.cursor()
                cur.execute(query, (postID))
            rds_con.commit()
        finally:
            rds_con.close()

        voted.append(postID)
        session.modified = True
        return jsonify('success')
    return jsonify('already voted')


@requires_auth
@app.route('/downvote', methods=['POST'])
def downvote():
    username = session[constants.PROFILE_KEY]['name']
    postID = request.form['postID']
    voted = session[constants.PROFILE_KEY]['voted']
    if postID in voted: #no negative votes, only takeaway your own vote
        #update dynamodb
        idx = voted.index(postID)
        dynamodb = aws_session.resource('dynamodb', region_name='us-west-2')
        table = dynamodb.Table('gg_users');
        response = table.update_item(
                Key={'username':username},
                UpdateExpression=f"REMOVE voted[{idx}]",
                ReturnValues="UPDATED_NEW"
                )

        #update RDS
        query= f"UPDATE POSTS set coins=coins-1 where postID=%s"
        rds_con = pymysql.connect(constants.rds_host, user=constants.rds_user, port=constants.rds_port, passwd=constants.rds_password, db=constants.rds_dbname)
        try:
            with rds_con:
                cur = rds_con.cursor()
                cur.execute(query, (postID))
            rds_con.commit()
        finally:
            rds_con.close()

        voted.remove(postID)
        session.modified = True
        return jsonify('success')
    return jsonify('cannot downvote something that was not upvoted')


@requires_auth
@app.route('/deletePost/<postID>', methods=['POST'])
def deletePost(postID):
    username = session[constants.PROFILE_KEY]['name']

    rds_con = pymysql.connect(constants.rds_host, user=constants.rds_user, port=constants.rds_port, passwd=constants.rds_password, db=constants.rds_dbname)
    query= f"SELECT user from POSTS where postID='{postID}'"
    try:
        with rds_con:
            cur = rds_con.cursor()
            cur.execute(query)
            owner = cur.fetchone()[0]
            if owner == username:
                query = f"DELETE FROM POSTS where postID='{postID}'"
                cur.execute(query)
                query = f"DELETE FROM COMMENTS where postID='{postID}'"
                cur.execute(query)
        rds_con.commit()
    finally:
        rds_con.close()
    
    return redirect(url_for('home'))


def normalize(game):
    game = game.replace(":", "_")
    return game.replace(" ", "_")

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
    

@requires_auth
@app.route('/follow', methods=['POST'])
def followUser():
    username = session[constants.PROFILE_KEY]['name']
    follow = request.form['follow']
    dynamodb = aws_session.resource('dynamodb', region_name='us-west-2')
    table = dynamodb.Table('gg_users');
    response = table.update_item(
            Key={'username':username},
            UpdateExpression="SET following = list_append(following, :i)",
            ExpressionAttributeValues={
                ':i':[follow],
                },
            ReturnValues="UPDATED_NEW"
            )

    session[constants.PROFILE_KEY]['following'] = response['Attributes']['following']

    response = table.update_item(
            Key={'username':follow},
            UpdateExpression="SET followers = list_append(followers, :i)",
            ExpressionAttributeValues={
                ':i':[username],
                },
            ReturnValues="UPDATED_NEW"
            )

    #add to followers
    session.modified = True
    return jsonify('success')


@requires_auth
@app.route('/unfollow', methods=['POST'])
def unfollowUser():
    username = session[constants.PROFILE_KEY]['name']
    unfollow = request.form['unfollow']
    dynamodb = aws_session.resource('dynamodb', region_name='us-west-2')
    table = dynamodb.Table('gg_users');
    response = table.get_item(
            Key={
                'username':username
                }
            )
    if 'Item' in response:
        if 'following' in response['Item']:
            following = response['Item']['following']
            idx = following.index(unfollow)

            response = table.update_item(
                    Key={'username':username},
                    UpdateExpression=f"REMOVE following[{idx}]",
                    ReturnValues="UPDATED_NEW"
                    )

            _, followers, *_ = getUserInfo(unfollow, 'placeholder')
            idx = followers.index(username)
            response = table.update_item(
                    Key={'username':unfollow},
                    UpdateExpression=f"REMOVE followers[{idx}]",
                    ReturnValues="UPDATED_NEW"
                    )

            response = table.get_item(
                    Key={
                        'username':username
                        }
                    )

            if 'Item' in response:
                if 'following' in response['Item']:
                    following = response['Item']['following']
                if 'followers' in response['Item']:
                    followers = response['Item']['followers']
            session[constants.PROFILE_KEY]['following'] = following 
            session[constants.PROFILE_KEY]['followers'] = followers
            session.modified = True

            #remove from followers
            return jsonify('success')



@app.route('/favicon.ico')
def favicon():
    return app.send_static_file('favicon.ico')

@app.route('/')
def home():
    if constants.PROFILE_KEY not in session:
        return render_template('index.html')
    else:
        return feed()

def getColor(name):
    colors  = ['Aqua', 'Aquamarine', 'Blue', 'BlueViolet', 'Chartreuse', 'Coral', 'CornflowerBlue', 'Crimson',
        'Cyan', 'DarkMagenta', 'DarkOrange', 'Fuchsia', 'ForestGreen', 'Gold', 'GreenYellow',
        'HotPink', 'Lavender', 'LawnGreen', 'Lime', 'Magenta', 'MediumSpringGreen', 'Red', 'RoyalBlue', 'Yellow']
    value = ord(name[0])*len(name)
    return colors[value%len(colors)];

def feed():
    posts = []
    postRefs = {}
    screen_name = session[constants.PROFILE_KEY]['name']
    display_name = session[constants.PROFILE_KEY]['name']
    email = session[constants.PROFILE_KEY]['email']
    #following = getUserInfo(screen_name, email)
    following = session[constants.PROFILE_KEY]['following']
    filtered_following = session[constants.PROFILE_KEY]['filtered_following']
    voted = session[constants.PROFILE_KEY]['voted']
    users = following+[screen_name]
    placeholder = '%s'
    allParams = []
    games = set()

    displayNames = {}
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
            query += "\n UNION \n"

    placeholders = ', '.join(placeholder for user in users)
    allParams.extend(users)
    query += f"SELECT postID, user, picture, game, info, createdtime, completed, coins FROM POSTS where user in ({placeholders}) ORDER BY createdtime DESC"

    rds_con = pymysql.connect(constants.rds_host, user=constants.rds_user, port=constants.rds_port, passwd=constants.rds_password, db=constants.rds_dbname)
    try:
        with rds_con:
            cur = rds_con.cursor()
            cur.execute(query, tuple(allParams))

        for row in cur.fetchall():
            postID = row[0]
            game = row[3]
            games.add(game)
            user = row[1]
            display_name = getDisplayName(user, displayNames)
            newPost = Post(user, game, row[2], row[4], row[7], row[5], postID, [], row[6], (postID in voted), normalize(game), display_name)
            postRefs[postID] = newPost 
            posts.append(newPost)

        games = [(game, normalize(game)) for game in games]

        if len(posts) > 0:
            placeholder = '%s'
            placeholders = ', '.join(placeholder for postID in postRefs.keys())
            query = f"SELECT postID, commentID, user, text, createdtime FROM COMMENTS where postID in ({placeholders}) ORDER BY createdtime ASC"
            with rds_con:
                cur = rds_con.cursor()
                cur.execute(query, tuple(postRefs.keys()))

            for row in cur.fetchall():
                postID = row[0]
                user = row[2]
                display_name = getDisplayName(user, displayNames)
                comment = Comment(row[2], row[3], row[4], row[1], getColor(row[2]), display_name)
                postRefs[postID].comments.append(comment)
    finally:
        rds_con.close()

    return render_template('feed.html', posts=posts, screen_name=screen_name, games=games, following=following, display_name=display_name)


if __name__=='__main__':
    application.run(host='0.0.0.0', port='80', debug=True)

