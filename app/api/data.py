from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import os
from app.services.data_service import DataService

data_bp = Blueprint('data', __name__)


@data_bp.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '没有上传文件'}), 400
    
    files = request.files.getlist('file')
    if not files or all(f.filename == '' for f in files):
        return jsonify({'success': False, 'message': '文件名为空'}), 400
    
    imported_count = 0
    error_count = 0
    errors = []
    
    for file in files:
        if file and file.filename.lower().endswith('.txt'):
            filename = secure_filename(file.filename)
            temp_path = os.path.join('/tmp', filename)
            
            try:
                file.save(temp_path)
                with open(temp_path, 'rb') as f:
                    result = DataService.import_txt_file(f)
                
                if result['success']:
                    imported_count += result['imported_count']
                else:
                    error_count += 1
                    errors.append(f"{filename}: {result['message']}")
                
                os.remove(temp_path)
            except Exception as e:
                error_count += 1
                errors.append(f"{filename}: {str(e)}")
                if os.path.exists(temp_path):
                    os.remove(temp_path)
        elif file.filename:
            error_count += 1
            errors.append(f"{file.filename}: 只支持TXT文件")
    
    return jsonify({
        'success': True,
        'message': f'成功导入{imported_count}只股票，{error_count}个错误',
        'imported_count': imported_count,
        'error_count': error_count,
        'errors': errors
    })


@data_bp.route('/stocks', methods=['GET'])
def get_stocks():
    try:
        stocks = DataService.get_all_stocks()
        return jsonify({
            'success': True,
            'stocks': [s.to_dict() for s in stocks]
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@data_bp.route('/stocks/<int:stock_id>', methods=['DELETE'])
def delete_stock(stock_id):
    try:
        success = DataService.delete_stock(stock_id)
        if success:
            return jsonify({'success': True, 'message': '删除成功'})
        else:
            return jsonify({'success': False, 'message': '股票不存在'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@data_bp.route('/stocks/<int:stock_id>/data', methods=['GET'])
def get_stock_data(stock_id):
    try:
        date_start = request.args.get('date_start', type=int)
        date_end = request.args.get('date_end', type=int)
        
        data = DataService.get_stock_data(stock_id, date_start, date_end)
        
        return jsonify({
            'success': True,
            'data': [d.to_dict() for d in data]
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
