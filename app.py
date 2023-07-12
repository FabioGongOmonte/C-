from flask import Flask, render_template, request
import itertools
app = Flask(__name__)

songs = []
performances = {}

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        if 'add_song' in request.form:
            song = request.form.get('song')
            dancers = request.form.get('dancers').split(',')

            if song and dancers:
                songs.append(song)
                performances[song] = dancers
        elif 'generate_setlists' in request.form:
            setlists_with_consecutive_performances = generate_setlists(songs, performances)
            return render_template('result.html', setlists=setlists_with_consecutive_performances)

    return render_template('index.html', songs=songs, performances=performances)


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
        set_1 = set(performances[setlist[i]])
        set_2 = set(performances[setlist[i + 1]])

        if set_1 & set_2:
            consecutive_performances.append((set_1 & set_2, setlist[i]))

    return consecutive_performances

if __name__ == '__main__':
    app.run(debug=True)
