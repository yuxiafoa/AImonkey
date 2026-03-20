import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.formula_parser import FormulaParser, Lexer, Parser, TokenType, NumberNode, VarNode, BinaryOpNode, FunctionCallNode


class TestLexer:
    def test_number(self):
        lexer = Lexer("123")
        token = lexer.get_next_token()
        assert token.type == TokenType.NUMBER
        assert token.value == 123

    def test_float(self):
        lexer = Lexer("12.34")
        token = lexer.get_next_token()
        assert token.type == TokenType.NUMBER
        assert token.value == 12.34

    def test_identifier(self):
        lexer = Lexer("CLOSE")
        token = lexer.get_next_token()
        assert token.type == TokenType.IDENTIFIER
        assert token.value == "CLOSE"

    def test_operators(self):
        lexer = Lexer("> < >= <= == !=")
        tokens = []
        while True:
            token = lexer.get_next_token()
            tokens.append(token)
            if token.type == TokenType.EOF:
                break

        assert tokens[0].type == TokenType.OPERATOR
        assert tokens[0].value == ">"
        assert tokens[1].value == "<"
        assert tokens[2].value == ">="
        assert tokens[3].value == "<="
        assert tokens[4].value == "=="
        assert tokens[5].value == "!="

    def test_expression(self):
        lexer = Lexer("CLOSE > OPEN")
        tokens = []
        while True:
            token = lexer.get_next_token()
            tokens.append(token)
            if token.type == TokenType.EOF:
                break

        assert len(tokens) == 4
        assert tokens[0].type == TokenType.IDENTIFIER
        assert tokens[1].type == TokenType.OPERATOR
        assert tokens[2].type == TokenType.IDENTIFIER


class TestParser:
    def test_number(self):
        lexer = Lexer("42")
        parser = Parser(lexer)
        ast = parser.parse()
        assert isinstance(ast, NumberNode)
        assert ast.value == 42

    def test_simple_expression(self):
        lexer = Lexer("CLOSE > OPEN")
        parser = Parser(lexer)
        ast = parser.parse()
        assert isinstance(ast, BinaryOpNode)
        assert ast.op == ">"

    def test_arithmetic_expression(self):
        lexer = Lexer("CLOSE + OPEN * 2")
        parser = Parser(lexer)
        ast = parser.parse()
        assert isinstance(ast, BinaryOpNode)
        assert ast.op == "+"

    def test_function_call(self):
        lexer = Lexer("MA(CLOSE, 5)")
        parser = Parser(lexer)
        ast = parser.parse()
        assert isinstance(ast, FunctionCallNode)
        assert ast.name == "MA"
        assert len(ast.args) == 2

    def test_nested_function(self):
        lexer = Lexer("MA(MA(CLOSE, 5), 10)")
        parser = Parser(lexer)
        ast = parser.parse()
        assert isinstance(ast, FunctionCallNode)
        assert ast.name == "MA"
        assert len(ast.args) == 2
        assert isinstance(ast.args[0], FunctionCallNode)


class TestFormulaParser:
    def test_validate_simple(self):
        valid, error = FormulaParser.validate_formula_syntax("CLOSE > OPEN")
        assert valid is True
        assert error is None

    def test_validate_function(self):
        valid, error = FormulaParser.validate_formula_syntax("MA(CLOSE, 5) > MA(CLOSE, 10)")
        assert valid is True
        assert error is None

    def test_validate_invalid(self):
        valid, error = FormulaParser.validate_formula_syntax("CLOSE >")
        assert valid is False
        assert error is not None

    def test_validate_unbalanced_parens(self):
        valid, error = FormulaParser.validate_formula_syntax("MA(CLOSE, 5")
        assert valid is False

    def test_get_variables(self):
        lexer = Lexer("CLOSE > OPEN + HIGH")
        parser = Parser(lexer)
        ast = parser.parse()
        vars = FormulaParser.get_variables(ast)
        assert "CLOSE" in vars
        assert "OPEN" in vars
        assert "HIGH" in vars

    def test_get_functions(self):
        lexer = Lexer("MA(CLOSE, 5)")
        parser = Parser(lexer)
        ast = parser.parse()
        funcs = FormulaParser.get_functions(ast)
        assert "MA" in funcs
