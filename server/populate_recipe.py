import os
import csv
from model import db, Recipe
from config import create_app

def populate_recipes_from_csv():
    csv_path = os.path.join(os.path.dirname(__file__), "Food.csv")

    if not os.path.exists(csv_path):
        print("Food.csv not found.")
        return

    try:
        with open(csv_path, mode="r", encoding="utf-8-sig") as file:
            reader = csv.DictReader(file)
            for row in reader:
                title = row.get("Title", "").strip()
                ingredients = row.get("Ingredients", "").strip()
                instructions = row.get("Instructions", "").strip()
                image_name = row.get("Image_Name", "").strip()

                if not title or not ingredients or not instructions or not image_name:
                    print(f"Skipping incomplete row: {row}")
                    continue

                existing_recipe = Recipe.query.filter_by(name=title).first()
                if existing_recipe:
                    print(f"Skipping duplicate recipe: {title}")
                    continue

                new_recipe = Recipe(
                    name=title,
                    ingredients=ingredients,
                    instructions=instructions,
                    image_url=image_name  
                )

                db.session.add(new_recipe)
            db.session.commit()
            print("Recipes successfully populated from Food.csv.")
    except Exception as e:
        print(f"Error while populating recipes: {e}")

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        populate_recipes_from_csv()
