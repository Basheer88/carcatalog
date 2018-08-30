from flask import Flask, render_template, request, redirect, jsonify, url_for, flash
from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Manager, Brand, Model
from flask import session as login_session
import random
import string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

app = Flask(__name__)

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Restaurant Menu Application"


# Connect to Database and create database session
engine = create_engine('sqlite:///carmodel.db',
                       connect_args={'check_same_thread': False})
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


# Create anti-forgery state token
@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    # return "The current session state is %s" % login_session['state']
    return render_template('login.html', STATE=state)


@app.route('/fbconnect', methods=['POST'])
def fbconnect():
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = request.data
    print "access token received %s " % access_token

    app_id = json.loads(open('fb_client_secrets.json', 'r').read())[
        'web']['app_id']
    app_secret = json.loads(
        open('fb_client_secrets.json', 'r').read())['web']['app_secret']
    url = 'https://graph.facebook.com/oauth/access_token?grant_type=fb_exchange_token&client_id=%s&client_secret=%s&fb_exchange_token=%s' % (
        app_id, app_secret, access_token)
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]

    # Use token to get user info from API
    userinfo_url = "https://graph.facebook.com/v2.8/me"
    '''
        Due to the formatting for the result from the server token exchange
        we have to split the token first on commas and select the first index
        which gives us the key : value for the server access token then we
        split it on colons to pull out the actual token value and replace the
        remaining quotes with nothing so that it can be used directly in the
        graph api calls
    '''
    token = result.split(',')[0].split(':')[1].replace('"', '')

    url = 'https://graph.facebook.com/v2.8/me?access_token=%s&fields=name,id,email' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    # print "url sent for API access:%s"% url
    # print "API JSON result: %s" % result
    data = json.loads(result)
    login_session['provider'] = 'facebook'
    login_session['username'] = data["name"]
    login_session['email'] = data["email"]
    login_session['facebook_id'] = data["id"]

    # The token must be stored in the login_session in order to properly logout
    login_session['access_token'] = token

    # Get user picture
    url = 'https://graph.facebook.com/v2.8/me/picture?access_token=%s&redirect=0&height=200&width=200' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result)

    login_session['picture'] = data["data"]["url"]

    # see if user exists
    user_id = getManagerID(login_session['email'])
    if not user_id:
        user_id = createManager(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']

    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '

    flash("Now logged in as %s" % login_session['username'])
    return output


@app.route('/fbdisconnect')
def fbdisconnect():
    facebook_id = login_session['facebook_id']
    # The access token must me included to successfully logout
    access_token = login_session['access_token']
    url = 'https://graph.facebook.com/%s/permissions?access_token=%s' % (facebook_id, access_token)
    h = httplib2.Http()
    result = h.request(url, 'DELETE')[1]
    return "you have been logged out"


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user already connected.'),
                                 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    # ADD PROVIDER TO LOGIN SESSION
    login_session['provider'] = 'google'

    # see if user exists, if it doesn't make a new one
    user_id = getManagerID(data["email"])
    if not user_id:
        user_id = createManager(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output

# User Helper Functions


def createManager(login_session):
    newManager = Manager(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    session.add(newManager)
    session.commit()
    manager = session.query(Manager).filter_by(email=login_session['email']).one()
    return manager.id


def getManagerInfo(manager_id):
    manager = session.query(Manager).filter_by(id=manager_id).one()
    return manager


def getManagerID(email):
    try:
        manager = session.query(Manager).filter_by(email=email).one()
        return manager.id
    except:
        return None

# DISCONNECT - Revoke a current user's token and reset their login_session


@app.route('/gdisconnect')
def gdisconnect():
    # Only disconnect a connected user.
    access_token = login_session.get('access_token')
    if access_token is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] == '200':
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        response = make_response(json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


# JSON APIs to view Restaurant Information
@app.route('/brand/<int:brand_id>/model/JSON')
def brandModelJSON(brand_id):
    brand = session.query(Brand).filter_by(id=brand_id).one()
    items = session.query(Model).filter_by(brand_id=brand_id).all()
    return jsonify(Model=[i.serialize for i in items])


@app.route('/brand/<int:brand_id>/model/<int:model_id>/JSON')
def modelJSON(brand_id, model_id):
    Model_Item = session.query(Model).filter_by(id=model_id).one()
    return jsonify(Model_Item=Model_Item.serialize)


@app.route('/brand/JSON')
def brandsJSON():
    brands = session.query(Brand).all()
    return jsonify(brands=[r.serialize for r in brands])


# Show all brands
@app.route('/')
@app.route('/brand/')
def showBrands():
    brands = session.query(Brand).order_by(asc(Brand.name))
    if 'username' not in login_session:
        return render_template('publicbrands.html', brands=brands)
    else:
        return render_template('brands.html', brands=brands)


# Create a new Brand
@app.route('/brand/new/', methods=['GET', 'POST'])
def newBrand():
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        newBrand = Brand(
            name=request.form['name'], manager_id=login_session['user_id'])
        session.add(newBrand)
        flash('New Brand %s Successfully Created' % newBrand.name)
        session.commit()
        return redirect(url_for('showBrands'))
    else:
        return render_template('newBrand.html')


# Edit a brand
@app.route('/brand/<int:brand_id>/edit/', methods=['GET', 'POST'])
def editBrand(brand_id):
    editedBrand = session.query(Brand).filter_by(id=brand_id).one()
    if 'username' not in login_session:
        return redirect('/login')
    if editedBrand.manager_id != login_session['user_id']:
        return "<script>function myFunction() {alert('You are not authorized to edit this restaurant. Please create your own restaurant in order to edit.');}</script><body onload='myFunction()'>"
    if request.method == 'POST':
        if request.form['name']:
            editedBrand.name = request.form['name']
            flash('Brand Successfully Edited %s' % editedBrand.name)
            return redirect(url_for('showBrands'))
    else:
        return render_template('editBrand.html', brand=editedBrand)


# Delete a brand
@app.route('/brand/<int:brand_id>/delete/', methods=['GET', 'POST'])
def deleteBrand(brand_id):
    brandToDelete = session.query(Brand).filter_by(id=brand_id).one()
    if 'username' not in login_session:
        return redirect('/login')
    if brandToDelete.manager_id != login_session['user_id']:
        return "<script>function myFunction() {alert('You are not authorized to delete this restaurant. Please create your own restaurant in order to delete.');}</script><body onload='myFunction()'>"
    if request.method == 'POST':
        session.delete(brandToDelete)
        flash('%s Successfully Deleted' % brandToDelete.name)
        session.commit()
        return redirect(url_for('showBrandss', brand_id=brand_id))
    else:
        return render_template('deleteBrand.html', brand=brandToDelete)


# Show a model
@app.route('/brand/<int:brand_id>/')
@app.route('/brand/<int:brand_id>/menu/')
def showModel(brand_id):
    brand = session.query(Brand).filter_by(id=brand_id).one()
    creator = getManagerInfo(brand.manager_id)
    items = session.query(Model).filter_by(brand_id=brand_id).all()
    if 'username' not in login_session or creator.id != login_session['user_id']:
        return render_template('publicmodel.html', items=items, brand=brand, creator=creator)
    else:
        return render_template('menu.html', items=items, brand=brand, creator=creator)


# Create a new model
@app.route('/brand/<int:brand_id>/model/new/', methods=['GET', 'POST'])
def newModel(brand_id):
    if 'username' not in login_session:
        return redirect('/login')
    brand = session.query(Brand).filter_by(id=brand_id).one()
    if login_session['user_id'] != brand.manager_id:
        return "<script>function myFunction() {alert('You are not authorized to add menu items to this restaurant. Please create your own restaurant in order to add items.');}</script><body onload='myFunction()'>"
    if request.method == 'POST':
        newItem = Model(name=request.form['name'],
                        description=request.form['description'],
                        price=request.form['price'], brand_id=brand_id,
                        manager_id=brand.manager_id)
        session.add(newItem)
        session.commit()
        flash('New Model %s Item Successfully Created' % (newItem.name))
        return redirect(url_for('showModel', brand_id=brand_id))
    return render_template('newmodel.html', brand_id=brand_id)


# Edit a model
@app.route('/brand/<int:brand_id>/model/<int:model_id>/edit', methods=['GET', 'POST'])
def editModel(brand_id, model_id):
    if 'username' not in login_session:
        return redirect('/login')
    editedItem = session.query(Model).filter_by(id=model_id).one()
    brand = session.query(Brand).filter_by(id=brand_id).one()
    if login_session['user_id'] != brand.manager_id:
        return "<script>function myFunction() {alert('You are not authorized to edit menu items to this restaurant. Please create your own restaurant in order to edit items.');}</script><body onload='myFunction()'>"
    if request.method == 'POST':
        if request.form['name']:
            editedItem.name = request.form['name']
        if request.form['description']:
            editedItem.description = request.form['description']
        if request.form['price']:
            editedItem.price = request.form['price']
        session.add(editedItem)
        session.commit()
        flash('Model Successfully Edited')
        return redirect(url_for('showModel', brand_id=brand_id))
    else:
        return render_template('editmodel.html', brand_id=brand_id, model_id=model_id, item=editedItem)


# Delete model
@app.route('/brand/<int:brand_id>/model/<int:model_id>/delete', methods=['GET', 'POST'])
def deleteModel(brand_id, model_id):
    if 'username' not in login_session:
        return redirect('/login')
    brand = session.query(Brand).filter_by(id=brand_id).one()
    itemToDelete = session.query(Model).filter_by(id=model_id).one()
    if login_session['user_id'] != brand.manager_id:
        return "<script>function myFunction() {alert('You are not authorized to delete menu items to this restaurant. Please create your own restaurant in order to delete items.');}</script><body onload='myFunction()'>"
    if request.method == 'POST':
        session.delete(itemToDelete)
        session.commit()
        flash('Model Successfully Deleted')
        return redirect(url_for('showModel', brand_id=brand_id))
    else:
        return render_template('deleteModel.html', item=itemToDelete)


# Disconnect based on provider
@app.route('/disconnect')
def disconnect():
    if 'provider' in login_session:
        if login_session['provider'] == 'google':
            gdisconnect()
            del login_session['gplus_id']
            del login_session['access_token']
        if login_session['provider'] == 'facebook':
            fbdisconnect()
            del login_session['facebook_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        del login_session['user_id']
        del login_session['provider']
        flash("You have successfully been logged out.")
        return redirect(url_for('showBrands'))
    else:
        flash("You were not logged in")
        return redirect(url_for('showBrands'))


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=8000)
