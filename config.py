import pathlib
import os
import dotenv
from flask import Flask
from flask_cors import CORS 
from flask_marshmallow import Marshmallow
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
mm = Marshmallow()

def create_app():
    this_app = Flask(__name__)
    this_dir = pathlib.Path(__file__)
    dotenv.load_dotenv(this_dir / pathlib.Path(".flaskenv"))
    this_app.config.from_prefixed_env()
    
    db_file = this_dir.parent / pathlib.Path(
        f"{this_app.config.get('FLASK_DATABASE_FILE', 'recipe_database')}.sqlite3"
    )
    this_app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "default_secret")
    this_app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_file}"
    this_app.config["JWT_SECRET_KEY"] = os.getenv("FLASK_JWT_SECRET_KEY", "default_jwt_secret")
    this_app.config["SQLALCHEMY_ECHO"] = os.getenv("FLASK_SQLALCHEMY_ECHO", False)
    this_app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = os.getenv("FLASK_SQLALCHEMY_TRACK_MODIFICATIONS", False)
    
    CORS(
        this_app,
        resources={r"/*": {"origins": [
            "http://localhost:5500",
            "http://127.0.0.1:5500",
            "http://[::]:5500"
            "https://your-netlify-subdomain.netlify.app",
            "https://recipesapps.com",
            "https://www.recipesapps.com"
        ]}},
        supports_credentials=True
    )
    
    db.init_app(this_app)
    mm.init_app(this_app)
    
    from model import User, Recipe, SavedRecipe, FridgeItem
    migrate = Migrate(this_app, db)
    if not db_file.exists():
        with this_app.app_context():
            db.create_all()
    
    return this_app
