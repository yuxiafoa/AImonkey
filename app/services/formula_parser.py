from enum import Enum, auto
from typing import List, Dict, Any, Optional, Tuple
import re


class TokenType(Enum):
    NUMBER = auto()
    IDENTIFIER = auto()
    OPERATOR = auto()
    LPAREN = auto()
    RPAREN = auto()
    COMMA = auto()
    EOF = auto()


class Token:
    def __init__(self, type_: TokenType, value: Any, line: int = 1, col: int = 1):
        self.type = type_
        self.value = value
        self.line = line
        self.col = col
    
    def __repr__(self):
        return f"Token({self.type.name}, {self.value!r}, line={self.line}, col={self.col})"


class Lexer:
    OPERATORS = {'+', '-', '*', '/', '>', '<', '>=', '<=', '==', '!=', ':='}
    
    def __init__(self, text: str):
        self.text = text
        self.pos = 0
        self.line = 1
        self.col = 1
    
    def error(self, message: str):
        return SyntaxError(f"{message} at line {self.line}, col {self.col}")
    
    def peek(self) -> str:
        if self.pos < len(self.text):
            return self.text[self.pos]
        return '\0'
    
    def advance(self) -> str:
        char = ''
        if self.pos < len(self.text):
            char = self.text[self.pos]
            self.pos += 1
            if char == '\n':
                self.line += 1
                self.col = 1
            else:
                self.col += 1
        return char
    
    def skip_whitespace(self):
        while self.pos < len(self.text) and self.text[self.pos] in ' \t\n\r':
            self.advance()
    
    def read_number(self) -> Token:
        start_col = self.col
        num_str = ''
        while self.pos < len(self.text) and (self.text[self.pos].isdigit() or self.text[self.pos] == '.'):
            num_str += self.advance()
        
        if '.' in num_str:
            return Token(TokenType.NUMBER, float(num_str), self.line, start_col)
        return Token(TokenType.NUMBER, int(num_str), self.line, start_col)
    
    def read_identifier(self) -> Token:
        start_col = self.col
        ident = ''
        while self.pos < len(self.text) and (self.text[self.pos].isalnum() or self.text[self.pos] == '_'):
            ident += self.advance()
        return Token(TokenType.IDENTIFIER, ident, self.line, start_col)
    
    def read_operator(self) -> Token:
        start_col = self.col
        op = self.advance()
        
        if op == ':' and self.peek() == '=':
            op += self.advance()
        elif op in '><=' and self.peek() == '=':
            op += self.advance()
        elif op == '=' and self.peek() == '=':
            op += self.advance()
        elif op == '!' and self.peek() == '=':
            op += self.advance()
        
        return Token(TokenType.OPERATOR, op, self.line, start_col)
    
    def get_next_token(self) -> Token:
        while self.pos < len(self.text):
            char = self.text[self.pos]
            
            if char in ' \t\n\r':
                self.skip_whitespace()
                continue
            
            if char.isdigit() or (char == '.' and self.pos + 1 < len(self.text) and self.text[self.pos + 1].isdigit()):
                return self.read_number()
            
            if char.isalpha() or char == '_':
                return self.read_identifier()
            
            if char in self.OPERATORS or char in ':':
                return self.read_operator()
            
            if char == '(':
                self.advance()
                return Token(TokenType.LPAREN, '(', self.line, self.col - 1)
            
            if char == ')':
                self.advance()
                return Token(TokenType.RPAREN, ')', self.line, self.col - 1)
            
            if char == ',':
                self.advance()
                return Token(TokenType.COMMA, ',', self.line, self.col - 1)
            
            if char == ';':
                self.advance()
                return Token(TokenType.OPERATOR, ';', self.line, self.col - 1)
            
            raise self.error(f"Unexpected character: {char!r}")
        
        return Token(TokenType.EOF, None, self.line, self.col)


class ASTNode:
    pass


class NumberNode(ASTNode):
    def __init__(self, value: float):
        self.value = value


class VarNode(ASTNode):
    def __init__(self, name: str):
        self.name = name.upper()


class BinaryOpNode(ASTNode):
    def __init__(self, left: ASTNode, op: str, right: ASTNode):
        self.left = left
        self.op = op
        self.right = right


class FunctionCallNode(ASTNode):
    def __init__(self, name: str, args: List[ASTNode]):
        self.name = name.upper()
        self.args = args


class Parser:
    BUILTIN_VARS = {'OPEN', 'HIGH', 'LOW', 'CLOSE', 'VOLUME', 'O', 'H', 'L', 'C', 'V'}
    BUILTIN_FUNCTIONS = {'MA', 'EMA', 'MACD', 'KDJ', 'RSI', 'BOLL', 'COUNT', 'REF', 'ABS', 'MAX', 'MIN'}
    
    def __init__(self, lexer: Lexer):
        self.lexer = lexer
        self.current_token = self.lexer.get_next_token()
    
    def error(self, message: str):
        return SyntaxError(f"{message} at line {self.current_token.line}, col {self.current_token.col}")
    
    def eat(self, token_type: TokenType):
        if self.current_token.type == token_type:
            self.current_token = self.lexer.get_next_token()
        else:
            raise self.error(f"Expected {token_type.name}, got {self.current_token.type.name}")
    
    def factor(self) -> ASTNode:
        token = self.current_token
        
        if token.type == TokenType.NUMBER:
            self.eat(TokenType.NUMBER)
            return NumberNode(token.value)
        
        if token.type == TokenType.IDENTIFIER:
            name = token.value.upper()
            self.eat(TokenType.IDENTIFIER)
            
            if self.current_token.type == TokenType.LPAREN:
                return self.function_call(name)
            return VarNode(name)
        
        if token.type == TokenType.LPAREN:
            self.eat(TokenType.LPAREN)
            node = self.expr()
            self.eat(TokenType.RPAREN)
            return node
        
        if token.type == TokenType.OPERATOR and token.value == '-':
            self.eat(TokenType.OPERATOR)
            return BinaryOpNode(NumberNode(0), '-', self.factor())
        
        raise self.error(f"Unexpected token: {token}")
    
    def function_call(self, name: str) -> ASTNode:
        self.eat(TokenType.LPAREN)
        args = []
        
        if self.current_token.type != TokenType.RPAREN:
            args.append(self.expr())
            while self.current_token.type == TokenType.COMMA:
                self.eat(TokenType.COMMA)
                args.append(self.expr())
        
        self.eat(TokenType.RPAREN)
        return FunctionCallNode(name, args)
    
    def term(self) -> ASTNode:
        node = self.factor()
        
        while self.current_token.type == TokenType.OPERATOR and self.current_token.value in ('*', '/'):
            op = self.current_token.value
            self.eat(TokenType.OPERATOR)
            node = BinaryOpNode(node, op, self.factor())
        
        return node
    
    def expr(self) -> ASTNode:
        node = self.term()
        
        while self.current_token.type == TokenType.OPERATOR and self.current_token.value in ('+', '-', '>', '<', '>=', '<=', '==', '!='):
            op = self.current_token.value
            self.eat(TokenType.OPERATOR)
            node = BinaryOpNode(node, op, self.term())
        
        return node
    
    def logical_and_expr(self) -> ASTNode:
        node = self.expr()
        
        while self.current_token.type == TokenType.IDENTIFIER and self.current_token.value.upper() == 'AND':
            self.eat(TokenType.IDENTIFIER)
            node = BinaryOpNode(node, 'AND', self.expr())
        
        return node
    
    def logical_or_expr(self) -> ASTNode:
        node = self.logical_and_expr()
        
        while self.current_token.type == TokenType.IDENTIFIER and self.current_token.value.upper() == 'OR':
            self.eat(TokenType.IDENTIFIER)
            node = BinaryOpNode(node, 'OR', self.logical_and_expr())
        
        return node
    
    def parse(self) -> ASTNode:
        node = self.logical_or_expr()
        
        while self.current_token.type == TokenType.OPERATOR and self.current_token.value == ';':
            self.eat(TokenType.OPERATOR)
            if self.current_token.type == TokenType.EOF:
                break
            node = self.logical_or_expr()
        
        if self.current_token.type == TokenType.OPERATOR and self.current_token.value == ':=':
            self.eat(TokenType.OPERATOR)
            node = self.parse()
        
        if self.current_token.type == TokenType.OPERATOR and self.current_token.value == ';':
            self.eat(TokenType.OPERATOR)
        
        if self.current_token.type != TokenType.EOF:
            raise self.error(f"Unexpected token: {self.current_token}")
        
        return node
        
        return node


class FormulaParser:
    
    def __init__(self):
        self.parser = None
        self.ast = None
        self.errors = []
    
    def validate(self, formula: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        self.errors = []
        
        try:
            lexer = Lexer(formula)
            self.parser = Parser(lexer)
            self.ast = self.parser.parse()
            return True, None
        except SyntaxError as e:
            error_info = {
                'message': str(e),
                'line': getattr(e, 'line', 1),
                'col': getattr(e, 'col', 1)
            }
            return False, error_info
    
    def get_ast(self) -> Optional[ASTNode]:
        return self.ast
    
    @staticmethod
    def validate_formula_syntax(formula: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        parser = FormulaParser()
        return parser.validate(formula)
    
    @staticmethod
    def get_variables(ast: ASTNode) -> set:
        variables = set()
        
        def traverse(node):
            if isinstance(node, VarNode):
                variables.add(node.name)
            elif isinstance(node, BinaryOpNode):
                traverse(node.left)
                traverse(node.right)
            elif isinstance(node, FunctionCallNode):
                for arg in node.args:
                    traverse(arg)
        
        traverse(ast)
        return variables
    
    @staticmethod
    def get_functions(ast: ASTNode) -> set:
        functions = set()
        
        def traverse(node):
            if isinstance(node, FunctionCallNode):
                functions.add(node.name)
                for arg in node.args:
                    traverse(arg)
            elif isinstance(node, BinaryOpNode):
                traverse(node.left)
                traverse(node.right)
        
        traverse(ast)
        return functions
