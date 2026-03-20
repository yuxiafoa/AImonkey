from flask import Flask
from flask_cors import CORS
from app.config import Config
from app.models import db
import os


def create_app(config_class=Config):
    base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    template_dir = os.path.join(base_dir, 'templates')
    static_dir = os.path.join(base_dir, 'static')
    
    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
    app.config.from_object(config_class)
    
    CORS(app)
    db.init_app(app)
    
    with app.app_context():
        db.create_all()
    
    from app.api import data_bp, formula_bp, selector_bp, backtest_bp
    app.register_blueprint(data_bp, url_prefix='/api/data')
    app.register_blueprint(formula_bp, url_prefix='/api/formula')
    app.register_blueprint(selector_bp, url_prefix='/api/select')
    app.register_blueprint(backtest_bp, url_prefix='/api/backtest')
    
    @app.route('/')
    def index():
        from flask import render_template
        return render_template('index.html')
    
    return app
