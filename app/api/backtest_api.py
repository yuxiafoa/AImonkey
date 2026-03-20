from flask import Blueprint, request, jsonify, send_file, Response
from app.services.backtest import BacktestEngine
from app.config import Config
import io
import csv
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

backtest_bp = Blueprint('backtest', __name__)

_backtest_results = {}


@backtest_bp.route('/run', methods=['POST'])
def run():
    data = request.get_json()
    stock_ids = data.get('stock_ids', [])
    formula = data.get('formula')
    date_start = data.get('date_start')
    date_end = data.get('date_end')
    initial_capital = data.get('initial_capital', Config.BACKTEST_DEFAULT_INITIAL_CAPITAL)
    commission_rate = data.get('commission_rate', Config.BACKTEST_DEFAULT_COMMISSION)
    slippage = data.get('slippage', Config.BACKTEST_DEFAULT_SLIPPAGE)
    
    if not formula:
        return jsonify({'success': False, 'message': '请提供选股公式'}), 400
    
    if not stock_ids:
        return jsonify({'success': False, 'message': '请选择股票'}), 400
    
    if not date_start or not date_end:
        return jsonify({'success': False, 'message': '请指定回测日期范围'}), 400
    
    try:
        engine = BacktestEngine(
            initial_capital=initial_capital,
            commission_rate=commission_rate,
            slippage=slippage
        )
        
        result = engine.run(
            stock_ids=stock_ids,
            formula=formula,
            date_start=date_start,
            date_end=date_end
        )
        
        import uuid
        result_id = str(uuid.uuid4())[:8]
        _backtest_results[result_id] = result
        
        result['id'] = result_id
        del result['trades']
        del result['equity_curve']
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@backtest_bp.route('/report/<result_id>', methods=['GET'])
def get_report(result_id):
    if result_id not in _backtest_results:
        return jsonify({'success': False, 'message': '回测结果不存在'}), 404
    
    result = _backtest_results[result_id]
    
    return jsonify({
        'success': True,
        'initial_capital': result['initial_capital'],
        'final_asset': result['final_asset'],
        'metrics': result['metrics'],
        'trades': result['trades'],
        'equity_curve': result['equity_curve']
    })


@backtest_bp.route('/export/<result_id>', methods=['GET'])
def export_report(result_id):
    if result_id not in _backtest_results:
        return jsonify({'success': False, 'message': '回测结果不存在'}), 404
    
    format_type = request.args.get('format', 'pdf')
    result = _backtest_results[result_id]
    
    if format_type == 'csv':
        return _export_csv(result)
    else:
        return _export_pdf(result)


def _export_csv(result: dict) -> Response:
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(['指标', '值'])
    writer.writerow(['初始资金', result['initial_capital']])
    writer.writerow(['最终资产', result['final_asset']])
    writer.writerow(['总收益率', f"{result['metrics']['total_return']}%"])
    writer.writerow(['年化收益率', f"{result['metrics']['annual_return']}%"])
    writer.writerow(['夏普比率', result['metrics']['sharpe_ratio']])
    writer.writerow(['最大回撤', f"{result['metrics']['max_drawdown']}%"])
    writer.writerow(['胜率', f"{result['metrics']['win_rate']}%"])
    writer.writerow([])
    
    writer.writerow(['交易记录'])
    writer.writerow(['日期', '股票代码', '股票名称', '操作', '价格', '数量', '金额', '佣金'])
    
    for trade in result['trades']:
        writer.writerow([
            trade['date'],
            trade['stock_code'],
            trade['stock_name'],
            trade['action'],
            trade['price'],
            trade['quantity'],
            trade['amount'],
            trade['commission']
        ])
    
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment;filename=backtest_report_{result_id}.csv'}
    )


def _export_pdf(result: dict) -> Response:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []
    
    elements.append(Paragraph('A股回测报告', styles['Title']))
    elements.append(Spacer(1, 20))
    
    metrics_data = [
        ['指标', '值'],
        ['初始资金', f"{result['initial_capital']:.2f}"],
        ['最终资产', f"{result['final_asset']:.2f}"],
        ['总收益率', f"{result['metrics']['total_return']}%"],
        ['年化收益率', f"{result['metrics']['annual_return']}%"],
        ['夏普比率', f"{result['metrics']['sharpe_ratio']:.2f}"],
        ['最大回撤', f"{result['metrics']['max_drawdown']}%"],
        ['胜率', f"{result['metrics']['win_rate']}%"],
        ['总交易次数', result['metrics']['total_trades']],
    ]
    
    table = Table(metrics_data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(table)
    elements.append(Spacer(1, 20))
    
    if result['trades']:
        elements.append(Paragraph('交易记录', styles['Heading2']))
        
        trade_data = [['日期', '股票', '操作', '价格', '数量', '金额']]
        for trade in result['trades'][:20]:
            trade_data.append([
                str(trade['date']),
                f"{trade['stock_code']}({trade['stock_name']})",
                trade['action'],
                f"{trade['price']:.2f}",
                trade['quantity'],
                f"{trade['amount']:.2f}"
            ])
        
        trade_table = Table(trade_data)
        trade_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ]))
        elements.append(trade_table)
    
    doc.build(elements)
    buffer.seek(0)
    
    return Response(
        buffer.getvalue(),
        mimetype='application/pdf',
        headers={'Content-Disposition': f'attachment;filename=backtest_report_{result_id}.pdf'}
    )
