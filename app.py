from flask import Flask, render_template, request, redirect, jsonify
from sqlalchemy.exc import SQLAlchemyError
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
from werkzeug.security import check_password_hash, generate_password_hash
from models import db, Song, Performance, Show
import itertools

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://setgen_user:MHTBLcG27UxVfgYooX409nhdLog9yqOb@dpg-cip2145gkuvrtob80nrg-a.ohio-postgres.render.com/setgen"
app.config['SECRET_KEY'] = 'qwertyuiop'  # Replace with your own secret key
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
def home():
    if not current_user.is_authenticated:
        return redirect('/')
    show_id = current_user.id
    show_name = Show.query.get(int(show_id)).name

    if request.method == 'POST':
        if 'generate_setlists' in request.form:
            songs = get_songs(show_id)
            if songs:
                performances = get_performances(show_id)
                setlists_with_consecutive_performances = generate_setlists(songs, performances)
                return render_template('result.html', setlists=setlists_with_consecutive_performances)
            else:
                return render_template('index.html', songs=get_songs(show_id), performances=get_performances(show_id), error='No songs added yet.', show = show_name)

        elif 'add_song' in request.form:
            song_title = request.form.get('song')
            dancers = request.form.get('dancers').split(',')

            if song_title and all(dancer.strip() for dancer in dancers):
                # Check if the song title already exists for the show
                existing_song = Song.query.filter_by(show_id=show_id, title=song_title).first()
                if existing_song:
                    error_message = f'A song with the title "{song_title}" already exists.'
                    return render_template('index.html', songs=get_songs(show_id), performances=get_performances(show_id), error=error_message, show = show_name)

                song = Song(title=song_title, show_id=show_id)
                db.session.add(song)
                db.session.flush()

                for dancer in dancers:
                    performance = Performance(song_title=song_title, dancer=dancer.strip())
                    db.session.add(performance)

                db.session.commit()
                return redirect(f'/home')  # Redirect to home 

    return render_template('index.html', songs=get_songs(show_id), performances=get_performances(show_id), show = show_name)


@app.route('/delete-song/<song_title>', methods=['POST'])
@login_required
def delete_song(song_title):
    show_id = current_user.id
    song = Song.query.filter_by(title=song_title, show_id=show_id).first()

    if song:
        try:
            # Delete performances associated with the song
            performances = Performance.query.filter_by(song_title=song.title).all()
            for performance in performances:
                db.session.delete(performance)

            # Delete the song
            db.session.delete(song)
            db.session.commit()
            return redirect(f'/home') 
        except SQLAlchemyError as e:
            db.session.rollback()
            return redirect(f'/home')
    else:
        error_message = 'Song not found'
        return redirect(f'/home')





def generate_setlists(songs, performances):
    all_setlists = list(itertools.permutations(songs, len(songs)))
    setlists_with_consecutive_performances = []

    for setlist in all_setlists:
        consecutive_performances = find_consecutive(performances, setlist)
        setlists_with_consecutive_performances.append((setlist, consecutive_performances))

    sorted_result = sorted(setlists_with_consecutive_performances, key=lambda x: (
        len(x[1]), (sum(len(dancers) for dancers, _ in x[1])))
    )

    top_20_setlists = sorted_result[:20]

    return top_20_setlists


def find_consecutive(performances, setlist):
    consecutive_performances = []

    for i in range(len(setlist) - 1):
        set_1 = set(performances[setlist[i].title])
        set_2 = set(performances[setlist[i + 1].title])

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
        performances[song.title] = [performance.dancer for performance in song.performances]

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
