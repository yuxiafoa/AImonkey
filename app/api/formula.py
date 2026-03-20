from flask import Blueprint, request, jsonify
from app.services.formula_parser import FormulaParser
from app.services.stock_selector import StockSelector
from app.services.data_service import DataService

formula_bp = Blueprint('formula', __name__)


@formula_bp.route('/validate', methods=['POST'])
def validate():
    data = request.get_json()
    formula = data.get('formula', '')
    
    if not formula:
        return jsonify({'valid': False, 'error': {'message': '公式不能为空'}}), 400
    
    valid, error = FormulaParser.validate_formula_syntax(formula)
    
    if valid:
        parser = FormulaParser()
        parser.validate(formula)
        ast = parser.get_ast()
        
        variables = FormulaParser.get_variables(ast) if ast else set()
        functions = FormulaParser.get_functions(ast) if ast else set()
        
        return jsonify({
            'valid': True,
            'variables': list(variables),
            'functions': list(functions)
        })
    else:
        return jsonify({'valid': False, 'error': error})


@formula_bp.route('/execute', methods=['POST'])
def execute():
    data = request.get_json()
    stock_id = data.get('stock_id')
    formula = data.get('formula')
    date = data.get('date')
    
    if not stock_id or not formula:
        return jsonify({'success': False, 'error': '缺少必要参数'}), 400
    
    try:
        result = StockSelector.calculate_formula_for_stock(stock_id, formula)
        
        if date:
            filtered = [r for r in result if r['date'] == date]
            if filtered:
                return jsonify({'success': True, 'result': filtered[0]['value']})
            return jsonify({'success': True, 'result': None, 'message': '未找到指定日期数据'})
        
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
