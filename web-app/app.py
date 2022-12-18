from flask import Flask, render_template, request, redirect, url_for, make_response, flash
from bson.objectid import ObjectId
from dotenv import dotenv_values
from utils import *

import pymongo
import datetime

# instantiate the app
app = Flask(__name__, static_url_path='/static')
app.secret_key = 'secret'  # Change this!

# modules for user authentication
import flask
import flask_login
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash

#set up flask-login for user authentication
login_manager = flask_login.LoginManager()
login_manager.init_app(app)

config = dotenv_values(".env")

config = dotenv_values(".env")

# turn on debugging if in development mode
if config['FLASK_ENV'] == 'development':
    # turn on debugging, if in development
    app.debug = True # debug mnode

# connect to the database
cxn = pymongo.MongoClient(config['MONGO_URI'], serverSelectionTimeoutMS=5000)
try:
    # verify the connection works by pinging the database
    cxn.admin.command('ping') # The ping command is cheap and does not require auth.
    db = cxn[config['MONGO_DBNAME']] # store a reference to the database
    print(' *', 'Connected to MongoDB!') # if we get here, the connection worked!
except Exception as e:
    # the ping command failed, so the connection is not available.
    # render_template('error.html', error=e) # render the edit template
    print(' *', "Failed to connect to MongoDB at", config['MONGO_URI'])
    print('Database connection error:', e) # debug

# class to represent user
class User(flask_login.UserMixin):
    def __init__(self,data):
        self.id = data['_id'] # shortcut to _id field
        self.username = data['username']
        self.favorite_apt = data['favorite_apt']
        self.data = data # all user 

def locate_user(user_id=None, username=None):
    '''
    Return a User object for the user with the given id or email address, or None if no such user exists.
    @param user_id: the user_id of the user to locate
    @param email: the email address of the user to locate
    '''
    if user_id:
        criteria = {"_id":ObjectId(user_id)}
    else:
        criteria = {"username":username}
    
    doc = db.users.find_one(criteria) # find user w/ this email
    # if user exists, create user object and return
    if doc:
        user = User(doc)
        return user
    #else
    return None

@login_manager.user_loader
def user_loader(user_id):
    #   This function is called automatically by flask-login with every request the browser makes to the server.
    return locate_user(user_id=user_id)

# make the currently-logged-in user, if any, available to all templates as 'user'
@app.context_processor
def inject_user():
    # print(flask_login.current_user)
    return dict(user=flask_login.current_user)

userId = "6351acad640dc9083d534403"


# set up the routes

# route for the home page
@app.route('/')
def home():
    """
    Route for the home page before login
    """
    if flask_login.current_user.is_authenticated:
        return render_template('user_home.html', username=flask_login.current_user.data['username'])
    return render_template('guest_home.html')
        
	
####################
# login and register
####################

@app.route('/login',methods=['GET'])
def login():
    if (flask_login.current_user.is_authenticated):
        flash('You are already logged in!')
        return redirect(url_for('home'))
    return render_template('login.html', error='')


@app.route('/login',methods=['POST'])
def login_submit():
    username = request.form['username']
    password = request.form['password']
    user = locate_user(username=username)
    print(user)
    if user and check_password_hash(user.data['password'],password):
        flask_login.login_user(user)
        flash('Welcome back!')
        return redirect(url_for('home'))
    return render_template('login.html', error = 'Wrong Password')

@app.route('/logout')
def logout():
    flask_login.logout_user()
    flash('You have been logged out.  Bye bye!')
    return redirect(url_for('login'))

@app.route('/register', methods=['POST', 'GET'])
def register():
    if (flask_login.current_user.is_authenticated):
        flash('You are already logged in!')
        return redirect(url_for('home'))
    if request.method == 'GET':
        return render_template('register.html')
    else:
        username = request.form.get('username')
        password = request.form.get('password')
        password = generate_password_hash(password)
        email = request.form.get('email')
        if locate_user(username=username):
            return render_template('register.html', error='User already exists!')
        elif len(username) >= 50:
            return render_template('register.html', error='Please enter a valid username!')
        elif len(email) >= 50 or len(email.split("@")) != 2:
            return render_template('register.html', error='Please enter a valid username!')
        else:
            # md5_pass = md5(password.encode('utf-8')).hexdigest()
            # new_id = mt.root_new_user_gen_id(user='root')

            user = {
                "username": username,
                "password": password,
                "email": email,
                "favorite_apt": [],
                }
            user_id = db.users.insert_one(user).inserted_id
            # user = db.users.findOne({"username": username})      
            return redirect(url_for('login'))

@app.route('/apartments/', methods=['GET'])
def apartments():
    return render_template('apartments.html')

@app.route('/apartments/<address_id>', methods = ['GET','POST'])
def viewApartment(address_id):
    # apartment = db.apartments.find_one({'_id': address_id})
    apartment = db.apartments.find({})[0]
    if (apartment ==None):
        return redirect(url_for('home'))
    # apartment = {
    #     "_id": "1",
    #     "price": 10000,
    #     "name": "The Octagon",
    #     "address": "888 Main St",
    #     "borough": "Roosevelt Island",
    #     "photo":"https://thumbs.cityrealty.com/assets/smart/736x/webp/9/97/9788674e147c90430c2beb67a1ec17e6297df3af/octagon-rotunda.jpg",
    #     "year_of_construction": 2001,
    #     "pet_friendly": True,
    #     "doorman": False,
    #     "gym": True,
    #     "parking": False,
    #     "elevator": True,
    #     "laundry_in_building": True
    # }
    rating = 3
    # login = True
    # like = True
    login = False    
    like = False
    if (flask_login.current_user.is_authenticated):
        login = True
        if apartment['_id'] in flask_login.current_user.favorite_apt:
            like = True
    if request.method == 'POST':
        li = flask_login.current_user.favorite_apt
        if (like):
            li.remove(apartment['_id'])
        else:
            li.append(apartment['_id'])
        doc = {
            "favorite_apt":  li, 
        }
        db.users.update_one(
            {"_id": ObjectId(flask_login.current_user.data['_id'])}, # match criteria
            { "$set": doc }
        )
        like = not like
    reviews = db.reviews.find({'address_id': address_id})
    return render_template('single_apartment.html', apartment = apartment, address_id=address_id, reviews=reviews, rating = rating, login = login, like = like)

@app.route('/reviews/<address_id>', methods = ['GET'])
def reviews(address_id):
    reviews = db.reviews.find({'address_id': address_id})
    print(reviews, flush=True)
    return render_template('reviews.html', reviews=reviews, address_id=address_id)


@app.route('/add_review/<address_id>', methods=['GET','POST'])
def add_review(address_id):
    if (not flask_login.current_user.is_authenticated):
        return redirect(url_for('viewApartment',  address_id=address_id))
    if request.method == 'GET':
        return render_template('add_review.html', address_id=address_id)
    else: 
        # create a new review with the data the user entered
        review = {
            "comments": request.form.get('comments'),
            "rating": request.form.get('rating',type=int), 
            "price": request.form.get('price'),
            "added_at": datetime.datetime.utcnow(),
            "address_id": address_id,
            "user_id": ObjectId(flask_login.current_user.data['_id']),
        }
        db.reviews.insert_one(review) # insert a new review
        return redirect(url_for('viewApartment',  address_id=address_id))



@app.route('/account', methods = ['GET'])
#default view of account
def account_favorites():
    if not flask_login.current_user.is_authenticated:
        return render_template('guest_home.html')
    # docs = flask_login.current_user.favorite_apt
    doc = db.users.find_one({"_id": ObjectId(flask_login.current_user.data['_id'])})
    apt_ids = doc['favorite_apt']
    docs=[]
    for apt in apt_ids:
        add = db.apartments.find_one({"_id":ObjectId(apt)})
        docs.append(add)
    return render_template('account_favorites.html',docs=docs, user=flask_login.current_user.data)

@app.route('/account/reviews', methods = ['GET'])
def account_reviews():
    if not flask_login.current_user.is_authenticated:
        return render_template('guest_home.html')
    docs = db.reviews.find({"user_id":ObjectId(flask_login.current_user.data['_id'])})
    user = db.users.find_one({"_id":ObjectId(flask_login.current_user.data['_id'])})
    docs2 = []
    for doc in docs:
        apt_id = doc["address_id"]
        apt = db.apartments.find_one({"_id": ObjectId(apt_id)})
        doc.update({"apt_name":apt['name']})
        doc.update({"apt_address" : apt['address']})
        docs2.append(doc)
    return render_template('account_reviews.html',docs = docs2, user = user)

# run the app
if __name__ == "__main__":
	app.run()


# # load credentials and configuration options from .env file
# # if you do not yet have a file named .env, make one based on the template in env.example
# config = dotenv_values(".env")

# # turn on debugging if in development mode
# if config['FLASK_ENV'] == 'development':
# 	# turn on debugging, if in development
# 	app.debug = True # debug mnode

# cxn = pymongo.MongoClient(config['MONGO_URI'], serverSelectionTimeoutMS=5000)
# try:
# 	# verify the connection works by pinging the database
# 	cxn.admin.command('ping') # The ping command is cheap and does not require auth.
# 	db = cxn[config['MONGO_DBNAME']] # store a reference to the database
# 	print(' *', 'Connected to MongoDB!') # if we get here, the connection worked!
# except Exception as e:
# 	# the ping command failed, so the connection is not available.
# 	# render_template('error.html', error=e) # render the edit template
# 	print(' *', "Failed to connect to MongoDB at", config['MONGO_URI'])
# 	print('Database connection error:', e) # debug