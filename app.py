from flask import Flask, render_template, request, redirect
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
from werkzeug.security import check_password_hash, generate_password_hash
from models import db, Song, Performance, Show
import itertools

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///setlist.db'
app.config['SECRET_KEY'] = 'your_secret_key'  # Replace with your own secret key
db.init_app(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    # Return the Show object associated with the user_id
    return Show.query.get(int(user_id))

with app.app_context():
    db.create_all()

@app.route('/home', methods=['GET', 'POST'])
@login_required
def home():
    show_id = current_user.id
    songs = get_songs(show_id)
    performances = get_performances(show_id)

    # Rest of the code

    if request.method == 'POST':
        if 'add_song' in request.form:
            song_title = request.form.get('song')
            dancers = request.form.get('dancers').split(',')

            if song_title and all(dancer.strip() for dancer in dancers):
                song = Song(title=song_title, show_id=current_user.id)
                db.session.add(song)
                db.session.flush()

                for dancer in dancers:
                    performance = Performance(song_id=song.id, dancer=dancer.strip())
                    db.session.add(performance)

                db.session.commit()

                success_message = f'Successfully added the song "{song.title}"'
                return render_template('index.html', songs=get_songs(show_id), performances=get_performances(show_id), success=success_message)
        elif 'generate_setlists' in request.form:
            songs = get_songs(show_id)
            if songs:
                performances = get_performances(show_id)
                setlists_with_consecutive_performances = generate_setlists(songs, performances)
                return render_template('result.html', setlists=setlists_with_consecutive_performances)
            else:
                return render_template('index.html', songs=get_songs(show_id), performances=get_performances(show_id), error='No songs added yet.')

    return render_template('index.html', songs=get_songs(show_id), performances=get_performances(show_id))



def generate_setlists(songs, performances):
    all_setlists = list(itertools.permutations(songs, len(songs)))
    setlists_with_consecutive_performances = []

    for setlist in all_setlists:
        consecutive_performances = find_consecutive(performances, setlist)
        setlists_with_consecutive_performances.append((setlist, consecutive_performances))

    sorted_result = sorted(setlists_with_consecutive_performances, key=lambda x: len(x[1]))

    return sorted_result


def find_consecutive(performances, setlist):
    consecutive_performances = []

    for i in range(len(setlist) - 1):
        set_1 = set(performances[setlist[i].id])
        set_2 = set(performances[setlist[i + 1].id])

        if set_1 & set_2:
            consecutive_performances.append((set_1 & set_2, setlist[i]))

    return consecutive_performances


def get_songs(show_id):
    songs = Song.query.filter_by(show_id=show_id).all()
    return songs


def get_performances(show_id):
    performances = {}
    songs = get_songs(show_id)

    for song in songs:
        performances[song.id] = [performance.dancer for performance in song.performances]

    return performances



@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect('/home')

    if request.method == 'POST':
        name = request.form.get('name')
        password = request.form.get('password')

        # Check if the show exists
        show = Show.query.filter_by(name=name).first()

        if show and check_password_hash(show.password, password):
            # Login the show
            login_user(show, remember=True)
            return redirect('/home')


        # Invalid show name or password
        error_message = 'Invalid show name or password'
        return render_template('login.html', error=error_message)

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    # Logout the current show
    logout_user()
    return redirect('/login')

@app.route('/', methods=['GET', 'POST'])
def create_show():
    if current_user.is_authenticated:
        return redirect('/home')

    if request.method == 'POST':
        name = request.form.get('name')
        password = request.form.get('password')

        # Check if the show name is already taken
        existing_show = Show.query.filter_by(name=name).first()
        if existing_show:
            error_message = 'Show name already taken'
            return render_template('create_show.html', error=error_message)

        # Create a new show
        new_show = Show(name=name, password=generate_password_hash(password))
        db.session.add(new_show)
        db.session.commit()

        # Login the new show
        login_user(new_show)

        return redirect('/home')

    return render_template('create_show.html')



if __name__ == '__main__':
    app.run(debug=True)
