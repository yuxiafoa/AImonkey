# A股回测系统

基于Web的A股回测平台，支持通达信公式解析、选股和回测功能。

## 功能特性

- **数据管理**: 上传包含股票历史数据的ZIP文件，自动解析并存储到SQLite数据库
- **公式解析引擎**: 支持通达信公式语法，包括变量、运算符、函数调用
- **选股功能**: 根据公式条件筛选符合条件的股票
- **回测引擎**: 模拟交易并计算收益率、夏普比率、最大回撤等指标
- **回测报告**: 可视化收益率曲线，支持PDF/CSV导出

## 支持的函数

| 函数 | 说明 | 示例 |
|------|------|------|
| MA | 简单移动平均 | MA(CLOSE, 5) |
| EMA | 指数移动平均 | EMA(CLOSE, 12) |
| MACD | MACD指标 | MACD(CLOSE) |
| KDJ | KDJ随机指标 | KDJ(CLOSE) |
| RSI | 相对强弱指标 | RSI(CLOSE, 14) |
| BOLL | 布林带 | BOLL(CLOSE, 20) |
| REF | 引用之前的数据 | REF(CLOSE, 1) |
| COUNT | 统计条件满足次数 | COUNT(CLOSE>OPEN, 5) |

## 安装

```bash
pip install -r requirements.txt
```

## 运行

```bash
python run.py
```

然后在浏览器中访问 http://localhost:5000

## 使用说明

### 1. 数据上传

将通达信导出的股票数据（.txt格式）打包成ZIP文件，上传到系统。

数据格式（每行）：
```
日期,开盘价,最高价,最低价,收盘价,成交量
20230101,10.5,11.0,10.2,10.8,1000000
```

### 2. 选股

在选股页面输入公式，选择日期范围，点击"执行选股"。

示例公式：
- `CLOSE > MA(CLOSE, 5)` - 收盘价站上5日均线
- `RSI(CLOSE, 14) > 50` - RSI指标大于50
- `MACD(CLOSE) > 0` - MACD柱状线为正

### 3. 回测

选择要回测的股票，设置初始资金、佣金率、滑点等参数，点击"执行回测"。

## 项目结构

```
app/
├── __init__.py          # Flask应用工厂
├── config.py             # 配置文件
├── models/               # 数据模型
├── services/             # 业务逻辑
│   ├── data_service.py   # 数据导入服务
│   ├── formula_parser.py # 公式解析引擎
│   ├── formula_executor.py # 公式执行器
│   ├── stock_selector.py # 选股服务
│   └── backtest.py       # 回测引擎
├── api/                  # API路由
└── utils/                # 工具函数
```

## 测试

```bash
pytest tests/ -v
```
