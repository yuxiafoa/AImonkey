import zipfile
import io
import re
from typing import List, Tuple, Optional
from app.models import db
from app.models.stock import Stock, DailyData


class DataService:
    
    @staticmethod
    def parse_tdx_line(line: str) -> Optional[Tuple[int, float, float, float, float, float]]:
        line = line.strip()
        if not line:
            return None
        
        if '/' in line and ',' in line:
            parts = line.split(',')
        elif '/' in line:
            parts = line.split('/')
        else:
            parts = line.split(',')
        
        if len(parts) < 6:
            return None
        
        try:
            date_str = parts[0]
            if '-' in date_str:
                date = int(date_str.replace('-', ''))
            elif '/' in date_str:
                date = int(date_str.replace('/', ''))
            else:
                date = int(date_str)
            
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
        name = name.replace('\\', '/').split('/')[-1]
        
        patterns = [
            (r'^([A-Z]{2})(\d{6})$', 'prefix'),
            (r'^(\d{6})\.([A-Z]{2})$', 'suffix'),
            (r'^([A-Z]{2})#(\d{6})$', 'prefix_hash'),
            (r'^(\d{6})[._]?([A-Z]{2})$', 'suffix_simple'),
            (r'^SZ#(\d{6})$', 'sz'),
            (r'^SH#(\d{6})$', 'sh'),
            (r'^SZ#(\d{6})$', 'sz_hash'),
            (r'^SH#(\d{6})$', 'sh_hash'),
        ]
        
        for pattern, style in patterns:
            match = re.match(pattern, name, re.IGNORECASE)
            if match:
                parts = match.groups()
                if style == 'prefix':
                    return parts[0].upper() + parts[1], parts[0].upper() + parts[1]
                elif style == 'suffix':
                    return parts[1].upper() + parts[0], parts[1].upper() + parts[0]
                elif style == 'prefix_hash':
                    return parts[0].upper() + parts[1], parts[0].upper() + parts[1]
                elif style == 'suffix_simple':
                    return parts[1].upper() + parts[0], parts[1].upper() + parts[0]
                elif style == 'sz':
                    return 'SZ' + parts[0], 'SZ' + parts[0]
                elif style == 'sh':
                    return 'SH' + parts[0], 'SH' + parts[0]
        
        code = re.sub(r'[^0-9]', '', name)
        if len(code) >= 6:
            return code[:6], code[:6]
        
        return name[:6] if len(name) >= 6 else name, name
    
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
    
    @staticmethod
    def import_txt_file(file_stream) -> dict:
        try:
            filename = getattr(file_stream, 'name', 'unknown.txt')
            content = file_stream.read().decode('gbk', errors='ignore')
            lines = content.split('\n')
            
            if len(lines) < 3:
                return {'success': False, 'message': '文件数据行数不足'}
            
            code, name = DataService.extract_stock_code_from_filename(filename)
            
            if not code:
                return {'success': False, 'message': '无法识别股票代码'}
            
            stock = Stock.query.filter_by(code=code).first()
            if not stock:
                stock = Stock(code=code, name=name or code)
                db.session.add(stock)
                db.session.flush()
            
            daily_records = []
            for i, line in enumerate(lines):
                line = line.strip()
                if not line:
                    continue
                
                if i < 2:
                    continue
                
                parts = re.split(r'\s+', line)
                if len(parts) < 6:
                    continue
                
                try:
                    date_str = parts[0]
                    if '-' in date_str:
                        date = int(date_str.replace('-', ''))
                    elif '/' in date_str:
                        date = int(date_str.replace('/', ''))
                    else:
                        date = int(date_str)
                    
                    open_price = float(parts[1])
                    high = float(parts[2])
                    low = float(parts[3])
                    close = float(parts[4])
                    volume = float(parts[5])
                    
                    existing = DailyData.query.filter_by(stock_id=stock.id, date=date).first()
                    if existing:
                        existing.open = open_price
                        existing.high = high
                        existing.low = low
                        existing.close = close
                        existing.volume = volume
                    else:
                        daily_records.append(DailyData(
                            stock_id=stock.id,
                            date=date,
                            open=open_price,
                            high=high,
                            low=low,
                            close=close,
                            volume=volume
                        ))
                except (ValueError, IndexError):
                    continue
            
            if daily_records:
                db.session.add_all(daily_records)
            
            db.session.commit()
            
            return {
                'success': True,
                'imported_count': 1,
                'records_count': len(daily_records),
                'code': code,
                'name': name
            }
            
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': str(e)}
