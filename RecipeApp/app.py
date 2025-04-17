from flask import Flask,
render_template, request, redirect
from flask_mysqldb import MySQL

app = Flask(__name__)

app.config['MYSQL_HOST']= 'localhost'
app.config['MYSQL_USER']= 'root'
app.config['MYSQL_PASSWORD']= 'AishiKitchenStory'
app.config['MYSQL_DB']= 'recipe_db'

mysql= MySQL(app)

@app.route('/')
def home():
    return "Welcome to Kitchen Story!"
if __name__=='__main__':
    app.run(debug-True)
    