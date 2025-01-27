from datetime import datetime
from config import db, mm

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    fridge_items = db.relationship('FridgeItem', backref='owner', lazy=True, cascade="all, delete-orphan")
    saved_recipes = db.relationship('SavedRecipe', backref='owner', lazy=True, cascade="all, delete-orphan")

class FridgeItem(db.Model):
    __tablename__ = 'fridge_item'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    item_name = db.Column(db.String(100), nullable=False)
    brand = db.Column(db.String(100), nullable=True)
    quantity = db.Column(db.String(50), nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)

class Recipe(db.Model):
    __tablename__ = 'recipe'
    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(db.Integer, unique=True, nullable=False)  
    name = db.Column(db.String(100), nullable=False)
    ingredients = db.Column(db.Text, nullable=False)
    instructions = db.Column(db.Text, nullable=False)  
    image_url = db.Column(db.String(300), nullable=True)    
    youtube_url = db.Column(db.String(300), nullable=True)  
    saved_recipes = db.relationship('SavedRecipe', backref='recipe', lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "recipe_id": self.recipe_id,
            "name": self.name,
            "ingredients": self.ingredients,
            "instructions": self.instructions,
            "image_url": self.image_url,
            "youtube_url": self.youtube_url
        }

class SavedRecipe(db.Model):
    __tablename__ = 'saved_recipe'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipe.id'), nullable=False)
    __table_args__ = (db.UniqueConstraint('user_id', 'recipe_id', name='_user_recipe_uc'),)

class UserSchema(mm.SQLAlchemyAutoSchema):
    class Meta:
        model = User
        load_instance = True

class RecipeSchema(mm.SQLAlchemyAutoSchema):
    class Meta:
        model = Recipe

class SavedRecipeSchema(mm.SQLAlchemyAutoSchema):
    class Meta:
        model = SavedRecipe

user_schema = UserSchema()
recipe_schema = RecipeSchema()
saved_recipe_schema = SavedRecipeSchema()
