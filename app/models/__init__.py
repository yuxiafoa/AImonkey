from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from app.models.stock import Stock, DailyData

__all__ = ['db', 'Stock', 'DailyData']
