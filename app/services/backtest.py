from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
from app.models.stock import Stock, DailyData
from app.services.formula_parser import FormulaParser
from app.services.formula_executor import FormulaContext, FormulaExecutor


class TradeAction(Enum):
    BUY = 1
    SELL = 2


class Trade:
    def __init__(self, action: TradeAction, date: int, price: float, 
                 quantity: int, commission: float, stock_id: int = None, 
                 stock_code: str = None, stock_name: str = None):
        self.action = action
        self.date = date
        self.price = price
        self.quantity = quantity
        self.commission = commission
        self.stock_id = stock_id
        self.stock_code = stock_code
        self.stock_name = stock_name
        self.amount = price * quantity
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'action': self.action.name,
            'date': self.date,
            'price': self.price,
            'quantity': self.quantity,
            'amount': self.amount,
            'commission': self.commission,
            'stock_id': self.stock_id,
            'stock_code': self.stock_code,
            'stock_name': self.stock_name
        }


class BacktestEngine:
    
    def __init__(self, initial_capital: float = 100000.0,
                 commission_rate: float = 0.0003,
                 slippage: float = 0.001):
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.slippage = slippage
    
    def run(self, stock_ids: List[int], formula: str,
            date_start: int, date_end: int,
            buy_condition: str = None,
            sell_condition: str = None) -> Dict[str, Any]:
        
        valid, error = FormulaParser.validate_formula_syntax(formula)
        if not valid:
            raise ValueError(f"Invalid formula: {error}")
        
        parser = FormulaParser()
        parser.validate(formula)
        ast = parser.get_ast()
        
        if ast is None:
            raise ValueError("Failed to parse formula")
        
        trades = []
        equity_curve = []
        current_capital = self.initial_capital
        position = None
        
        all_data = {}
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
            
            all_data[stock_id] = {
                'stock': stock,
                'data': daily_data,
                'close': [d.close for d in daily_data],
                'open': [d.open for d in daily_data],
                'high': [d.high for d in daily_data],
                'low': [d.low for d in daily_data],
                'volume': [d.volume for d in daily_data],
                'dates': [d.date for d in daily_data]
            }
        
        if not all_data:
            return self._generate_empty_result()
        
        max_len = max(len(d['dates']) for d in all_data.values())
        
        for i in range(max_len):
            current_dates = {}
            for stock_id, d in all_data.items():
                if i < len(d['dates']):
                    current_dates[stock_id] = d['dates'][i]
            
            signals = {}
            for stock_id, d in all_data.items():
                if i < len(d['close']):
                    context = FormulaContext({
                        'close': d['close'][:i+1],
                        'open': d['open'][:i+1],
                        'high': d['high'][:i+1],
                        'low': d['low'][:i+1],
                        'volume': d['volume'][:i+1]
                    })
                    result = FormulaExecutor.execute(ast, context)
                    signals[stock_id] = result[-1] if result else 0.0
            
            for stock_id, signal in signals.items():
                if position is None and signal != 0:
                    d = all_data[stock_id]
                    stock = d['stock']
                    
                    if i + 1 < len(d['dates']):
                        next_date = d['dates'][i + 1]
                        next_open = d['open'][i + 1]
                        
                        buy_price = next_open * (1 + self.slippage)
                        max_quantity = int(current_capital / buy_price)
                        
                        if max_quantity > 0:
                            commission = buy_price * max_quantity * self.commission_rate
                            
                            trades.append(Trade(
                                action=TradeAction.BUY,
                                date=next_date,
                                price=buy_price,
                                quantity=max_quantity,
                                commission=commission,
                                stock_id=stock_id,
                                stock_code=stock.code,
                                stock_name=stock.name
                            ))
                            
                            position = {
                                'stock_id': stock_id,
                                'quantity': max_quantity,
                                'buy_price': buy_price,
                                'buy_date': next_date,
                                'cost': buy_price * max_quantity + commission
                            }
                            current_capital -= (buy_price * max_quantity + commission)
                
                elif position is not None and position['stock_id'] == stock_id:
                    if signal == 0 and i > 0:
                        prev_signal = signals.get(stock_id, 0)
                        if prev_signal != 0:
                            d = all_data[stock_id]
                            stock = d['stock']
                            
                            if i + 1 < len(d['dates']):
                                next_date = d['dates'][i + 1]
                                next_open = d['open'][i + 1]
                                
                                sell_price = next_open * (1 - self.slippage)
                                sell_amount = sell_price * position['quantity']
                                commission = sell_amount * self.commission_rate
                                
                                trades.append(Trade(
                                    action=TradeAction.SELL,
                                    date=next_date,
                                    price=sell_price,
                                    quantity=position['quantity'],
                                    commission=commission,
                                    stock_id=stock_id,
                                    stock_code=stock.code,
                                    stock_name=stock.name
                                ))
                                
                                current_capital += (sell_amount - commission)
                                position = None
            
            total_asset = current_capital
            if position:
                stock_id = position['stock_id']
                d = all_data[stock_id]
                if i < len(d['close']):
                    current_price = d['close'][i]
                    total_asset += current_price * position['quantity']
            
            if all_data:
                first_stock_data = list(all_data.values())[0]
                if i < len(first_stock_data['dates']):
                    equity_curve.append({
                        'date': first_stock_data['dates'][i],
                        'asset': total_asset,
                        'cash': current_capital,
                        'position_value': total_asset - current_capital
                    })
        
        if position:
            d = all_data[position['stock_id']]
            stock = d['stock']
            last_date = d['dates'][-1] if d['dates'] else date_end
            last_close = d['close'][-1] if d['close'] else 0
            
            sell_price = last_close * (1 - self.slippage)
            sell_amount = sell_price * position['quantity']
            commission = sell_amount * self.commission_rate
            
            trades.append(Trade(
                action=TradeAction.SELL,
                date=last_date,
                price=sell_price,
                quantity=position['quantity'],
                commission=commission,
                stock_id=position['stock_id'],
                stock_code=stock.code,
                stock_name=stock.name
            ))
            
            current_capital += (sell_amount - commission)
            position = None
        
        final_asset = current_capital
        
        metrics = self._calculate_metrics(final_asset, equity_curve, trades)
        
        return {
            'success': True,
            'initial_capital': self.initial_capital,
            'final_asset': final_asset,
            'metrics': metrics,
            'trades': [t.to_dict() for t in trades],
            'equity_curve': equity_curve
        }
    
    def _generate_empty_result(self) -> Dict[str, Any]:
        return {
            'success': True,
            'initial_capital': self.initial_capital,
            'final_asset': self.initial_capital,
            'metrics': {
                'total_return': 0.0,
                'annual_return': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0,
                'win_rate': 0.0,
                'total_trades': 0,
                'profit_loss': 0.0
            },
            'trades': [],
            'equity_curve': []
        }
    
    def _calculate_metrics(self, final_asset: float, equity_curve: List[Dict],
                          trades: List[Trade]) -> Dict[str, float]:
        
        total_return = (final_asset - self.initial_capital) / self.initial_capital * 100
        
        if len(equity_curve) > 1:
            days = equity_curve[-1]['date'] - equity_curve[0]['date']
            years = days / 365.0
            if years > 0:
                annual_return = ((final_asset / self.initial_capital) ** (1 / years) - 1) * 100
            else:
                annual_return = 0.0
        else:
            annual_return = 0.0
        
        returns = []
        for i in range(1, len(equity_curve)):
            daily_return = (equity_curve[i]['asset'] - equity_curve[i-1]['asset']) / equity_curve[i-1]['asset']
            returns.append(daily_return)
        
        if returns:
            avg_return = sum(returns) / len(returns)
            std_return = (sum((r - avg_return) ** 2 for r in returns) / len(returns)) ** 0.5
            if std_return > 0:
                sharpe_ratio = (avg_return / std_return) * (252 ** 0.5)
            else:
                sharpe_ratio = 0.0
        else:
            sharpe_ratio = 0.0
        
        max_asset = self.initial_capital
        max_drawdown = 0.0
        for point in equity_curve:
            if point['asset'] > max_asset:
                max_asset = point['asset']
            drawdown = (max_asset - point['asset']) / max_asset * 100
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        buy_trades = [t for t in trades if t.action == TradeAction.BUY]
        sell_trades = [t for t in trades if t.action == TradeAction.SELL]
        
        winning_trades = 0
        total_profit_loss = 0.0
        
        if len(sell_trades) > 0:
            buy_idx = 0
            for sell in sell_trades:
                if buy_idx < len(buy_trades) and buy_trades[buy_idx].stock_id == sell.stock_id:
                    buy_trade = buy_trades[buy_idx]
                    profit = (sell.price - buy_trade.price) * sell.quantity - sell.commission - buy_trade.commission
                    total_profit_loss += profit
                    if profit > 0:
                        winning_trades += 1
                    buy_idx += 1
        
        total_trades = len(sell_trades)
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0
        
        return {
            'total_return': round(total_return, 2),
            'annual_return': round(annual_return, 2),
            'sharpe_ratio': round(sharpe_ratio, 2),
            'max_drawdown': round(max_drawdown, 2),
            'win_rate': round(win_rate, 2),
            'total_trades': total_trades,
            'profit_loss': round(total_profit_loss, 2)
        }
