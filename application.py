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

AUTH0_CALLBACK_URL = constants.AUTH0_CALLBACK_URL
AUTH0_CLIENT_ID = constants.AUTH0_CLIENT_ID
AUTH0_CLIENT_SECRET = constants.AUTH0_CLIENT_SECRET
AUTH0_DOMAIN = constants.AUTH0_DOMAIN
print(constants.AUTH0_DOMAIN)
print(AUTH0_DOMAIN)
AUTH0_BASE_URL = 'https://' + AUTH0_DOMAIN
AUTH0_AUDIENCE = constants.AUTH0_AUDIENCE



application = Flask(__name__)
SECRET_KEY = os.urandom(32)
application.config['SECRET_KEY'] = SECRET_KEY
app = application

Post = collections.namedtuple("Post", ['username', 'game', 'image', 'editorial', 'coins', 'time'])

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
    table = dynamodb.Table('gg_users');
    response = table.get_item(
            Key={
                'username':username
                }
            )

    if 'Item' in response:
        if 'following' in response['Item']:
            following = response['Item']['following']
    else:
        response = table.put_item(
                Item={
                    'username':username,
                    'email':email
                    }
                )
        flash('Welcome! New gameshots account created. Find some friends and share some great game memories :)')
    return following

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if constants.PROFILE_KEY not in session:
            return redirect('/login')
        return f(*args, **kwargs)

    return decorated

def createPost(user, picture):

    #upload to S3 and get link
    s3 = aws_session.resource('s3')
    bucket = s3.Bucket('gameshots.gg')
    bucket.upload_fileobj(picture, user+picture.filename, ExtraArgs={'ACL':'public-read'})
    s3_link = f'https://s3-us-west-2.amazonaws.com/gameshots.gg/{user}{picture.filename}'
    query = f"INSERT INTO POSTS (user, picture) VALUES ('{user}', '{s3_link}')"

    with rds_con:
        cur = rds_con.cursor()
        cur.execute(query)
    
@app.route('/create', methods=['POST', 'GET'])
@requires_auth
def create():
    username = session[constants.PROFILE_KEY]['name']
    if request.method == 'POST':
        result = request.form
        print(request.files)
        print(request)
        print(result)
        if 'file' in request.files:
            file = request.files['file']
            filename = file.filename
            createPost(username, file)
            #file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return redirect(url_for('feed'))
    return render_template('create.html')

@app.route('/callback')
def callback_handling():
    auth0.authorize_access_token()
    resp = auth0.get('userinfo')
    userinfo = resp.json()
    print(userinfo)

    session[constants.JWT_PAYLOAD] = userinfo
    session[constants.PROFILE_KEY] = {
        'user_id': userinfo['sub'],
        'name': userinfo['name'],
        'email': userinfo['email']
    }
    return redirect('/feed')


@app.route('/login')
def login():
    return auth0.authorize_redirect(redirect_uri=AUTH0_CALLBACK_URL)


@app.route('/logout')
def logout():
    session.clear()
    params = {'returnTo': url_for('home', _external=True), 'client_id': AUTH0_CLIENT_ID}
    return redirect(auth0.api_base_url + '/v2/logout?' + urlencode(params))


@app.route('/')
def home():
    return render_template('index.html')

@app.route('/feed')
@requires_auth
def feed():
    posts = []
    screen_name = session[constants.PROFILE_KEY]['name']
    email = session[constants.PROFILE_KEY]['email']
    following = getUserInfo(screen_name, email)
    print(screen_name)
    
    query = f"SELECT * FROM POSTS where user='{screen_name}'"

    with rds_con:
        cur = rds_con.cursor()
        cur.execute(query)

    for row in cur.fetchall():
        posts.append(Post(row[1], 'GamePlaceholder', row[2], 'text placeholder', 42, 'T2310PST'))
    return render_template('feed.html', posts=posts, screen_name=screen_name)

@app.route('/profile')
def profile():
    screen_name = 'bishopofcode'
    return render_template('profile.html', screen_name=screen_name)

if __name__=='__main__':
    print('running')
    application.run(host='0.0.0.0', port='80')

