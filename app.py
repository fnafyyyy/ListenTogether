from flask import Flask, request, render_template, redirect, url_for, session, send_from_directory
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS
from werkzeug.utils import secure_filename
from uuid import UUID
import os
import uuid

app = Flask(__name__)
CORS(app)
app.secret_key = 'f3cfe9ed8fae309f02079dbf'
app.config['UPLOAD_FOLDER'] = 'uploads'  # Folder do przesyłania plików
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Maksymalny rozmiar pliku: 16MB

socketio = SocketIO(app)

rooms = {}

# Przenieść dodoawnaie plików do pokoju
# autoodtwarzanie koljenych utworów na liście 
# delay około 1 sekundy na timestampie przy dołączaniu do istniejącego pokoju

ALLOWED_EXTENSIONS = {'mp3', 'wav'}  

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_room_code():
    return uuid.uuid4()

def create_room():
    room = generate_room_code()
    rooms[room] = {"members": 0, "room_dir": '', "files": [], "file_id": 0, "timestamp": 0}
    session["room"] = room
    return room

@app.route('/')
def index():
    message = session.pop('error', 'no file chosen')
    # Dodaj stan obecności innych użytkowników w pokoju
    return render_template('index.html', file_name=message, rooms = rooms)

@app.route('/uploads', methods=['POST'])
def upload_files():
    files = request.files.getlist('files')
    filenames = []

    for file in files:
        if file.filename == '':
            return redirect(request.url)
        
        if not file or not allowed_file(file.filename):
            session['error'] = 'Invalid file type'
            return redirect(url_for('index'))

    room_id = create_room()

    room_dir = os.path.join(app.config['UPLOAD_FOLDER'], str(room_id))

    os.mkdir(room_dir)

    for file in files:    
        filename = secure_filename(file.filename)
        filepath = os.path.join(room_dir, filename)
        file.save(filepath)
        filenames.append(filename)
    
    rooms[room_id]['files'] = filenames
    rooms[room_id]['room_dir'] = room_dir

    return redirect(url_for('room', room_id=room_id))
    
@app.route('/room/<room_id>')
def room(room_id):
    room = session.get('room')

    if room is None or room not in rooms:
        return redirect(url_for('index'))

    return render_template('room.html', id=room_id)

@app.route('/join/<room_id>')
def join(room_id):
   
    try:
        room_uuid = UUID(room_id)
    except ValueError:
        session['error'] = 'Invalid room ID'
        return redirect(url_for('index'))

    if room_uuid not in rooms:
        session['error'] = 'Room doesnt exist'
        return redirect(url_for('index'))

    session['room'] = room_uuid
    return redirect(url_for('room', room_id=room_id))

@socketio.on('connect')
def on_connect():
    room = session.get('room', False)

    if not room:
        return
    if room not in rooms:
        leave_room(room)
        return
    
    join_room(room)
    rooms[room]['members'] += 1

    emit('update_users', rooms[room]['members'], to=room)
    emit('getTime', include_self=False, to=room)

@socketio.on('disconnect')
def on_disconnect():
    room = session.get('room')
    leave_room(room)
    if room in rooms:
        rooms[room]['members'] -= 1
        emit('update_users', rooms[room]['members'], to=room)

    if rooms[room]['members'] <= 0:
        for file in rooms[room]['files']:
            if file:
                filepath = os.path.join(rooms[room]['room_dir'], file)
                os.remove(filepath)
        os.rmdir(rooms[room]['room_dir'])
        del rooms[room]


@app.route('/uploads/<path:filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@socketio.on('files_request')
def send_files():
    room = session.get('room', None)
    if room:
        emit('requested_files',{'room_dir': rooms[room]['room_dir'], 'files':rooms[room]['files'],"file_id":rooms[room]['file_id'],"timestamp":rooms[room]['timestamp']})

@socketio.on('play_music')
def play_music():
    room = session.get('room', None)
    if room:
        emit('play', to=room)

@socketio.on('stop_music')
def stop_music():
    room = session.get('room', None)
    if room:
        emit('stop', to=room)

@socketio.on('reset')
def reset():
    room = session.get('room', None)
    if room:
        emit('reset', to=room)

@socketio.on('changeAudio')
def changeAudio(id):
    room = session.get('room', None)
    if room:
        rooms[room]['file_id'] = id
        emit('changeAudio',id,to=room)

@socketio.on('requestedTime')
def setTimestamp(time):
    room = session.get('room', None)
    if room:
        rooms[room]['timestamp'] = time

socketio.run(app, debug=True)
