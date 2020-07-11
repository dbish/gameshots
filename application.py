from flask import Flask, render_template, redirect, url_for, jsonify, session, flash, request
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

Post = collections.namedtuple("Post", ['username', 'game', 'image', 'editorial', 'coins', 'time', 'id', 'comments', 'completed', 'voted', 'gameNormalized'])
Comment = collections.namedtuple("Comment", ['username', 'text', 'time', 'id'])

UPLOAD_FOLDER = "/tmp"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER



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


rds_con = pymysql.connect(constants.rds_host, user=constants.rds_user, port=constants.rds_port, passwd=constants.rds_password, db=constants.rds_dbname)
rds_con.autocommit(True)

def getUserInfo(username, email):
    dynamodb = aws_session.resource('dynamodb', region_name='us-west-2')
    following = []
    followers = []
    table = dynamodb.Table('gg_users');
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
        if 'voted' in response['Item']:
            voted = response['Item']['voted']
    else:
        response = table.put_item(
                Item={
                    'username':username,
                    'email':email,
                    'following':[],
                    'followers':[],
                    'voted':[]
                    }
                )
        flash('Welcome! New gameshots account created. Find some friends and share some great game memories :)')
    return following, followers, voted

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if constants.PROFILE_KEY not in session:
            return redirect('/login')
        return f(*args, **kwargs)

    return decorated

def createComment(user, text, postID):
    commentID = str(uuid.uuid4())

    query = f"INSERT INTO COMMENTS (commentID, user, postID, text) VALUES (%s, %s, %s, %s)"


    with rds_con:
        cur = rds_con.cursor()
        cur.execute(query, (commentID, user, postID, text))

    return commentID


def createPost(user, picture, game, info, completed):
    postID = str(uuid.uuid4())
    #upload to S3 and get link
    s3 = aws_session.resource('s3')
    bucket = s3.Bucket('gameshots.gg')
    bucket.upload_fileobj(picture, user+picture.filename, ExtraArgs={'ACL':'public-read'})
    s3_link = f'https://s3-us-west-2.amazonaws.com/gameshots.gg/{user}{picture.filename}'
    comp_val = 0
    query = f"INSERT INTO POSTS (postID, user, picture, game, info, completed) VALUES (%s,%s,%s,%s,%s,%s)"
    if completed:
        comp_val = 1
    with rds_con:
        cur = rds_con.cursor()
        vals = (postID, user, s3_link, game, info, comp_val)
        cur.execute(query, (postID, user, s3_link, game, info, comp_val))
    
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

    following, followers, voted = getUserInfo(userinfo['name'], userinfo['email'])

    session[constants.JWT_PAYLOAD] = userinfo
    session[constants.PROFILE_KEY] = {
        'user_id': userinfo['sub'],
        'name': userinfo['name'],
        'email': userinfo['email'], 
        'following':following,
        'followers':followers,
        'voted':voted
    }
    return redirect('/')

def getUserGames(username):
    query = f"SELECT DISTINCT game FROM POSTS where user='{username}'"
    games = []

    with rds_con:
        cur = rds_con.cursor()
        cur.execute(query)

    game_info = cur.fetchall()
    games = [game[0] for game in game_info]

    query = f"SELECT DISTINCT game FROM POSTS where user='{username}' and completed=1"

    with rds_con:
        cur = rds_con.cursor()
        cur.execute(query)

    completed_games = cur.fetchall() 
    completed_games = [game[0] for game in completed_games]

    return games, completed_games 

def getUserThumbnails(username):
    query = f"SELECT postID, picture, completed FROM POSTS where user='{username}' ORDER BY createdtime DESC"
    posts = []

    with rds_con:
        cur = rds_con.cursor()
        cur.execute(query)

    for row in cur.fetchall():
        posts.append((row[0], row[1], row[2])) 

    return posts

@app.route('/gamer/<username>')
@requires_auth
def viewProfile(username):
    games, completed_games = getUserGames(username)
    posts = getUserThumbnails(username)
    following = session[constants.PROFILE_KEY]['following']
    followers = session[constants.PROFILE_KEY]['followers']
    profile_following, profile_followers, x = getUserInfo(username, "placeholder")
    myusername = session[constants.PROFILE_KEY]['name']
    return render_template('profile.html', screen_name=myusername, username=username, games=games, posts=posts, following=following, followers=followers, myusername=myusername, profile_following=profile_following, profile_followers=profile_followers, completed_games=completed_games) 

@app.route('/post/<postid>')
@requires_auth
def viewPost(postid):
    username = session[constants.PROFILE_KEY]['name']
    voted = session[constants.PROFILE_KEY]['voted']

    query = f"SELECT user, picture, game, info, createdtime, completed, coins FROM POSTS where postid='{postid}'"

    with rds_con:
        cur = rds_con.cursor()
        cur.execute(query)

    info = cur.fetchone()
    post = Post(info[0], info[2], info[1], info[3], info[6], info[4], postid, [], info[5], (postid in voted), normalize(info[2]))

    query = f"SELECT commentID, user, text, createdtime FROM COMMENTS where postID='{postid}' ORDER BY createdtime ASC"
    with rds_con:
        cur = rds_con.cursor()
        cur.execute(query)

    for row in cur.fetchall():
        post.comments.append(Comment(row[1], row[2], row[3], row[0]))

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
    with rds_con:
        cur = rds_con.cursor()
        cur.execute(query)
        owner = cur.fetchone()[0]
        if owner == username:
            query = f"DELETE FROM COMMENTS where commentID='{commentID}'"
            cur.execute(query)
    
        return jsonify("success")

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
        query= f"UPDATE POSTS set coins=coins+1 where postID=%s"
        with rds_con:
            cur = rds_con.cursor()
            cur.execute(query, (postID))


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
        with rds_con:
            cur = rds_con.cursor()
            cur.execute(query, (postID))

        voted.remove(postID)
        session.modified = True
        return jsonify('success')
    return jsonify('cannot downvote something that was not upvoted')


@requires_auth
@app.route('/deletePost/<postID>', methods=['POST'])
def deletePost(postID):
    username = session[constants.PROFILE_KEY]['name']

    query= f"SELECT user from POSTS where postID='{postID}'"
    with rds_con:
        cur = rds_con.cursor()
        cur.execute(query)
        owner = cur.fetchone()[0]
        if owner == username:
            query = f"DELETE FROM POSTS where postID='{postID}'"
            cur.execute(query)
            query = f"DELETE FROM COMMENTS where postID='{postID}'"
            cur.execute(query)
    
    return redirect(url_for('home'))


def normalize(game):
    game = game.replace(":", "_")
    return game.replace(" ", "_")

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

            x, followers, y = getUserInfo(unfollow, 'placeholder')
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




@app.route('/')
def home():
    if constants.PROFILE_KEY not in session:
        return render_template('index.html')
    else:
        return feed()

def feed():
    posts = []
    postRefs = {}
    screen_name = session[constants.PROFILE_KEY]['name']
    email = session[constants.PROFILE_KEY]['email']
    #following = getUserInfo(screen_name, email)
    following = session[constants.PROFILE_KEY]['following']
    voted = session[constants.PROFILE_KEY]['voted']
    users = following+[screen_name]
    placeholder = '%s'
    placeholders = ', '.join(placeholder for unused in users)
    games = set()
    query = f"SELECT postID, user, picture, game, info, createdtime, completed, coins FROM POSTS where user in ({placeholders}) ORDER BY createdtime DESC"

    with rds_con:
        cur = rds_con.cursor()
        cur.execute(query, tuple(users))

    for row in cur.fetchall():
        postID = row[0]
        game = row[3]
        games.add(game)
        newPost = Post(row[1], game, row[2], row[4], row[7], row[5], postID, [], row[6], (postID in voted), normalize(game))
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
            comment = Comment(row[2], row[3], row[4], row[1])
            postRefs[postID].comments.append(comment)

    return render_template('feed.html', posts=posts, screen_name=screen_name, games=games)


if __name__=='__main__':
    application.run(host='0.0.0.0', port='80', debug=True)

