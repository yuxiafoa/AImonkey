from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from app.models import db
from sqlalchemy import func


class Stock(db.Model):
    __tablename__ = 'stocks'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), nullable=False, unique=True)
    name = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=db.func.current_timestamp())
    
    daily_data = relationship('DailyData', back_populates='stock', cascade='all, delete-orphan', lazy='dynamic')
    
    __table_args__ = (
        Index('idx_stock_code', 'code'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'data_count': self.daily_data.count()
        }


class DailyData(db.Model):
    __tablename__ = 'daily_data'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_id = Column(Integer, ForeignKey('stocks.id', ondelete='CASCADE'), nullable=False)
    date = Column(Integer, nullable=False)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    
    stock = relationship('Stock', back_populates='daily_data')
    
    __table_args__ = (
        UniqueConstraint('stock_id', 'date', name='uq_stock_date'),
        Index('idx_stock_date', 'stock_id', 'date'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'stock_id': self.stock_id,
            'date': self.date,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume
        }
