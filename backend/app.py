import io
from tempfile import NamedTemporaryFile
from threading import Thread
import secrets

import jwt
from flask import Flask, request, jsonify, send_file, session, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from ShortsGenerator import generateShorts
from werkzeug.utils import secure_filename
import dotenv, os, datetime
dotenv.load_dotenv()


app = Flask(__name__)
CORS(app, supports_credentials=True)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI')

# async_mode = 'eventlet'
socketio = SocketIO(app, async_mode='threading', cors_allowed_origins="*")
# import eventlet
# eventlet.monkey_patch()


db = SQLAlchemy(app)
app.config['SECRET_KEY'] = "DUPA"
stdiff_api_key=os.getenv("STABLEDIFFUSION_API_KEY")
openai_api_key=os.getenv("OPENAI_API_KEY")
elevenlabs_api_key=os.getenv("ELEVENLABS_API_KEY")

@socketio.on('clip_status')
def handle_message(data):
    print(f"Connected {data}")
    print(session.keys())
    socketio.emit('response', f"HEJ")


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(255), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=False)
    # validation_code = db.Column(db.String(255), unique=True)
    # validation_code_valid_to = db.Column(db.DateTime)
    last_creation = db.Column(db.DateTime)

    def to_json(self):
        json_user = {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'is_active': self.is_active,
            # 'validation_code': self.validation_code,
            # 'validation_code_valid_to': self.validation_code_valid_to.strftime('%Y-%m-%d %H:%M:%S') if self.validation_code_valid_to else None,
            'last_creation': self.last_creation.strftime('%Y-%m-%d %H:%M:%S') if self.validation_code_valid_to else None
        }
        return json_user


class Clip(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    style = db.Column(db.Integer, db.ForeignKey('style.id'), nullable=False)
    theme = db.Column(db.Integer, db.ForeignKey('theme.id'), nullable=False)
    quote = db.Column(db.String(255))
    title = db.Column(db.String(255))
    description = db.Column(db.String(255))
    tags = db.Column(db.String(255))
    clip = db.Column(db.LargeBinary)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, nullable=False)
    status = db.Column(db.Integer, nullable=False, default=0)

    def to_json(self):
        json_clip = {
            'id': self.id,
            'user_id': self.user_id,
            'style': self.style,
            'theme': self.theme,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'status': self.status
        }
        return json_clip


class Style(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False)

    def to_json(self):
        json_style = {
            'id': self.id,
            'name': self.name,
        }
        return json_style


class Theme(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False)

    def to_json(self):
        json_theme = {
            'id': self.id,
            'name': self.name,
        }
        return json_theme


@app.route('/users/register', methods=['POST'])
def register():
    data = request.get_json()

    email = data['email']
    password = data['password']
    username = data['username']
    print(data)

    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return jsonify({"message": "Email already exists"}), 400

    # validation_code = generate_validation_code(length=16)

    new_user = User(
        email=email,
        username=username,
        password=password,
        # validation_code_valid_to=datetime.datetime.utcnow() + datetime.timedelta(hours=2),
        is_active=True,
        # validation_code=validation_code,
    )
    # print("VALIDATION CODE", validation_code)
    try:
        db.session.add(new_user)
        db.session.commit()
        return jsonify({"message": "User created successfully"}), 201
    except:
        db.session.rollback()
        return jsonify({"message": "Failed to create user"}), 500

@app.route('/users/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email', None)
    password = data.get('password', None)

    if not email or not password:
        return jsonify({'message': 'Username and password are required'}), 400

    user = User.query.filter_by(email=email, password=password).first()

    if not user:
        return jsonify({'message': 'Invalid credentials'}), 401

    # Create a JWT token
    expiration = datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    token = jwt.encode({'user': user.email, 'id': user.id, 'exp': expiration}, app.config['SECRET_KEY'], algorithm='HS256')

    # Set the token in a cookie
    response = make_response(jsonify({'message': 'Login successful'}))
    response.set_cookie('access_token', value=token, expires=expiration, httponly=True)
    print(token)
    return response


@app.route('/validate/<string:validationCode>', methods=['GET'])
def validate(validationCode):
    # data = request.get_json()
    # user_email = data['email']

    user = User.query.filter_by(validation_code=validationCode).first()

    if user:
        if user.validation_code_valid_to and user.validation_code_valid_to >= datetime.datetime.utcnow():
            user.is_active = True
            user.validation_code = None
            user.validation_code_valid_to = None
            db.session.commit()
            return jsonify({"message": "User validated successfully"}), 200
        else:
            return jsonify({"message": "Validation code has expired"}), 400
    else:
        return jsonify({"message": "Invalid email or validation code"}), 400

def generate_token():
    return secrets.token_urlsafe(16)

token_database = {}

def is_valid_token(token):
    if token in token_database:
        expiration_time = token_database[token]
        return datetime.datetime.utcnow() < expiration_time
    return False

@app.route('/generate_video_link')
def generate_video_link():
    token = generate_token()
    expiration_time = datetime.datetime.now() + datetime.timedelta(hours=24)
    token_database[token] = expiration_time
    return {'video_link': f'/get_video/{token}'}

@app.route('/clips/<int:clipId>', methods=['GET'])
def getClip(clipId):
    # token = request.cookies.get('access_token')
    # print(token)
    # decoded_token = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
    # userId = decoded_token['id']
    userId = 1

    user = User.query.get(userId)

    if user is None:
        return jsonify({"message": "User not found"}), 404

    clip = Clip.query.get(clipId)
    if clip:
        return send_file(io.BytesIO(clip.clip), mimetype='video/mp4')
    else:
        return jsonify({"error": "Video not found"})

@app.route('/clips', methods=['GET', 'POST', 'DELETE'])
def clip():
    # token = request.cookies.get('access_token')
    # decoded_token = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
    # userId = decoded_token['id']
    userId = 1
    user = User.query.get(userId)
    print(userId)

    if user is None:
        return jsonify({"message": "User not found"}), 404

    if request.method == "GET":
        clipId = request.args.get('clipId')
        if clipId:
            clip = Clip.query.filter_by(clip_id=clipId, user_id=userId).first()
            return jsonify({"clip": clip.to_json()})
        else:
            clips = Clip.query.filter_by(user_id=userId).all()
            clips_list = [clip.to_json() for clip in clips]
            return jsonify({"clips": clips_list}), 200

    elif request.method == "POST":
        data = request.get_json()

        style = data['style']
        theme = data['theme']
        quote = data['quote']

        style_obj = Style.query.get(style)
        print(style_obj)
        theme_obj = Theme.query.get(theme)

        if style_obj is None:
            return jsonify({"message": "Style not found"}), 404

        if theme_obj is None:
            return jsonify({"message": "Theme not found"}), 404
        # socketio.start_background_task(target=lambda: createShort(userId, style, theme, quote, socketio))
        thread = Thread(target=createShort, args=(userId, style, theme, quote, socketio))
        thread.start()

        return jsonify({"message": "Clip creation started"}), 201

    elif request.method == "DELETE":
        clipId = request.args.get('clipId')
        clip = Clip.query.get(clipId)
        if clip is None:
            return jsonify({"message": "Clip not found"}), 404

        db.session.delete(clip)
        db.session.commit()
        return jsonify({"message": "Clip deleted successfully"})


def createShort(userId, style, theme, quote, socketio):
    with app.app_context():
        socketio.emit("clip_status", {"status": 10})
        new_clip = Clip(
            user_id=userId,
            style=style,
            theme=theme,
        )

        db.session.add(new_clip)
        db.session.commit()
        filename = f"{userId}-{new_clip.id}-{style}-{theme}.mp4"
        theme_name = Theme.query.get(theme).name
        style_name = Style.query.get(style).name
        try:
            clip, details = generateShorts(stdiff_api_key=stdiff_api_key, openai_api_key=openai_api_key, elevenlabs_api_key=elevenlabs_api_key, quote=quote, style=style_name, theme=theme_name, socketio=socketio)
            with open(filename, "wb"):
                clip.write_videofile(filename, codec="libx264", fps=24)

                with open(filename, "rb") as mp4_file:
                    mp4_binary = mp4_file.read()
                    new_clip.clip = mp4_binary
                    new_clip.status = 1
                    new_clip.title = details['title']
                    new_clip.description = details['description']
                    new_clip.tags = details['tags']

                    db.session.commit()
                socketio.emit("clip_status", {"status": 100, "clip": new_clip.to_json()})

            os.remove(filename)

        except Exception as e:
            print(e)
            os.remove(filename)
            new_clip.status = 2
            db.session.commit()


def generate_validation_code(length=8):
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    validation_code = ''.join(secrets.choice(alphabet) for _ in range(length))
    return validation_code


if __name__ == '__main__':
    context = (os.getenv('CERT'), os.getenv('DECRYPTED_KEY'))

    with app.app_context():
        db.create_all()
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True, host='0.0.0.0', ssl_context=context)
