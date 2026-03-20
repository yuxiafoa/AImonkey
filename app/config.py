import os

class Config:
    BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    DATA_DIR = os.path.join(BASE_DIR, 'data')
    DATABASE_PATH = os.path.join(DATA_DIR, 'stock_data.db')
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{DATABASE_PATH}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024
    UPLOAD_FOLDER = DATA_DIR
    
    BACKTEST_DEFAULT_INITIAL_CAPITAL = 100000
    BACKTEST_DEFAULT_COMMISSION = 0.0003
    BACKTEST_DEFAULT_SLIPPAGE = 0.001
