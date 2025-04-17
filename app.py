from flask import Flask, render_template, request, redirect, session
from flask_mysqldb import MySQL

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Needed for session management

# Database Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'aishisql25'  # Replace with your MySQL password
app.config['MYSQL_DB'] = 'recipe_db'

mysql = MySQL(app)

# Home route with updated layout and links
@app.route('/')
def home():
    if 'username' in session:
        return render_template('home.html', username=session['username'])
    return redirect('/login')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']  # Get role from the form

        cursor = mysql.connection.cursor()
        cursor.execute("INSERT INTO users (username, password, role) VALUES (%s, %s, %s)", (username, password, role))
        mysql.connection.commit()
        cursor.close()

        return redirect('/login')

    return render_template('signup.html')


# Recipe saving route
@app.route('/save_recipe/<int:recipe_id>', methods=['POST', 'GET'])
def save_recipe(recipe_id):
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    
    cursor = mysql.connection.cursor()
    cursor.execute("INSERT IGNORE INTO saved_recipes (user_id, recipe_id) VALUES (%s, %s)", (user_id, recipe_id))
    mysql.connection.commit()
    cursor.close()

    return redirect('/saved_recipes')


# Recipe unsaving route
@app.route('/unsave_recipe/<int:recipe_id>', methods=['POST'])
def unsave_recipe(recipe_id):
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']

    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM saved_recipes WHERE user_id = %s AND recipe_id = %s", (user_id, recipe_id))
    mysql.connection.commit()
    cursor.close()

    return redirect('/saved_recipes')


# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cursor = mysql.connection.cursor()
        cursor.execute('SELECT id, username, password, role FROM users WHERE username = %s', (username,))
        user = cursor.fetchone()
        cursor.close()

        if user and user[2] == password:  # Compare plain text password
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['role'] = user[3]

            if user[3] == 'admin':
                return redirect('/admin_dashboard')
            else:
                return redirect('/')
        
        return 'Invalid username or password'

    return render_template('login.html')


# Rate recipe route
@app.route('/rate_recipe/<int:recipe_id>', methods=['POST'])
def rate_recipe(recipe_id):
    if 'user_id' not in session:
        return redirect('/login')

    rating = request.form['rating']
    user_id = session['user_id']

    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM recipe_ratings WHERE user_id = %s AND recipe_id = %s", (user_id, recipe_id))
    existing_rating = cursor.fetchone()

    if existing_rating:
        return "You've already rated this recipe. You can only rate once.", 400

    cursor.execute("INSERT INTO recipe_ratings (user_id, recipe_id, rating) VALUES (%s, %s, %s)", (user_id, recipe_id, rating))
    mysql.connection.commit()

    cursor.execute("SELECT AVG(rating) FROM recipe_ratings WHERE recipe_id = %s", (recipe_id,))
    avg_rating = cursor.fetchone()[0]

    cursor.execute("UPDATE recipes SET average_rating = %s WHERE id = %s", (avg_rating, recipe_id))
    mysql.connection.commit()

    cursor.close()

    return redirect('/saved_recipes')


# Saved recipes route
@app.route('/saved_recipes')
def saved_recipes():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']

    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT r.id, r.name, r.cuisine, r.ingredients, r.instructions, r.average_rating,
               CASE WHEN EXISTS (SELECT 1 FROM recipe_ratings WHERE user_id = %s AND recipe_id = r.id) THEN TRUE ELSE FALSE END AS rated
        FROM recipes r
        JOIN saved_recipes sr ON r.id = sr.recipe_id
        WHERE sr.user_id = %s
    """, (user_id, user_id))

    recipes = cursor.fetchall()
    cursor.close()

    return render_template('saved_recipes.html', recipes=recipes)


# Logout route
@app.route('/logout')
def logout():
    session.clear()  # Logout user
    return redirect('/login')


# Search by ingredients route
@app.route('/search_by_ingredients', methods=['GET', 'POST'])
def search_by_ingredients():
    if request.method == 'POST':
        ingredients = request.form['ingredients']
        ingredients_list = ingredients.split(',')

        query = "SELECT * FROM recipes WHERE "
        query += " OR ".join(["ingredients LIKE %s" for _ in ingredients_list])
        
        cursor = mysql.connection.cursor()
        cursor.execute(query, ['%' + ingredient.strip() + '%' for ingredient in ingredients_list])
        recipes = cursor.fetchall()
        cursor.close()

        return render_template('search_by_ingredients.html', recipes=recipes)

    return render_template('search_by_ingredients.html', recipes=None)


# Search route
@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        cuisine = request.form['cuisine']
        ingredient = request.form['ingredient']
        
        cursor = mysql.connection.cursor()

        if cuisine and ingredient:
            query = """
                SELECT * FROM recipes 
                WHERE cuisine LIKE %s 
                AND ingredients LIKE %s
            """
            cursor.execute(query, ('%' + cuisine + '%', '%' + ingredient + '%'))
        elif cuisine:
            query = "SELECT * FROM recipes WHERE cuisine LIKE %s"
            cursor.execute(query, ('%' + cuisine + '%',))
        elif ingredient:
            query = "SELECT * FROM recipes WHERE ingredients LIKE %s"
            cursor.execute(query, ('%' + ingredient + '%',))
        else:
            cursor.execute("SELECT * FROM recipes")
        
        recipes = cursor.fetchall()
        cursor.close()

        return render_template('search.html', recipes=recipes)

    return render_template('search.html', recipes=None)


# Add new recipe route (Admin)
@app.route('/add_recipes', methods=['GET', 'POST'])
def add_recipe():
    if 'username' not in session or session['role'] != 'admin':
        return redirect('/login')

    if request.method == 'POST':
        name = request.form['name']
        cuisine = request.form['cuisine']
        ingredients = request.form['ingredients']
        instructions = request.form['instructions']

        cursor = mysql.connection.cursor()
        cursor.execute('INSERT INTO recipes (name, cuisine, ingredients, instructions) VALUES (%s, %s, %s, %s)',
                       (name, cuisine, ingredients, instructions))
        mysql.connection.commit()
        cursor.close()

        return redirect('/admin_dashboard')

    return render_template('add_recipe.html')


# Admin dashboard route
@app.route('/admin_dashboard')
def admin_dashboard():
    if 'username' not in session or session['role'] != 'admin':
        return redirect('/login')
    
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM recipes")
    recipes = cursor.fetchall()
    cursor.close()
    
    return render_template('admin_dashboard.html', recipes=recipes)


# Admin view all recipes route
@app.route('/admin_view_recipes')
def admin_view_recipes():
    if 'username' not in session or session['role'] != 'admin':
        return redirect('/login')

    cursor = mysql.connection.cursor()
    cursor.execute("SELECT id, name, cuisine, ingredients, instructions, average_rating FROM recipes")
    recipes = cursor.fetchall()
    cursor.close()

    return render_template('admin_view_recipes.html', recipes=recipes)


# Delete recipe (Admin)
@app.route('/delete_recipe/<int:recipe_id>', methods=['POST'])
def delete_recipe(recipe_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')  # Only admins should be able to delete recipes

    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM recipes WHERE id = %s", (recipe_id,))
    mysql.connection.commit()
    cursor.close()

    return redirect('/admin_dashboard')

@app.route('/random_recipe')
def random_recipe():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT id, name, cuisine, ingredients, instructions, average_rating FROM recipes ORDER BY RAND() LIMIT 1")
    recipe = cursor.fetchone()
    cursor.close()

    if not recipe:
        return render_template('random_recipe.html', recipe=None)

    recipe_data = {
        'id': recipe[0],
        'name': recipe[1],
        'cuisine': recipe[2],
        'ingredients': recipe[3],
        'instructions': recipe[4],
        'average_rating': recipe[5]
    }

    return render_template('random_recipe.html', recipe=recipe_data)



if __name__ == '__main__':
    app.run(debug=True)
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
    
