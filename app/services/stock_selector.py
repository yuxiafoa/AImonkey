from typing import List, Dict, Any, Tuple
from app.models.stock import Stock, DailyData
from app.services.formula_parser import FormulaParser
from app.services.formula_executor import FormulaContext, FormulaEvaluator


class StockSelector:
    
    def __init__(self, parser: FormulaParser = None):
        self.parser = parser or FormulaParser()
    
    def select(self, formulas: List[str], stock_ids: List[int], 
               date_start: int, date_end: int, 
               combine_mode: str = 'AND') -> List[Dict[str, Any]]:
        
        if not formulas:
            return []
        
        formula_asts = []
        for formula in formulas:
            valid, error = FormulaParser.validate_formula_syntax(formula)
            if not valid:
                raise ValueError(f"Invalid formula: {formula}, error: {error}")
            
            parser = FormulaParser()
            parser.validate(formula)
            formula_asts.append((formula, parser.get_ast()))
        
        results = []
        
        for stock_id in stock_ids:
            stock = Stock.query.get(stock_id)
            if not stock:
                continue
            
            daily_data = DailyData.query.filter(
                DailyData.stock_id == stock_id,
                DailyData.date >= date_start,
                DailyData.date <= date_end
            ).order_by(DailyData.date).all()
            
            if not daily_data:
                continue
            
            data = {
                'open': [d.open for d in daily_data],
                'high': [d.high for d in daily_data],
                'low': [d.low for d in daily_data],
                'close': [d.close for d in daily_data],
                'volume': [d.volume for d in daily_data],
                'date': [d.date for d in daily_data]
            }
            
            context = FormulaContext(data)
            evaluator = FormulaEvaluator(context)
            
            all_pass = True
            any_pass = False
            values = []
            
            for formula_text, ast in formula_asts:
                result = evaluator.evaluate(ast)
                max_value = max(result) if result else 0.0
                
                if max_value != 0:
                    any_pass = True
                    values.append(max_value)
                else:
                    values.append(0.0)
                
                if combine_mode == 'AND' and max_value == 0:
                    all_pass = False
            
            if combine_mode == 'AND' and all_pass:
                results.append({
                    'stock_id': stock_id,
                    'code': stock.code,
                    'name': stock.name,
                    'values': values,
                    'formulas': formulas
                })
            elif combine_mode == 'OR' and any_pass:
                results.append({
                    'stock_id': stock_id,
                    'code': stock.code,
                    'name': stock.name,
                    'values': values,
                    'formulas': formulas
                })
        
        return results
    
    @staticmethod
    def calculate_formula_for_stock(stock_id: int, formula: str, 
                                    date_start: int = None, 
                                    date_end: int = None) -> List[Dict[str, Any]]:
        
        valid, error = FormulaParser.validate_formula_syntax(formula)
        if not valid:
            raise ValueError(f"Invalid formula: {error}")
        
        parser = FormulaParser()
        parser.validate(formula)
        ast = parser.get_ast()
        
        stock = Stock.query.get(stock_id)
        if not stock:
            raise ValueError(f"Stock not found: {stock_id}")
        
        query = DailyData.query.filter_by(stock_id=stock_id)
        if date_start:
            query = query.filter(DailyData.date >= date_start)
        if date_end:
            query = query.filter(DailyData.date <= date_end)
        
        daily_data = query.order_by(DailyData.date).all()
        
        if not daily_data:
            return []
        
        data = {
            'open': [d.open for d in daily_data],
            'high': [d.high for d in daily_data],
            'low': [d.low for d in daily_data],
            'close': [d.close for d in daily_data],
            'volume': [d.volume for d in daily_data],
            'date': [d.date for d in daily_data]
        }
        
        context = FormulaContext(data)
        evaluator = FormulaEvaluator(context)
        result = evaluator.evaluate(ast)
        
        return [
            {'date': d.date, 'value': v}
            for d, v in zip(daily_data, result)
        ]
