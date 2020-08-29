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
import requests
import string

AUTH0_CALLBACK_URL = constants.AUTH0_CALLBACK_URL
AUTH0_CLIENT_ID = constants.AUTH0_CLIENT_ID
AUTH0_CLIENT_SECRET = constants.AUTH0_CLIENT_SECRET
AUTH0_DOMAIN = constants.AUTH0_DOMAIN
AUTH0_BASE_URL = 'https://' + AUTH0_DOMAIN
AUTH0_AUDIENCE = constants.AUTH0_AUDIENCE

PIC_FILE_TYPES = set(['png', 'jpg', 'jpeg', 'gif'])
MOV_FILE_TYPES = set(['mp4'])
MAX_FILE_SIZE = 10*1024*1024 #10MB max

application = Flask(__name__)
SECRET_KEY = os.urandom(32)
application.config['SECRET_KEY'] = SECRET_KEY
app = application

Post = collections.namedtuple("Post", ['username', 'game', 'image', 'editorial', 'coins', 'time', 'id', 'comments', 'completed', 'voted', 'gameSlug', 'display_name', 'tags'])
Comment = collections.namedtuple("Comment", ['username', 'text', 'time', 'id', 'color', 'display_name'])
Notification = collections.namedtuple("Notification", ['id', 'username', 'link', 'info', 'timestamp', 'read'])

UPLOAD_FOLDER = "/tmp"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE
ALGORITHMS=['RS256']

@app.before_request
def before_request():
    if not request.is_secure:
        url = request.url.replace('http://', 'https://', 1)
        code = 301
        return redirect(url, code=code)

def createSlug(name):
    punctuation_to_delete = '''!"#$%&()*+,./:;<=>?@[\]^_`{|}~'''
    name = name.replace("'", "-")
    name = name.translate(str.maketrans('', '', punctuation_to_delete)).lower().replace(" ", "-")
    return name


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
        flash('Welcome! New gameshots account created. Find some friends and share some great game memories :)')
    return following, followers, voted, filtered_following, display_name, games_following

def addUserToIndex(username, displayname):
    cloudsearch = aws_session.client('cloudsearchdomain', endpoint_url='http://doc-gg-test-6bwc55aehpsty6w5qfiv4pbsmy.us-west-2.cloudsearch.amazonaws.com', region_name='us-west-2')
    doc = {}
    doc['id'] = username 
    doc['type'] = 'add'
    doc['fields'] = {}
    doc['fields']['username'] = username
    doc['fields']['display_name'] = displayname
    cloudsearch.upload_documents(documents = json.dumps([doc]), contentType="application/json")

def updateSearchIndex(username, displayname):
    cloudsearch = aws_session.client('cloudsearchdomain', endpoint_url='http://doc-gg-test-6bwc55aehpsty6w5qfiv4pbsmy.us-west-2.cloudsearch.amazonaws.com', region_name='us-west-2')
    doc = {'id':username, 'type':'delete'}
    cloudsearch.upload_documents(documents = json.dumps([doc]), contentType="application/json")
    addUserToIndex(username, displayname)

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
        jwks = json.loads(jsonurl.read())
        unverified_header = jwt.get_unverified_header(token)
        rsa_key = {}
        for key in jwks["keys"]:
            if key["kid"] == unverified_header["kid"]:
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"]
                }
        if rsa_key:
            try:
                AUTH0_AUDIENCE = 'http://gameshots.gg/api'
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
    try:
        username = request.form['username'] 
        if 'file' in request.files:
            file = request.files['file']
            game = request.form['game']
            comment = request.form['comment']
            filename = file.filename
            if 'completed' in request.form:
                completed = True
            s3_link = uploadToS3(file)
            createPost(username, file, game, comment, completed)
            return jsonify('post created')
        else:
            return jsonify('missing file')
    except:
        return jsonify('missing data')


@app.route('/autocompleteGames')
@requires_auth
def autoCompleteGames():
    url = constants.IGDB_URL
    user_key = constants.IGDB_KEY
    prefix = request.args.get('term')
    data = f'fields name; where name~"{prefix}"*; limit 50;'
    result = requests.post(url, data=data, headers={'user-key':user_key})
    all_games = result.json()
    games = [game['name'] for game in all_games]
    return jsonify(games)
    
@app.route('/autocompleteTag')
@requires_auth
def autoCompleteTag():
    name = request.args.get('term')
    tag_suggestions = searchUsers(name)
    tag_suggestions = [user['fields']['username'][0] for user in tag_suggestions]
    return jsonify(tag_suggestions)

def createComment(user, text, postID):
    rds_con = pymysql.connect(constants.rds_host, user=constants.rds_user, port=constants.rds_port, passwd=constants.rds_password, db=constants.rds_dbname)
    commentID = str(uuid.uuid4())

    query = f"INSERT INTO COMMENTS (commentID, user, postID, text) VALUES (%s, %s, %s, %s)"

    try:
        with rds_con:
            cur = rds_con.cursor()
            cur.execute(query, (commentID, user, postID, text))
        rds_con.commit()
    except e:
        print(e)

    
    try: 
        query = f"SELECT user from POSTS where postID='{postID}'"
        with rds_con:
            cur = rds_con.cursor()
            cur.execute(query)
        postOwner = cur.fetchone()[0]

        
        if user != postOwner:
            addNotification(postOwner, url_for('viewPost', postid=postID), f"{user} commented on your post")
    except e:
        print(e)

    rds_con.close()

    return commentID

def addNotification(user, link, info):
    notificationID = str(uuid.uuid4())
    query = f"INSERT INTO NOTIFICATIONS (ID, user, link, info) VALUES (%s,%s,%s,%s)"

    rds_con = pymysql.connect(constants.rds_host, user=constants.rds_user, port=constants.rds_port, passwd=constants.rds_password, db=constants.rds_dbname)
    try:
        with rds_con:
            cur = rds_con.cursor()
            vals = (notificationID, user, link, info)
            cur.execute(query, vals) 
        rds_con.commit()
    except e:
        print(e)
    finally:
        rds_con.close()
    
@app.route('/markNotificationsRead', methods=['POST'])
@requires_auth
def markNotificationsRead():
    result = request.form
    notifications = json.loads(request.form['notifications'])
    rds_con = pymysql.connect(constants.rds_host, user=constants.rds_user, port=constants.rds_port, passwd=constants.rds_password, db=constants.rds_dbname)
    for nID in notifications:
        query= f"UPDATE NOTIFICATIONS set read_state=1 where ID='{nID}'"
        try:
            with rds_con:
                cur = rds_con.cursor()
                cur.execute(query)
        except e:
            print(e)
    rds_con.commit()
    rds_con.close()
    return jsonify('success')



@app.route('/getNotifications')
@requires_auth
def getNotifications():
    user = session[constants.PROFILE_KEY]['name']
    since = request.args.get('since', 0)
    result = getNewNotifications(user, since)
    notifications = [Notification(row[0], user, row[1], row[2], row[3].strftime("%Y-%m-%d %H:%M:%S"), row[4]) for row in result]
    return jsonify(notifications) 


def getNewNotifications(user, timestamp):
    query = f"SELECT ID, link, info, createdtime, read_state FROM NOTIFICATIONS where user='{user}' and createdtime > '{timestamp}' ORDER BY createdtime DESC limit 100"
    rds_con = pymysql.connect(constants.rds_host, user=constants.rds_user, port=constants.rds_port, passwd=constants.rds_password, db=constants.rds_dbname)
    try:
        with rds_con:
            cur = rds_con.cursor()
            cur.execute(query)
    finally:
        rds_con.close()

    notifications = cur.fetchall() 
    return notifications

def createTags(postID, tags):
    query = f"INSERT INTO Tags (postID, user) VALUES (%s,%s)"
    tags = list(set(tags))
    rds_con = pymysql.connect(constants.rds_host, user=constants.rds_user, port=constants.rds_port, passwd=constants.rds_password, db=constants.rds_dbname)
    try:
        with rds_con:
            cur = rds_con.cursor()
            for tag in tags:
                vals = (postID, tag) 
                cur.execute(query, vals) 
                addNotification(tag, url_for('viewPost', postid=postID), f"you were tagged in a post!")
        rds_con.commit()
    finally:
        rds_con.close()



def uploadToS3(picture):
    s3 = aws_session.resource('s3')
    bucket = s3.Bucket('gameshots.gg')
    prefix = str(uuid.uuid4())
    filename = picture.filename
    if len(filename) > 100:
        filename = filename[-100:]
    filename = prefix + filename
    bucket.upload_fileobj(picture, filename, ExtraArgs={'ACL':'public-read'})
    link = f'https://s3-us-west-2.amazonaws.com/gameshots.gg/{filename}'
    return link

def createPost(user, link, game, info, completed):
    postID = str(uuid.uuid4())
    slug = createSlug(game)
    comp_val = 0
    query = f"INSERT INTO POSTS (postID, user, picture, game, info, completed, slug) VALUES (%s,%s,%s,%s,%s,%s,%s)"
    if completed:
        comp_val = 1

    
    rds_con = pymysql.connect(constants.rds_host, user=constants.rds_user, port=constants.rds_port, passwd=constants.rds_password, db=constants.rds_dbname)
    try:
        with rds_con:
            cur = rds_con.cursor()
            vals = (postID, user, link, game, info, comp_val, slug)
            cur.execute(query, vals) 
        rds_con.commit()
    finally:
        rds_con.close()

    return postID

@app.route('/settings', methods=['POST', 'GET'])
@requires_auth
def settings():
    username = session[constants.PROFILE_KEY]['name']
    dynamodb = aws_session.resource('dynamodb', region_name='us-west-2')
    table = dynamodb.Table('gg_users');
    displayNames = {}
    getDisplayName(username, displayNames)
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
        updateSearchIndex(username, display_name)
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
    
def allowed_file(filename):
    allowed_extensions = PIC_FILE_TYPES|MOV_FILE_TYPES

    return '.' in filename and \
            filename.rsplit('.', 1)[1].lower() in allowed_extensions 

@app.route('/create', methods=['POST', 'GET'])
@requires_auth
def create():
    username = session[constants.PROFILE_KEY]['name']
    completed = False
    if request.method == 'POST':
        result = request.form
        if request.form['option'] == 'media':
            file = request.files['file']
            if file.filename == '':
                flash('no selected file')
                return redirect(url_for('create'))
            if file and allowed_file(file.filename):
                link = uploadToS3(file)
            else:
                return redirect(url_for('create'))

        elif request.form['option'] == 'twitch': 
            clipSlug = request.form['linkInput']
            link = 'https://clips.twitch.tv/embed?clip='+clipSlug+'&parent=gameshots.gg&parent=ec2-54-188-110-37.us-west-2.compute.amazonaws.com&muted=true';

        else:
            clipSlug = request.form['youtubeLinkInput']
            link = 'https://www.youtube.com/embed/'+clipSlug+'?&autoplay=1&mute=1'
        game = request.form['game']
        comment = request.form['comment']
        if 'completed' in request.form:
            completed = True
        postID = createPost(username, link, game, comment, completed)
        if ('tag0' in request.form) and (request.form['tag0'] != ''):
            tagCount = 0
            tags = []
            curTag = 'tag'+str(tagCount)
            while curTag in request.form:
                if (request.form[curTag] != ''):
                    tags.append(request.form[curTag])
                tagCount+=1
                curTag = 'tag'+str(tagCount)
            if len(tags) > 0:
                createTags(postID, tags) 
        return redirect(url_for('home'))
    return render_template('create.html')

@app.route('/callback')
def callback_handling():
    auth0.authorize_access_token()
    resp = auth0.get('userinfo')
    userinfo = resp.json()

    following, followers, voted, filtered_following, display_name, games_following = getUserInfo(userinfo['name'], userinfo['email'])

    session[constants.JWT_PAYLOAD] = userinfo
    session[constants.PROFILE_KEY] = {
        'user_id': userinfo['sub'],
        'name': userinfo['name'],
        'email': userinfo['email'], 
        'following':following,
        'followers':followers,
        'filtered_following':filtered_following,
        'voted':voted,
        'display_name':display_name,
        'games_following':games_following
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

@app.route('/findGame', methods=['POST'])
@requires_auth
def findGame():
    result = request.form
    try:
        game = request.form['game'] 
        slug = createSlug(game)
        return redirect(url_for('viewGame', game=slug))
    except:
        return None


@app.route('/searchResults', methods=['GET'])
@requires_auth
def searchResults():
    username = session[constants.PROFILE_KEY]['name']
    query = request.args.get('q')
    hits = session['hits']
    return render_template('searchResults.html', search=query, users=hits, screen_name=username)

def searchUsers(user):
    cloudsearch = aws_session.client('cloudsearchdomain', endpoint_url='http://doc-gg-test-6bwc55aehpsty6w5qfiv4pbsmy.us-west-2.cloudsearch.amazonaws.com', region_name='us-west-2')
    response = cloudsearch.search(query=user+'*')
    hits = response['hits']['hit']
    return hits


@app.route('/findFriends', methods=['POST'])
@requires_auth
def findFriends():
    result = request.form
    try:
        name = request.form['username'] 
        hits = searchUsers(name) 
        if len(hits) == 1:
            username = hits[0]['id']
            return redirect(url_for('viewProfile', username=username))
        else:
            session['hits'] = hits
            return redirect(url_for('searchResults', q=name))
    except:
        return None 

def getCoverID(gameSlug):
    url = 'https://api-v3.igdb.com/games/'
    headers = {'user-key':'16fc75eea1a58e7100f4130bddca7967'}
    data = f'fields id; where slug="{gameSlug}";'
    result = requests.post(url, data=data, headers=headers)
    game_id = result.json()[0]['id']
    cover_url = 'https://api-v3.igdb.com/covers'
    data = f'fields image_id; where game={game_id};'
    result = requests.post(cover_url, data=data, headers=headers)
    image_id = result.json()[0]['image_id']
    return image_id



@app.route('/game/<game>', methods=['GET'])
@requires_auth
def viewGame(game):
    games_following = session[constants.PROFILE_KEY]['games_following']
    username = session[constants.PROFILE_KEY]['name']
    #games_following = session[constants.PROFILE_KEY]['games_following']
    try:
        url = 'https://api-v3.igdb.com/games/'
        headers = {'user-key':'16fc75eea1a58e7100f4130bddca7967'}
        data = f'fields *; where slug="{game}";'
        result = requests.post(url, data=data, headers=headers)
        game_id = result.json()[0]['id']
        companies = result.json()[0]['involved_companies']
        summary = result.json()[0]['summary']
        name = result.json()[0]['name']

        cover_url = 'https://api-v3.igdb.com/covers'
        data = f'fields image_id; where game={game_id};'
        result = requests.post(cover_url, data=data, headers=headers)
        image_id = result.json()[0]['image_id']
        image_url = f'http://images.igdb.com/igdb/image/upload/t_cover_big/{image_id}.jpg'

        company_url = 'https://api-v3.igdb.com/companies'
        companies = ','.join(map(str,companies))
        data = f'fields *; where developed=({game_id});';
        result = requests.post(company_url, data=data, headers=headers)
        companies = [x['name'] for x in result.json()]
        companies = ','.join(companies)

    except:
        image_url = 'https://s3-us-west-2.amazonaws.com/gameshots.gg/unkown.jpg'
        companies = 'unknown'
        summary = 'this game does not show up in our database'
        name = game

    posts = getGamePosts(None, game)



    return render_template('game.html', posts=posts, image_url=image_url, companies=companies, summary=summary, name=name, gameSlug=game,
            games_following=games_following, screen_name=username)

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
def viewPost(postid):
    username = None
    voted = []

    if constants.PROFILE_KEY in session:
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
        post = Post(info[0], info[2], info[1], info[3], info[6], info[4].strftime("%Y-%m-%d %H:%M:%S"), postid, [],  info[5], (postid in voted), createSlug(info[2]), display_name, [])

        query = f"SELECT commentID, user, text, createdtime FROM COMMENTS where postID='{postid}' ORDER BY createdtime ASC"
        with rds_con:
            cur = rds_con.cursor()
            cur.execute(query)

        for row in cur.fetchall():
            user = row[1]
            display_name = getDisplayName(user, displayNames)
            post.comments.append(Comment(row[1], row[2], row[3], row[0], getColor(row[1]), display_name))

        query = f"SELECT user FROM Tags where postID='{postid}'"

        with rds_con:
            cur = rds_con.cursor()
            cur.execute(query)

        for row in cur.fetchall():
            user = row[0]
            post.tags.append(user)

    finally:
        rds_con.close()

    gameThumbLink = 'https://s3-us-west-2.amazonaws.com/gameshots.gg/defaultThumb.jpg'

    return render_template('post.html', post=post, screen_name=username, gameThumbnail=gameThumbLink)

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

    addNotification(follow, url_for('viewProfile', username=username), f"{username} followed you!")

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

@requires_auth
@app.route('/followGame', methods=['POST'])
def followGame():
    username = session[constants.PROFILE_KEY]['name']
    follow = request.form['follow']
    dynamodb = aws_session.resource('dynamodb', region_name='us-west-2')
    table = dynamodb.Table('gg_users');
    response = table.update_item(
            Key={'username':username},
            UpdateExpression="SET games_following = list_append(games_following, :i)",
            ExpressionAttributeValues={
                ':i':[follow],
                },
            ReturnValues="UPDATED_NEW"
            )

    session[constants.PROFILE_KEY]['games_following'] = response['Attributes']['games_following']
    #add to followers
    session.modified = True
    return jsonify('success')


@requires_auth
@app.route('/unfollowGame', methods=['POST'])
def unfollowGame():
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
        if 'games_following' in response['Item']:
            games_following = response['Item']['games_following']
            idx = games_following.index(unfollow)

            response = table.update_item(
                    Key={'username':username},
                    UpdateExpression=f"REMOVE games_following[{idx}]",
                    ReturnValues="UPDATED_NEW"
                    )

            response = table.get_item(
                    Key={
                        'username':username
                        }
                    )

            if 'Item' in response:
                if 'games_following' in response['Item']:
                    games_following = response['Item']['games_following']

            session[constants.PROFILE_KEY]['games_following'] = games_following 
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


@app.route('/scrollFeed', methods=['GET'])
def scrollFeed():
    before = request.args.get('before')
    posts = getPosts(before)
    return jsonify(posts)
    

@app.route('/scrollGamesFeed', methods=['GET'])
def scrollGamesFeed():
    before = request.args.get('before')
    posts = getGamePosts(before, None)
    return jsonify(posts)

def feed():
    screen_name = session[constants.PROFILE_KEY]['name']
    following = session[constants.PROFILE_KEY]['following']
    posts = getPosts(None)
    postIDs = [post.id for post in posts]
    return render_template('feed.html', posts=posts, screen_name=screen_name, following=following, earliest=posts[-1].time, postIDs=postIDs, activePage='friendsNav')

@requires_auth
@app.route('/games')
def gameFeed():
    screen_name = session[constants.PROFILE_KEY]['name']
    games_following = session[constants.PROFILE_KEY]['games_following']
    following = session[constants.PROFILE_KEY]['following']
    posts = []
    if len(games_following) > 0:
        posts = getGamePosts(None, None)
        earliest = posts[-1].time
    else:
        earliest = 0
    postIDs = [post.id for post in posts]
    return render_template('gameFeed.html', posts=posts, screen_name=screen_name, games_following=games_following, following=following, earliest=earliest, postIDs=postIDs, activePage='gamesNav')



def getGamePosts(before, game):
    posts = []
    displayNames = {}
    postRefs = {}
    screen_name = session[constants.PROFILE_KEY]['name']
    following = session[constants.PROFILE_KEY]['following']
    voted = session[constants.PROFILE_KEY]['voted']
    if game is None:
        games = session[constants.PROFILE_KEY]['games_following']
    else:
        games = [game]
    placeholder = '%s'
    placeholders = ', '.join(placeholder for game in games)

    query = f"SELECT postID, user, picture, game, info, createdtime, completed, coins FROM POSTS where slug in ({placeholders})"
    if before:
        query += f" AND createdtime <= '{before}'"
    query += " ORDER BY createdtime DESC LIMIT 10"

    rds_con = pymysql.connect(constants.rds_host, user=constants.rds_user, port=constants.rds_port, passwd=constants.rds_password, db=constants.rds_dbname)
    try:
        with rds_con:
            cur = rds_con.cursor()
            cur.execute(query, tuple(games))

        for row in cur.fetchall():
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

            with rds_con:
                cur = rds_con.cursor()
                cur.execute(query, tuple(postRefs.keys()))

            for row in cur.fetchall():
                postID = row[0]
                user = row[2]
                display_name = getDisplayName(user, displayNames)
                comment = Comment(row[2], row[3], row[4], row[1], getColor(row[2]), display_name)
                postRefs[postID].comments.append(comment)

            query = f"SELECT postID, user FROM Tags where postID in ({placeholders})"

            with rds_con:
                cur = rds_con.cursor()
                cur.execute(query, tuple(postRefs.keys()))

            for row in cur.fetchall():
                postID = row[0]
                user = row[1]
                postRefs[postID].tags.append(user)

    finally:
        rds_con.close()

    return posts



    


def getPosts(before):
    posts = []
    postRefs = {}
    screen_name = session[constants.PROFILE_KEY]['name']
    email = session[constants.PROFILE_KEY]['email']
    following = session[constants.PROFILE_KEY]['following']
    filtered_following = session[constants.PROFILE_KEY]['filtered_following']
    voted = session[constants.PROFILE_KEY]['voted']
    users = following+[screen_name]
    placeholder = '%s'
    allParams = []

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
    query += f"SELECT postID, user, picture, game, info, createdtime, completed, coins FROM POSTS where user in ({placeholders})"
    if before:
        query += f" AND createdtime <= '{before}'"
    query += " ORDER BY createdtime DESC LIMIT 10"

    rds_con = pymysql.connect(constants.rds_host, user=constants.rds_user, port=constants.rds_port, passwd=constants.rds_password, db=constants.rds_dbname)
    try:
        with rds_con:
            cur = rds_con.cursor()
            cur.execute(query, tuple(allParams))

        for row in cur.fetchall():
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
            with rds_con:
                cur = rds_con.cursor()
                cur.execute(query, tuple(postRefs.keys()))

            for row in cur.fetchall():
                postID = row[0]
                user = row[2]
                display_name = getDisplayName(user, displayNames)
                comment = Comment(row[2], row[3], row[4], row[1], getColor(row[2]), display_name)
                postRefs[postID].comments.append(comment)

            query = f"SELECT postID, user FROM Tags where postID in ({placeholders})"

            with rds_con:
                cur = rds_con.cursor()
                cur.execute(query, tuple(postRefs.keys()))

            for row in cur.fetchall():
                postID = row[0]
                user = row[1]
                postRefs[postID].tags.append(user)
    finally:
        rds_con.close()

    return posts

if __name__=='__main__':
    #application.run(host='0.0.0.0', port='80', debug=True)
    application.run(host='0.0.0.0', port='443', debug=True, ssl_context='adhoc')

