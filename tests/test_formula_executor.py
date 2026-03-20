import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.formula_parser import FormulaParser
from app.services.formula_executor import FormulaContext, FormulaEvaluator


class TestFormulaContext:
    def test_get_var_close(self):
        data = {'close': [10.0, 11.0, 12.0], 'open': [9.0, 10.0, 11.0]}
        context = FormulaContext(data)
        close = context.get_var('CLOSE')
        assert close == [10.0, 11.0, 12.0]

    def test_get_var_open(self):
        data = {'close': [10.0, 11.0], 'open': [9.0, 10.0]}
        context = FormulaContext(data)
        open_price = context.get_var('OPEN')
        assert open_price == [9.0, 10.0]


class TestFormulaEvaluator:
    def test_evaluate_number(self):
        data = {'close': [10.0, 11.0]}
        context = FormulaContext(data)
        
        parser = FormulaParser()
        parser.validate("42")
        ast = parser.get_ast()
        
        evaluator = FormulaEvaluator(context)
        result = evaluator.evaluate(ast)
        assert result == [42.0, 42.0]

    def test_evaluate_binary_op(self):
        data = {'close': [10.0, 20.0], 'open': [9.0, 19.0]}
        context = FormulaContext(data)
        
        parser = FormulaParser()
        parser.validate("CLOSE > OPEN")
        ast = parser.get_ast()
        
        evaluator = FormulaEvaluator(context)
        result = evaluator.evaluate(ast)
        assert result == [1.0, 1.0]

    def test_evaluate_addition(self):
        data = {'close': [10.0, 20.0], 'open': [5.0, 10.0]}
        context = FormulaContext(data)
        
        parser = FormulaParser()
        parser.validate("CLOSE + OPEN")
        ast = parser.get_ast()
        
        evaluator = FormulaEvaluator(context)
        result = evaluator.evaluate(ast)
        assert result == [15.0, 30.0]

    def test_evaluate_ma(self):
        data = {'close': [10.0, 11.0, 12.0, 13.0, 14.0]}
        context = FormulaContext(data)
        
        parser = FormulaParser()
        parser.validate("MA(CLOSE, 3)")
        ast = parser.get_ast()
        
        evaluator = FormulaEvaluator(context)
        result = evaluator.evaluate(ast)
        assert abs(result[-1] - 13.0) < 0.01

    def test_evaluate_ref(self):
        data = {'close': [10.0, 11.0, 12.0]}
        context = FormulaContext(data)
        
        parser = FormulaParser()
        parser.validate("REF(CLOSE, 1)")
        ast = parser.get_ast()
        
        evaluator = FormulaEvaluator(context)
        result = evaluator.evaluate(ast)
        assert result[0] == 0.0
        assert result[1] == 10.0
        assert result[2] == 11.0
