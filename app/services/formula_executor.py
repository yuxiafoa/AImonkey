from typing import Dict, List, Any, Optional, Tuple
from app.services.formula_parser import ASTNode, NumberNode, VarNode, BinaryOpNode, FunctionCallNode


class FormulaContext:
    def __init__(self, data: Dict[str, List[float]]):
        self.data = data
        self.length = len(data.get('close', []))
    
    def get_var(self, name: str) -> List[float]:
        name = name.upper()
        if name == 'CLOSE' or name == 'C':
            return self.data.get('close', [0.0] * self.length)
        elif name == 'OPEN' or name == 'O':
            return self.data.get('open', [0.0] * self.length)
        elif name == 'HIGH' or name == 'H':
            return self.data.get('high', [0.0] * self.length)
        elif name == 'LOW' or name == 'L':
            return self.data.get('low', [0.0] * self.length)
        elif name == 'VOLUME' or name == 'V':
            return self.data.get('volume', [0.0] * self.length)
        return [0.0] * self.length
    
    def _ensure_length(self, arr: List[float]) -> List[float]:
        if len(arr) < self.length:
            return arr + [0.0] * (self.length - len(arr))
        return arr[:self.length]


class FormulaEvaluator:
    
    def __init__(self, context: FormulaContext):
        self.context = context
    
    def evaluate(self, ast: ASTNode) -> List[float]:
        if isinstance(ast, NumberNode):
            return [float(ast.value)] * self.context.length
        
        if isinstance(ast, VarNode):
            return self.context.get_var(ast.name)
        
        if isinstance(ast, BinaryOpNode):
            return self._evaluate_binary_op(ast)
        
        if isinstance(ast, FunctionCallNode):
            return self._evaluate_function(ast)
        
        return [0.0] * self.context.length
    
    def _evaluate_binary_op(self, node: BinaryOpNode) -> List[float]:
        left = self._ensure_array(self.evaluate(node.left))
        right = self._ensure_array(self.evaluate(node.right))
        
        if len(left) != len(right):
            max_len = max(len(left), len(right))
            left = self._pad_array(left, max_len)
            right = self._pad_array(right, max_len)
        
        op = node.op
        if op == '+':
            return [a + b for a, b in zip(left, right)]
        elif op == '-':
            return [a - b for a, b in zip(left, right)]
        elif op == '*':
            return [a * b for a, b in zip(left, right)]
        elif op == '/':
            return [a / b if b != 0 else 0.0 for a, b in zip(left, right)]
        elif op == '>':
            return [1.0 if a > b else 0.0 for a, b in zip(left, right)]
        elif op == '<':
            return [1.0 if a < b else 0.0 for a, b in zip(left, right)]
        elif op == '>=':
            return [1.0 if a >= b else 0.0 for a, b in zip(left, right)]
        elif op == '<=':
            return [1.0 if a <= b else 0.0 for a, b in zip(left, right)]
        elif op == '==':
            return [1.0 if a == b else 0.0 for a, b in zip(left, right)]
        elif op == '!=':
            return [1.0 if a != b else 0.0 for a, b in zip(left, right)]
        elif op == 'AND':
            return [1.0 if (a != 0 and b != 0) else 0.0 for a, b in zip(left, right)]
        elif op == 'OR':
            return [1.0 if (a != 0 or b != 0) else 0.0 for a, b in zip(left, right)]
        
        return [0.0] * len(left)
    
    def _evaluate_function(self, node: FunctionCallNode) -> List[float]:
        func_name = node.name
        args = [self._ensure_array(self.evaluate(arg)) for arg in node.args]
        
        if func_name == 'MA':
            return self._ma(args[0] if args else self.context.get_var('CLOSE'), int(args[1][0]) if len(args) > 1 else 5)
        elif func_name == 'EMA':
            return self._ema(args[0] if args else self.context.get_var('CLOSE'), int(args[1][0]) if len(args) > 1 else 12)
        elif func_name == 'MACD':
            fast = int(args[1][0]) if len(args) > 1 else 12
            slow = int(args[2][0]) if len(args) > 2 else 26
            signal = int(args[3][0]) if len(args) > 3 else 9
            return self._macd(args[0] if args else self.context.get_var('CLOSE'), fast, slow, signal)
        elif func_name == 'KDJ':
            n = int(args[3][0]) if len(args) > 3 else 9
            m1 = int(args[4][0]) if len(args) > 4 else 3
            m2 = int(args[5][0]) if len(args) > 5 else 3
            return self._kdj(n, m1, m2)
        elif func_name == 'RSI':
            return self._rsi(args[0] if args else self.context.get_var('CLOSE'), int(args[1][0]) if len(args) > 1 else 14)
        elif func_name == 'BOLL':
            n = int(args[1][0]) if len(args) > 1 else 20
            k = int(args[2][0]) if len(args) > 2 else 2
            return self._boll(args[0] if args else self.context.get_var('CLOSE'), n, k)
        elif func_name == 'COUNT':
            cond = args[0]
            n = int(args[1][0]) if len(args) > 1 else 1
            return self._count(cond, n)
        elif func_name == 'REF':
            val = args[0]
            n = int(args[1][0]) if len(args) > 1 else 1
            return self._ref(val, n)
        elif func_name == 'ABS':
            return [abs(v) for v in args[0]]
        elif func_name == 'MAX':
            return [max(a, b) for a, b in zip(args[0], args[1])]
        elif func_name == 'MIN':
            return [min(a, b) for a, b in zip(args[0], args[1])]
        elif func_name == 'ATAN':
            import math
            return [math.atan(v) for v in args[0]]
        
        return [0.0] * self.context.length
    
    def _ensure_array(self, arr: List[float]) -> List[float]:
        return arr if isinstance(arr, list) else [arr]
    
    def _pad_array(self, arr: List[float], length: int) -> List[float]:
        return arr + [0.0] * (length - len(arr))
    
    def _ma(self, data: List[float], n: int) -> List[float]:
        result = []
        for i in range(len(data)):
            if i < n - 1:
                result.append(sum(data[:i+1]) / (i+1))
            else:
                result.append(sum(data[i-n+1:i+1]) / n)
        return result
    
    def _ema(self, data: List[float], n: int) -> List[float]:
        result = []
        k = 2.0 / (n + 1)
        
        for i in range(len(data)):
            if i == 0:
                result.append(data[0])
            elif i < n - 1:
                sma = sum(data[:i+1]) / (i+1)
                result.append(sma)
            else:
                result.append(data[i] * k + result[-1] * (1 - k))
        
        return result
    
    def _macd(self, data: List[float], fast: int, slow: int, signal: int) -> List[float]:
        ema_fast = self._ema(data, fast)
        ema_slow = self._ema(data, slow)
        diff = [f - s for f, s in zip(ema_fast, ema_slow)]
        dea = self._ema(diff, signal)
        bar = [(d - de) * 2 for d, de in zip(diff, dea)]
        
        return bar
    
    def _kdj(self, n: int, m1: int, m2: int) -> List[float]:
        high = self.context.data.get('high', [0.0] * self.context.length)
        low = self.context.data.get('low', [0.0] * self.context.length)
        close = self.context.data.get('close', [0.0] * self.context.length)
        
        rsv = []
        for i in range(len(close)):
            if i < n - 1:
                rsv.append(50.0)
            else:
                h_n = max(high[i-n+1:i+1])
                l_n = min(low[i-n+1:i+1])
                if h_n == l_n:
                    rsv.append(50.0)
                else:
                    rsv.append((close[i] - l_n) / (h_n - l_n) * 100)
        
        k = [50.0]
        d = [50.0]
        for i in range(1, len(rsv)):
            k.append((m1 - 1) / m1 * k[-1] + 1 / m1 * rsv[i])
            d.append((m2 - 1) / m2 * d[-1] + 1 / m2 * k[i])
        
        j = [3 * k[i] - 2 * d[i] for i in range(len(k))]
        
        return j
    
    def _rsi(self, data: List[float], n: int) -> List[float]:
        result = []
        gains = [0.0]
        losses = [0.0]
        
        for i in range(1, len(data)):
            diff = data[i] - data[i-1]
            gains.append(max(diff, 0))
            losses.append(max(-diff, 0))
        
        for i in range(len(data)):
            if i < n - 1:
                avg_gain = sum(gains[:i+1]) / (i+1)
                avg_loss = sum(losses[:i+1]) / (i+1)
            else:
                avg_gain = sum(gains[i-n+1:i+1]) / n
                avg_loss = sum(losses[i-n+1:i+1]) / n
            
            if avg_loss == 0:
                result.append(100.0)
            else:
                rs = avg_gain / avg_loss
                result.append(100.0 - 100.0 / (1 + rs))
        
        return result
    
    def _boll(self, data: List[float], n: int, k: int) -> List[float]:
        middle = self._ma(data, n)
        std = []
        for i in range(len(data)):
            if i < n - 1:
                std.append(0.0)
            else:
                mean = middle[i]
                variance = sum((data[j] - mean) ** 2 for j in range(i-n+1, i+1)) / n
                std.append(variance ** 0.5)
        
        upper = [m + k * s for m, s in zip(middle, std)]
        lower = [m - k * s for m, s in zip(middle, std)]
        
        return lower
    
    def _count(self, cond: List[float], n: int) -> List[float]:
        result = []
        for i in range(len(cond)):
            if i < n - 1:
                count = sum(1 for v in cond[:i+1] if v != 0)
            else:
                count = sum(1 for v in cond[i-n+1:i+1] if v != 0)
            result.append(float(count))
        return result
    
    def _ref(self, data: List[float], n: int) -> List[float]:
        result = [0.0] * n + data[:-n] if len(data) > n else [0.0] * len(data)
        return result


class FormulaExecutor:
    
    @staticmethod
    def execute(ast: ASTNode, context: FormulaContext) -> List[float]:
        evaluator = FormulaEvaluator(context)
        return evaluator.evaluate(ast)
    
    @staticmethod
    def execute_single(formula: str, data: Dict[str, List[float]], date_idx: int) -> float:
        from app.services.formula_parser import FormulaParser
        
        valid, error = FormulaParser.validate_formula_syntax(formula)
        if not valid:
            raise ValueError(f"Formula syntax error: {error}")
        
        context = FormulaContext(data)
        
        parser = FormulaParser()
        valid, _ = parser.validate(formula)
        if not valid:
            raise ValueError("Failed to parse formula")
        
        ast = parser.get_ast()
        if ast is None:
            raise ValueError("Failed to parse formula")
        
        result = FormulaExecutor.execute(ast, context)
        
        if 0 <= date_idx < len(result):
            return result[date_idx]
        return 0.0
