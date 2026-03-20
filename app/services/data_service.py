import zipfile
import io
import re
from typing import List, Tuple, Optional
from app.models import db
from app.models.stock import Stock, DailyData


class DataService:
    
    @staticmethod
    def parse_tdx_line(line: str) -> Optional[Tuple[int, float, float, float, float, float]]:
        parts = line.strip().split(',')
        if len(parts) != 6:
            return None
        
        try:
            date = int(parts[0])
            open_price = float(parts[1])
            high = float(parts[2])
            low = float(parts[3])
            close = float(parts[4])
            volume = float(parts[5])
            return (date, open_price, high, low, close, volume)
        except (ValueError, IndexError):
            return None
    
    @staticmethod
    def extract_stock_code_from_filename(filename: str) -> Tuple[str, str]:
        name = filename.replace('.txt', '').replace('.TXT', '')
        code = name[:6] if len(name) >= 6 else name
        stock_name = name[6:] if len(name) > 6 else code
        return code, stock_name.strip()
    
    @staticmethod
    def import_zip(file_stream) -> Tuple[int, int, List[str]]:
        imported_count = 0
        error_count = 0
        errors = []
        
        with zipfile.ZipFile(file_stream, 'r') as zf:
            txt_files = [f for f in zf.namelist() if f.lower().endswith('.txt')]
            
            for txt_file in txt_files:
                try:
                    content = zf.read(txt_file).decode('gbk', errors='ignore')
                    code, name = DataService.extract_stock_code_from_filename(txt_file)
                    
                    if not code:
                        error_count += 1
                        errors.append(f"{txt_file}: 无法识别股票代码")
                        continue
                    
                    stock = Stock.query.filter_by(code=code).first()
                    if not stock:
                        stock = Stock(code=code, name=name or code)
                        db.session.add(stock)
                        db.session.flush()
                    
                    daily_records = []
                    for line in content.split('\n'):
                        line = line.strip()
                        if not line:
                            continue
                        
                        parsed = DataService.parse_tdx_line(line)
                        if parsed:
                            date, open_p, high, low, close, volume = parsed
                            existing = DailyData.query.filter_by(stock_id=stock.id, date=date).first()
                            if existing:
                                existing.open = open_p
                                existing.high = high
                                existing.low = low
                                existing.close = close
                                existing.volume = volume
                            else:
                                daily_records.append(DailyData(
                                    stock_id=stock.id,
                                    date=date,
                                    open=open_p,
                                    high=high,
                                    low=low,
                                    close=close,
                                    volume=volume
                                ))
                    
                    if daily_records:
                        db.session.add_all(daily_records)
                        imported_count += 1
                        
                except Exception as e:
                    error_count += 1
                    errors.append(f"{txt_file}: {str(e)}")
        
        db.session.commit()
        return imported_count, error_count, errors
    
    @staticmethod
    def get_all_stocks():
        return Stock.query.order_by(Stock.code).all()
    
    @staticmethod
    def get_stock_by_id(stock_id: int) -> Optional[Stock]:
        return Stock.query.get(stock_id)
    
    @staticmethod
    def delete_stock(stock_id: int) -> bool:
        stock = Stock.query.get(stock_id)
        if stock:
            db.session.delete(stock)
            db.session.commit()
            return True
        return False
    
    @staticmethod
    def get_stock_data(stock_id: int, date_start: int = None, date_end: int = None):
        query = DailyData.query.filter_by(stock_id=stock_id)
        
        if date_start:
            query = query.filter(DailyData.date >= date_start)
        if date_end:
            query = query.filter(DailyData.date <= date_end)
        
        return query.order_by(DailyData.date).all()
