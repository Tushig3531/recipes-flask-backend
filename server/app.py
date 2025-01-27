import os
import sys
import pathlib
import pandas as pd
import requests
import dotenv
import csv
import re
import logging
from googleapiclient.discovery import build  

from flask import Flask, request, jsonify, url_for, render_template
from flask_bcrypt import Bcrypt
from flask_jwt_extended import (
    JWTManager, create_access_token, get_jwt_identity,
    jwt_required, set_access_cookies, unset_jwt_cookies
)
from datetime import datetime, timedelta


from config import create_app, db
from model import User, Recipe, SavedRecipe, FridgeItem
from flask import send_from_directory


dotenv.load_dotenv()

app = create_app()


bcrypt = Bcrypt(app)

app.config["JWT_TOKEN_LOCATION"] = ["cookies"]
app.config["JWT_ACCESS_COOKIE_PATH"] = "/"
app.config["JWT_COOKIE_SECURE"] = False  
app.config["JWT_COOKIE_SAMESITE"] = "Lax" 
app.config["JWT_COOKIE_CSRF_PROTECT"] = False 
JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)  
JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)
jwt = JWTManager(app)


@app.route('/register', methods=['POST'])
def register():
    data = request.json
    if not data:
        return jsonify({"error": "No data"}), 400

    existing_user = User.query.filter_by(email=data['email']).first()
    if existing_user:
        return jsonify({"error": "Email already registered"}), 400

    hashed_password = bcrypt.generate_password_hash(data['password']).decode('utf-8')
    new_user = User(username=data['username'], email=data['email'], password=hashed_password)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"message": "User registered successfully!"}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({"error": "Email and password are required."}), 400

    user = User.query.filter_by(email=data['email']).first()
    if user and bcrypt.check_password_hash(user.password, data['password']):
        access_token = create_access_token(identity=str(user.id))
        response = jsonify({"message": "Login successful!"})
        set_access_cookies(response, access_token)
        return response, 200
    else:
        return jsonify({"error": "Invalid credentials."}), 401
    
@app.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    response = jsonify({"message": "Logged out successfully"})
    unset_jwt_cookies(response)
    return response, 200


@app.route('/protected', methods=['GET'])
@jwt_required()
def protected():
    try:
        user_id = get_jwt_identity()
        user = User.query.get(int(user_id))
        if not user:
            return jsonify({'message': 'User not found'}), 404
        return jsonify({
            'message': 'This is a protected route',
            'user': {
                'id': user.id,
                'username': user.username
            }
        })
    except Exception as e:
        return jsonify({'message': f'Token validation failed: {str(e)}'}), 422



def load_recipes_from_csv():
    recipes = []
    filename = os.path.join(os.path.dirname(__file__), "Food.csv")
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8-sig") as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    recipe_id = row.get("recipe_id")
                    if recipe_id is None or not recipe_id.strip().isdigit():
                        logging.warning(f"Invalid recipe_id found: {recipe_id}. Generating new ID.")
                        recipe_id = len(recipes) + 1
                    else:
                        recipe_id = int(recipe_id)

                    recipes.append({
                        "recipe_id": recipe_id,
                        "name": row["Title"].strip(),
                        "ingredients": row["Ingredients"].strip(),
                        "instructions": row["Instructions"].strip(),
                        "image_name": row["Image_Name"].strip(),
                    })
        except Exception as e:
            logging.error(f"Error reading CSV: {e}")
    else:
        logging.error("Food.csv does not exist.")
    logging.info(f"Loaded {len(recipes)} recipes from CSV.")
    return recipes

def get_image_url(image_name):
    if not image_name:
        return ""
    return f"https://storage.googleapis.com/recipesapp-images1/{image_name}.png"



def search_recipes_from_csv_by_ingredients(ingredient_string):
    ingredient_list = [ing.strip().lower() for ing in ingredient_string.split(",") if ing.strip()]

    results = []
    csv_path = os.path.join(os.path.dirname(__file__), "Food.csv")
    if not os.path.isfile(csv_path):
        logging.error("Food.csv not found.")
        return results

    with open(csv_path, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row_ingredients = row.get("Ingredients", "").lower()
            if all(ing in row_ingredients for ing in ingredient_list):
                image_name = row.get("Image_Name", "").strip()
                image_url = get_image_url(image_name)
                results.append({
                    "recipe_id": row.get("recipe_id", "0"),
                    "name": row.get("Title", "Untitled"),
                    "ingredients": row.get("Ingredients", ""),
                    "instructions": row.get("Instructions", ""),
                    "image_url": image_url,
                    "youtube_url": ""  
                })
    return results

def search_recipes_from_csv_by_name(name_query):
    
    name_query = name_query.strip().lower()
    results = []
    csv_path = os.path.join(os.path.dirname(__file__), "Food.csv")
    if not os.path.isfile(csv_path):
        logging.error("Food.csv not found.")
        return results

    with open(csv_path, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row_name = row.get("Title", "").lower()
            if name_query in row_name:
                image_name = row.get("Image_Name", "").strip()
                image_url = get_image_url(image_name)
                results.append({
                    "recipe_id": row.get("recipe_id", "0"),
                    "name": row.get("Title", "Untitled"),
                    "ingredients": row.get("Ingredients", ""),
                    "instructions": row.get("Instructions", ""),
                    "image_url": image_url,
                    "youtube_url": "",
                })
    return results

def get_recipe_details_from_csv(recipe_name):

    if not recipe_name:
        return None

    csv_path = os.path.join(os.path.dirname(__file__), "Food.csv")
    if not os.path.isfile(csv_path):
        logging.error("Food.csv not found.")
        return None

    recipe_name_lower = recipe_name.strip().lower()
    with open(csv_path, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Compare ignoring case
            row_title = row.get("Title", "").strip().lower()
            if row_title == recipe_name_lower:
                image_name = row.get("Image_Name", "").strip()
                image_url = get_image_url(image_name)
                return {
                    "recipe_id": row.get("recipe_id", "0"),
                    "name": row.get("Title", ""),
                    "ingredients": row.get("Ingredients", ""),
                    "instructions": row.get("Instructions", ""),
                    "image_url": image_url,
                    "youtube_url": ""
                }
    return None

@app.route("/debug_load_csv", methods=["GET"])
def debug_load_csv():
    recipes = load_recipes_from_csv()
    return jsonify(recipes)

@app.route("/list_recipes", methods=["GET"])
def list_recipes():
    all_recipes = Recipe.query.all()
    return jsonify([r.to_dict() for r in all_recipes])



@app.route('/search_recipes_by_ingredients', methods=['GET'])
@jwt_required()
def search_recipes_by_ingredients_csv():
    ingredients = request.args.get('ingredients', '').strip()
    if not ingredients:
        return jsonify({"error": "No ingredients provided."}), 400
    matching_recipes = search_recipes_from_csv_by_ingredients(ingredients)
    return jsonify({"recipes": matching_recipes, "count": len(matching_recipes)}), 200

@app.route('/search_recipes_by_name', methods=['GET'])
@jwt_required()
def search_recipes_by_name_csv():
    name = request.args.get('name', '').strip()
    if not name:
        return jsonify({"error": "No recipe name provided."}), 400
    matching_recipes = search_recipes_from_csv_by_name(name)
    return jsonify({"recipes": matching_recipes, "count": len(matching_recipes)}), 200




@app.route('/autocomplete_recipes', methods=['GET'])
@jwt_required()
def autocomplete_recipes():

    query = request.args.get('q', '').strip().lower()
    search_type = request.args.get('type', 'ingredient')

    if not query:
        return jsonify({"suggestions": []}), 200

    if search_type == 'ingredient':
        recipes = Recipe.query.filter(Recipe.ingredients.ilike(f"%{query}%")).all()
        suggestions = []
        for r in recipes:
            ing_list = re.findall(r"[A-Za-z0-9\-]+", r.ingredients.lower())
            for ing in ing_list:
                if query in ing and ing not in suggestions:
                    suggestions.append(ing)
        return jsonify({"suggestions": suggestions[:10]}), 200
    elif search_type == 'name':
        # DB-based
        recipes = Recipe.query.filter(Recipe.name.ilike(f"%{query}%")).all()
        suggestions = []
        for r in recipes:
            if query in r.name.lower() and r.name not in suggestions:
                suggestions.append(r.name)
        return jsonify({"suggestions": suggestions[:10]}), 200
    else:
        return jsonify({"suggestions": []}), 200


@app.route("/recipe_details_csv", methods=["GET"])
def get_recipe_details_csv():
    recipe_name = request.args.get("name", "").strip().lower()
    if not recipe_name:
        return jsonify({"error": "Recipe name is required"}), 400

    csv_path = os.path.join(os.path.dirname(__file__), "Food.csv")
    if not os.path.isfile(csv_path):
        return jsonify({"error": "Food.csv not found"}), 500

    with open(csv_path, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            
            row_title = row.get("Title", "").strip().lower()
            if row_title == recipe_name:
                image_name = row.get("Image_Name", "").strip()
                image_url = get_image_url(image_name)
                
                return jsonify({
                    "recipe": {
                        "recipe_id": row.get("recipe_id", "0"),
                        "name": row.get("Title", ""),
                        "ingredients": row.get("Ingredients", ""),
                        "instructions": row.get("Instructions", ""),
                        "image_url": image_url,
                        "youtube_url": ""
                    }
                }), 200

    return jsonify({"error": "No recipe found with the given name."}), 404



@app.route('/save_recipe', methods=['POST'])
@jwt_required()
def save_recipe():
    user_id = get_jwt_identity()
    data = request.json

    external_id = data.get('recipe_id')
    if not external_id:
        return jsonify({"error": "recipe_id is required"}), 400
    
    existing_recipe = Recipe.query.filter_by(recipe_id=external_id).first()
    if not existing_recipe:
        existing_recipe = Recipe(
            recipe_id=int(external_id),
            name=data.get('name', 'Untitled'),
            ingredients=data.get('ingredients', ''),
            instructions=data.get('instructions', ''),
            youtube_url=data.get('youtube_url', ''),
            image_url=data.get('image_url', '')
        )
        db.session.add(existing_recipe)
        db.session.commit()


    from_user = User.query.get(int(user_id))  
    if not from_user:
        return jsonify({"error": "User not found"}), 400

    already_saved = SavedRecipe.query.filter_by(user_id=int(user_id), recipe_id=existing_recipe.id).first()
    if already_saved:
        return jsonify({"message": "Recipe already saved"}), 400

    new_saved = SavedRecipe(user_id=int(user_id), recipe_id=existing_recipe.id)
    db.session.add(new_saved)
    db.session.commit()
    return jsonify({"message": "Recipe saved successfully!"}), 201

@app.route('/unsave_recipe/<int:recipe_id>', methods=['DELETE'])
@jwt_required()
def unsave_recipe(recipe_id):
    user_id = get_jwt_identity()
    
    
    recipe = Recipe.query.filter_by(recipe_id=recipe_id).first()
    if not recipe:
        return jsonify({"error": "Recipe not found."}), 404
    
    
    saved_recipe = SavedRecipe.query.filter_by(user_id=int(user_id), recipe_id=recipe.id).first()
    if not saved_recipe:
        return jsonify({"error": "Recipe not saved."}), 400
    
    
    db.session.delete(saved_recipe)
    db.session.commit()
    
    return jsonify({"message": "Recipe removed successfully!"}), 200

@app.route('/saved_recipes', methods=['GET'])
@jwt_required()
def get_saved_recipes():
    
    user_id = get_jwt_identity()
    saved_list = SavedRecipe.query.filter_by(user_id=int(user_id)).all()

    recipes = []
    for sr in saved_list:
        r = Recipe.query.get(sr.recipe_id)
        if r:
            recipes.append(r.to_dict())
    return jsonify(recipes), 200

@app.route('/is_recipe_saved/<int:recipe_id>', methods=['GET'])
@jwt_required()
def is_recipe_saved(recipe_id):
    user_id = get_jwt_identity()
    recipe = Recipe.query.filter_by(recipe_id=recipe_id).first()
    if not recipe:
        return jsonify({"saved": False}), 200
    saved = SavedRecipe.query.filter_by(user_id=int(user_id), recipe_id=recipe.id).first()
    return jsonify({"saved": bool(saved)}), 200





def load_items_from_csv_Item():
    items = []
    filename = os.path.join(os.path.dirname(__file__), "Item.csv")
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8-sig") as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    items.append(row["ItemName"])
        except Exception as e:
            print(f"Error reading CSV: {e}")
    else:
        print("Item.csv does not exist.")
    return items

@app.route("/fridge/search_items_fridge", methods=["GET"])
@jwt_required()
def search_items_fridge():
    query = request.args.get("q", "").lower()
    if not query:
        return jsonify({})

    csv_items = load_items_from_csv_Item()
    results = {}
    for item in csv_items:
        if query in item.lower():
            match = re.match(r"^(.*?)\s*\((.*?)\)", item)
            if match:
                keyword, item_type = match.groups()
                results.setdefault(keyword.strip(), []).append(item_type.strip())
            else:
                results.setdefault(item.strip(), []).append("")
    return jsonify(results)

@app.route('/fridge', methods=['GET'])
@jwt_required()
def get_fridge_items():
    user_id = get_jwt_identity()
    items = FridgeItem.query.filter_by(user_id=int(user_id)).all()
    result = []
    for item in items:
        result.append({
            "id": item.id,
            "item_name": item.item_name,
            "brand": item.brand,
            "quantity": item.quantity,
            "date_added": item.date_added.strftime("%Y-%m-%d %H:%M:%S")
        })
    return jsonify(result), 200

@app.route('/fridge/add', methods=['POST'])
@jwt_required()
def add_fridge_item():
    user_id = get_jwt_identity()
    data = request.json
    item_name = data.get("item_name")
    brand = data.get("brand", "No Brand")
    quantity = data.get("quantity", "0 items")
    if not item_name:
        return jsonify({"error": "Item name is required"}), 400
    new_item = FridgeItem(
        user_id=int(user_id),
        item_name=item_name,
        brand=brand,
        quantity=quantity,
        date_added=datetime.utcnow()
    )
    db.session.add(new_item)
    db.session.commit()
    return jsonify({
        "id": new_item.id,
        "item_name": new_item.item_name,
        "brand": new_item.brand,
        "quantity": new_item.quantity,
        "date_added": new_item.date_added.strftime("%Y-%m-%d %H:%M:%S")
    }), 201

@app.route('/fridge/edit/<int:item_id>', methods=['POST'])
@jwt_required()
def edit_fridge_item(item_id):
    
    user_id = get_jwt_identity()
    data = request.json

    item = FridgeItem.query.filter_by(id=item_id, user_id=int(user_id)).first()
    if not item:
        return jsonify({"error": "Item not found or not yours"}), 404

    new_quantity = data.get("quantity")
    new_brand = data.get("brand")
    new_name = data.get("item_name")

    if new_quantity is not None:
        item.quantity = new_quantity
    if new_brand is not None:
        item.brand = new_brand
    if new_name is not None:
        item.item_name = new_name

    db.session.commit()
    return jsonify({"message": "Item updated successfully!"}), 200

@app.route('/fridge/delete/<int:item_id>', methods=['POST'])
@jwt_required()
def delete_fridge_item(item_id):
    user_id = get_jwt_identity()
    item = FridgeItem.query.filter_by(id=item_id, user_id=int(user_id)).first()
    if not item:
        return jsonify({"error": "Item not found or not yours"}), 404

    db.session.delete(item)
    db.session.commit()
    return jsonify({"message": "Item deleted successfully!"}), 200

@app.route('/list_tables')
@jwt_required()
def list_tables():
    tables = db.engine.table_names()
    return {"tables": tables}



@app.route('/youtube_tutorial', methods=['GET'])
@jwt_required()
def youtube_tutorial():
    query = request.args.get('query', '').strip()
    if not query:
        return jsonify({"error": "Query parameter is required."}), 400

    YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')  
    if not YOUTUBE_API_KEY:
        return jsonify({"error": "YouTube API key not configured."}), 500

    youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
    request_youtube = youtube.search().list(
        part="snippet",
        q=f"{query} tutorial",
        type="video",
        maxResults=1
    )
    response = request_youtube.execute()

    if 'items' in response and len(response['items']) > 0:
        video_id = response['items'][0]['id']['videoId']
        youtube_url = f"https://www.youtube.com/embed/{video_id}"
        return jsonify({"youtube_url": youtube_url}), 200
    else:
        return jsonify({"youtube_url": ""}), 200

if __name__ == "__main__":
    app.run(debug=True, port=8080)
