from flask import Blueprint, request, jsonify
from app.services.stock_selector import StockSelector
from app.services.data_service import DataService

selector_bp = Blueprint('selector', __name__)


@selector_bp.route('', methods=['POST'])
def select():
    data = request.get_json()
    formulas = data.get('formulas', [])
    stock_ids = data.get('stock_ids')
    date_start = data.get('date_start')
    date_end = data.get('date_end')
    combine_mode = data.get('combine_mode', 'AND')
    
    if not formulas:
        return jsonify({'success': False, 'message': '请至少提供一个公式'}), 400
    
    if not stock_ids:
        stocks = DataService.get_all_stocks()
        stock_ids = [s.id for s in stocks]
    
    if not date_start or not date_end:
        return jsonify({'success': False, 'message': '请指定日期范围'}), 400
    
    try:
        selector = StockSelector()
        results = selector.select(
            formulas=formulas,
            stock_ids=stock_ids,
            date_start=date_start,
            date_end=date_end,
            combine_mode=combine_mode
        )
        
        return jsonify({
            'success': True,
            'results': results,
            'count': len(results)
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
