from flask import Flask, redirect, render_template, session, flash, g, request, jsonify
from flask_debugtoolbar import DebugToolbarExtension
from sqlalchemy.exc import IntegrityError
from models import db, connect_db, User, Favorite, Review, Order
from forms import RegisterForm, LoginForm, IngredientSubsForm, EditProfileForm, ShopIngredientsForm, FilterRecipesForm
from keys import spoonacular_key, db_url
import json
import requests
import random
import decimal
import os


app = Flask(__name__)
app.app_context().push()
# app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql:///sous_chef')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', db_url)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = True
# app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'Sous-Chef')

connect_db(app)
db.create_all()

# debug = DebugToolbarExtension(app)

current_user = "curr_user"

# Account actions ********************************************************************************

@app.before_request
def add_user_to_g():
    """If we're logged in, add curr user to Flask global."""
    if current_user in session:
        g.user = User.query.get(session[current_user])
    else:
        g.user = None


def do_login(user):
    """Log user in"""
    session[current_user] = user.id


def do_logout():
    """Log user out"""
    if current_user in session:
        del session[current_user]

# User Account Info ********************************************************************************

@app.route('/register', methods=["GET", "POST"])
def register():
    """Load register form if nobody is logged in"""
    form = RegisterForm()
    if not g.user:
        if form.validate_on_submit():
            try:
                user = User.register(
                    first_name = form.first_name.data,
                    last_name = form.last_name.data,
                    email = form.email.data,
                    profile_pic = form.profile_pic.data or User.profile_pic.default.arg,
                    username = form.username.data,
                    password = form.password.data
                )
                db.session.commit()

            except IntegrityError:
                flash("Username already taken", 'danger')
                return render_template('user/register.html', form=form)

            do_login(user)

            return redirect("/")

        else:
            return render_template('user/register.html', form=form)
    
    else: 
        return redirect('/')  


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Load login form if nobody is logged in"""
    form = LoginForm()

    if not g.user:
        if form.validate_on_submit():
            user = User.authenticate(
                form.username.data,
                form.password.data
            )
            if user:
                do_login(user)
                flash(f"Hello, {user.username}!", "success")
                return redirect("/")

            flash("Invalid credentials.", 'danger')

        return render_template('user/login.html', form=form)
    
    else:
        return redirect('/')


@app.route('/logout')
def logout():
    """Log user out"""
    session.pop(current_user)
    flash("Goodbye!", "info")
    return redirect('/login')


@app.route("/")
def homepage():
    """Display homepage"""

    return render_template('index.html')


@app.route('/user/<int:user_id>')
def profile(user_id):
    """Get favorite recipes and reviews for the specified user and display them on their profile"""
    if user_id == g.user.id:
        user = User.query.get(user_id)
    else:
        user = User.query.get(user_id)

    favorites = [recipe.recipe_id for recipe in user.favorites]
    favorite_recipes = []

    for id in favorites:
        res = requests.get(f'https://api.spoonacular.com/recipes/{ id }/information',
                               params={
                                'apiKey': spoonacular_key,
                                'id': id
                               }).text

        recipe_info = json.loads(res)
        fixed_recipe = {
            'id': recipe_info['id'],
            'title': recipe_info['title'],
            'sourceUrl': recipe_info['sourceUrl'],
            'image': recipe_info.get('image', '/static/images/def_img.png'),
            'summary': recipe_info['summary'],
            'tags': {
                'Vegetarian': recipe_info['vegetarian'],
                'Vegan': recipe_info['vegan'],
                'Gluten Free': recipe_info['glutenFree'],
                'Dairy Free': recipe_info['dairyFree'],
                'Very Healthy': recipe_info['veryHealthy'],
                'Cheap': recipe_info['cheap'],
                'Very Popular': recipe_info['veryPopular'],
                'Sustainable': recipe_info['sustainable']
            }
        }

        favorite_recipes.append(fixed_recipe)

    reviewed_recipes = [recipe.recipe_id for recipe in user.reviews]
    reviews = []
    for id in reviewed_recipes:
        res = requests.get(f'https://api.spoonacular.com/recipes/{ id }/information',
                               params={
                                'apiKey': spoonacular_key,
                                'id': id
                               }).text
        
        recipe_info = json.loads(res)


        modified_info = {
            'id': recipe_info['id'],
            'title': recipe_info['title'],
            'image': recipe_info.get('image', '/static/images/def_img.png'),
            'rating': Review.query.filter(Review.recipe_id == recipe_info['id']).first().rating,
            'comment': Review.query.filter(Review.recipe_id == recipe_info['id']).first().comment
        }

        reviews.append(modified_info)
    
    return render_template('user/profile.html', user=user, recipes=favorite_recipes, favorites=favorites, reviews=reviews)


@app.route('/user/edit', methods=['GET', 'POST'])
def edit_profile():
    user = User.query.get_or_404(g.user.id)
    form = EditProfileForm()

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect(f'/user/{ g.user.id }')
    
    if form.validate_on_submit():
        if form.username.data:
            user.username = form.username.data
        else:
            user.username = user.username

        if form.email.data:
            user.email = form.email.data
        else:
            user.email = user.email

        if form.profile_pic.data:
            user.profile_pic = form.profile_pic.data
        else:
            user.profile_pic = user.profile_pic

        if User.authenticate(form.username.data, form.password.data):
            db.session.commit()
            flash('Profile Modified!', 'success')
            return redirect(f'/user/{ user.id }')
        else:
            flash("Password incorrect!", "danger")

    return render_template('user/profile-edit.html', form=form, user=user)


@app.route('/user/cart/load', methods=['POST'])
def load_user_cart():
    cart_info = []
    data = request.json.get('cart')

    if len(data) > 0:
        for item in data:
            res = requests.get(f'https://api.spoonacular.com/food/ingredients/{ item["id"] }/information',
               params={
                'apiKey': spoonacular_key,
               }).text

            ingredient_info = json.loads(res)

            info = {
                'id': item['id'],
                'name': ingredient_info['name'],
                'image': f"https://spoonacular.com/cdn/ingredients_100x100/{ ingredient_info['image'] }",
                'count': item['count'],
                'price': item['price'],
                'total': decimal.Decimal(float(item['count']) * float(item['price'])).quantize(decimal.Decimal('0.00'))
                  
            }

            cart_info.append(info)

    cart_total = 0
    for item in cart_info:
        cart_total = cart_total + item['total']

    results = {
        'cart_items': cart_info,
        'cart_total': decimal.Decimal(cart_total).quantize(decimal.Decimal('0.00'))
    }

    return jsonify(results)


@app.route('/user/cart/submit', methods=['POST'])
def submit_user_cart():
    user = User.query.get(g.user.id)

    if len(user.orders) == 0:
        order_num = 1
    else:
        order_num = user.orders[0].order_id + 1

    data = request.json.get('order')

    for item in data:
        db.session.add(Order(order_id=order_num, user_id=user.id, ingredient_id=item['id'], ingredient_count=item['count'], ingredient_price=item['price']))
        db.session.commit()


    flash('Order submitted successfully!', 'success')
    return redirect('/user/cart/previous')


@app.route('/user/cart/previous', methods=['GET', 'POST'])
def user_order_history():
    user = User.query.get(g.user.id)
    num_of_orders = user.orders[0].order_id
    orders = []
    
    for order in user.orders:
        res = requests.get(f'https://api.spoonacular.com/food/ingredients/{order.ingredient_id}/information',
           params={
            'apiKey': spoonacular_key,
           }).text
    
        ingredient_info = json.loads(res)
    
        info = {
            'order_id': order.order_id,
            'name': ingredient_info['originalName'],
            'image': f"https://spoonacular.com/cdn/ingredients_100x100/{ ingredient_info['image'] }",
            'count': order.ingredient_count,
            'price': order.ingredient_price,
            'total': decimal.Decimal(float(order.ingredient_count) * float(order.ingredient_price)).quantize(decimal.Decimal('0.00'))
        }

        orders.append(info)

    """Create list of items in each order"""
    order_dict = {}
    for i in reversed(range(1, num_of_orders+1)): 
        order_dict[i] = {'items': [], 'total': 0}
        for order in orders:
            if order['order_id'] == i:
                order_dict[i]['items'].append(order)

    """Calculate the total price of each order"""
    order_num = num_of_orders
    for order in order_dict:
        order_total = 0
        for item in order_dict[order]['items']:
            if item['order_id'] == order_num:

                order_total = order_total + (item['price'] * item['count'])
        
        order_num = order_num - 1
        order_dict[order]['total'] = decimal.Decimal(order_total).quantize(decimal.Decimal('0.00'))
                    
    return render_template('user/previous_orders.html', user=user, orders=order_dict)


@app.route('/user/cart')
def user_cart():
    user = User.query.get(g.user.id)

    return render_template('user/cart.html', user=user)

# Recipes ********************************************************************************

@app.route('/recipes/favorite', methods=['GET', 'POST'])
def recipe_fav():
    """Get recipe ID from js when favorite star is pressed and either add or remove from favorites"""
    recipe = int(request.json['recipeID'])
    user = User.query.get(g.user.id)
    favorites = [recipe.recipe_id for recipe in user.favorites]

    if (recipe in favorites):
        db.session.delete(Favorite.query.filter(Favorite.recipe_id == recipe, Favorite.user_id == g.user.id).first())
        db.session.commit()
    else:
        db.session.add(Favorite(user_id=g.user.id, recipe_id=recipe))
        db.session.commit()

    return jsonify(recipe)
    

@app.route('/recipes/more', methods=['GET', 'POST'])
def recipes_more():
    res = requests.get('https://api.spoonacular.com/recipes/random',
                           params={
                            'apiKey': spoonacular_key,
                            'number': 10
                           }).text

    recipes_data = json.loads(res)
    recipes = recipes_data['recipes']

    favorites = []

    if g.user:
        user = User.query.get(g.user.id)
        favorites = [recipe.recipe_id for recipe in user.favorites]

    modified_recipes = []

    for recipe in recipes:
        fixed_recipe = {
            'id': recipe['id'],
            'title': recipe['title'],
            'sourceUrl': recipe['sourceUrl'],
            'image': recipe.get('image', '/static/images/def_img.png'),
            'summary': recipe['summary'],
            'tags': {
                'Vegetarian': recipe['vegetarian'],
                'Vegan': recipe['vegan'],
                'Gluten Free': recipe['glutenFree'],
                'Dairy Free': recipe['dairyFree'],
                'Very Healthy': recipe['veryHealthy'],
                'Cheap': recipe['cheap'],
                'Very Popular': recipe['veryPopular'],
                'Sustainable': recipe['sustainable']
            }
        }

        if g.user:
            fixed_recipe['favorite'] = recipe['id'] in favorites

        modified_recipes.append(fixed_recipe)

    return jsonify(modified_recipes)


@app.route('/recipes/browse', methods=['GET', 'POST'])
def recipes_browse():
    form = FilterRecipesForm()

    if form.validate_on_submit:
        res = requests.get('https://api.spoonacular.com/recipes/random',
                       params={
                        'apiKey': spoonacular_key,
                        'number': 10,
                        'tags': form.filters.data
                       }).text
    
        recipes_data = json.loads(res)

    else:
        res = requests.get('https://api.spoonacular.com/recipes/random',
                               params={
                                'apiKey': spoonacular_key,
                                'number': 10
                               }).text

        recipes_data = json.loads(res)
    
    recipes = recipes_data['recipes']

    modified_recipes = []

    for recipe in recipes:
        fixed_recipe = {
            'id': recipe['id'],
            'title': recipe['title'],
            'sourceUrl': recipe['sourceUrl'],
            'image': recipe.get('image', '/static/images/def_img.png'),
            'summary': recipe['summary'],
            'tags': {
                'Vegetarian': recipe['vegetarian'],
                'Vegan': recipe['vegan'],
                'Gluten Free': recipe['glutenFree'],
                'Dairy Free': recipe['dairyFree'],
                'Very Healthy': recipe['veryHealthy'],
                'Cheap': recipe['cheap'],
                'Very Popular': recipe['veryPopular'],
                'Sustainable': recipe['sustainable']
            }
        }
        
        modified_recipes.append(fixed_recipe)

    if g.user:
        user = User.query.get(g.user.id)
        favorites = [recipe.recipe_id for recipe in user.favorites]

        return render_template('recipes/browse.html', recipes=modified_recipes, favorites=favorites, form=form)
    
    else:
        return render_template('recipes/browse.html', recipes=modified_recipes, form=form)


@app.route('/recipes/<int:recipe_id>')
def recipe_details(recipe_id):
    """Get info for recipe to display on page"""
    res = requests.get(f'https://api.spoonacular.com/recipes/{ recipe_id }/information',
                           params={
                            'apiKey': spoonacular_key,
                            'id': recipe_id
                           }).text

    recipe_info = json.loads(res)

    modified_info = {
        'id': recipe_info['id'],
        'title': recipe_info['title'],
        'sourceUrl': recipe_info['sourceUrl'],
        'image': recipe_info.get('image', '/static/images/def_img.png'),
        'summary': recipe_info['summary'],
        'servings': recipe_info['servings'],
        'readyInMinutes': recipe_info['readyInMinutes'],
        'analyzedInstructions': recipe_info['analyzedInstructions'],
        'extendedIngredients': recipe_info['extendedIngredients'],
        'tags': {
            'Vegetarian': recipe_info['vegetarian'],
            'Vegan': recipe_info['vegan'],
            'Gluten Free': recipe_info['glutenFree'],
            'Dairy Free': recipe_info['dairyFree'],
            'Very Healthy': recipe_info['veryHealthy'],
            'Cheap': recipe_info['cheap'],
            'Very Popular': recipe_info['veryPopular'],
            'Sustainable': recipe_info['sustainable']
        }
    }

    res = requests.get(f'https://api.spoonacular.com/recipes/{ recipe_id }/nutritionWidget.json',
                           params={
                            'apiKey': spoonacular_key,
                            'id': recipe_id
                           }).text

    nutrition_data = json.loads(res)

    calories = int(''.join(char for char in nutrition_data['calories'] if char.isdigit()))

    modified_good = [{**nutrient, 'rating': 'good'} for nutrient in nutrition_data['good']]
    modified_bad = [{**nutrient, 'rating': 'bad'} for nutrient in nutrition_data['bad']] 
    modified_nutrients = [nutrient for nutrient in (modified_good + modified_bad)]

    modified_data = {
        'calories': calories,
        'nutrients' : modified_nutrients
    }

    reviews = (db.session.query(User.id,
                                User.username,
                                User.profile_pic,
                                Review.recipe_id,
                                Review.rating,
                                Review.comment)
                            .join(Review).filter(Review.recipe_id == recipe_id).all())

    if g.user:
        user = User.query.get(g.user.id)
        favorites = [recipe.recipe_id for recipe in user.favorites]

        user_review = Review.query.filter(Review.user_id == user.id, Review.recipe_id == recipe_id).first()

        return render_template('recipes/details.html', recipe=modified_info, favorites=favorites, nutrition=modified_data, reviews=reviews, user_review=user_review)
    
    else:    
        
        return render_template('recipes/details.html', recipe=modified_info, nutrition=modified_data, reviews=reviews)


@app.route('/recipes/resourceful/add', methods=['GET', 'POST'])
def add_recipes_resourceful():
    """Get recipes using ingredients entered into the form"""
    ingredientsList = request.json.get('ingredients')
    ingredients = ', '.join(str(ingredient) for ingredient in ingredientsList)

    res = requests.get('https://api.spoonacular.com/recipes/findByIngredients',
                   params={
                    'apiKey': spoonacular_key,
                    'ingredients': ingredients,
                    'number': 10,
                    'limitLicense': True,
                    'ranking': 2,
                    'ignorePantry': True
                   }).text

    recipe_info = json.loads(res)

    if g.user:
        user = User.query.get(g.user.id)
        favorites = [recipe.recipe_id for recipe in user.favorites]

        for recipe in recipe_info:
            if recipe['id'] in favorites:
                recipe['favorite'] = True
            else:
                recipe['favorite'] = False

    return jsonify(recipe_info)


@app.route('/recipes/resourceful', methods=['GET', 'POST'])
def recipes_resourceful():
    """Get recipes using ingredients entered into the form"""

    return render_template('recipes/resourceful.html')


@app.route('/recipes/search', methods=['GET','POST'])
def recipe_search():
    """Search for recipe by key words"""
    recipe = request.args.get('search')

    res = requests.get('https://api.spoonacular.com/recipes/complexSearch',
                       params={
                        'apiKey': spoonacular_key,
                        'query': recipe
                       }).text
    
    recipe_info = json.loads(res)
    results = recipe_info['results']

    return render_template('recipes/search.html', results=results)



# Ingredients ********************************************************************************

@app.route('/ingredients/substitute', methods=['GET','POST'])
def ingredient_subs():
    """Find substitutes for specified ingredient"""
    form = IngredientSubsForm()
    modified_info = {}

    if form.validate_on_submit():
        ingredient = form.ingredient.data

        res = requests.get('https://api.spoonacular.com/food/ingredients/substitutes',
                           params={
                            'apiKey': spoonacular_key,
                            'ingredientName': ingredient
                           }).text

        recipe_info = json.loads(res)

        if recipe_info['status'] == 'success':
            modified_info['status'] = recipe_info['status']
            modified_info['ingredient'] = recipe_info['ingredient']
            modified_info['substitutes'] = recipe_info['substitutes']
        else:
            modified_info['status'] = recipe_info['status']

    return render_template('ingredients/substitutes.html', form=form, results=modified_info)


@app.route('/ingredients/order', methods=['GET','POST'])
def ingredient_order():
    """Create order and submit to instacart"""
    form = ShopIngredientsForm()

    if form.validate_on_submit():
        ingredient = form.ingredient.data

        res = requests.get('https://api.spoonacular.com/food/ingredients/search',
                   params={
                    'apiKey': spoonacular_key,
                    'query': ingredient
                   }).text

        ingredient_info = json.loads(res)
        results = ingredient_info['results']


        """Simulate a price"""
        for item in results: item['price'] = decimal.Decimal(random.uniform(1, 50)).quantize(decimal.Decimal('0.00'))

        return render_template('ingredients/order.html', form=form, results=results)
    else:
        return render_template('ingredients/order.html', form=form)

# Review ********************************************************************************

@app.route('/review/<int:recipe_id>/submit')
def submit_review(recipe_id):
    """Process recipe review submitted by user"""
    user = User.query.get(g.user.id)
    reviews = [review.recipe_id for review in user.reviews]

    if (recipe_id in reviews):
        flash("You've already left a review for this recipe", 'danger')
        return redirect(f'/recipe/{ recipe_id }')
    else:
        rating = request.args.get('rating')
        comment = request.args.get('comment')
        db.session.add(Review(user_id=g.user.id, recipe_id=recipe_id, rating=rating, comment=comment))
        db.session.commit()

        flash('Review submitted successfully!', 'success')
        return redirect(f'/recipes/{ recipe_id }')

