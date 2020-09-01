from flask import Flask, render_template
app = Flask(__name__)

@app.route('/')
def conectar():
    v1, v2, v3 = 1, 2, 3
    return render_template('index.html', v1 = v1, v2 = v2, v3 = v3)
    

if __name__ == '__main__':

    # Local deployment
    app.run(host='127.0.0.1', port=8080, debug=True)
