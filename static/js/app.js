let selectedStocks = [];
let currentBacktestResultId = null;
let equityChart = null;

document.addEventListener('DOMContentLoaded', function() {
    initNavigation();
    initUpload();
    initSelect();
    initBacktest();
    initReport();
    loadStocks();
});

function initNavigation() {
    const navBtns = document.querySelectorAll('.nav-btn');
    const sections = document.querySelectorAll('.section');

    navBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const tab = this.dataset.tab;

            navBtns.forEach(b => b.classList.remove('active'));
            this.classList.add('active');

            sections.forEach(s => s.classList.remove('active'));
            document.getElementById(`${tab}-section`).classList.add('active');
        });
    });
}

function initUpload() {
    const uploadArea = document.getElementById('upload-area');
    const fileInput = document.getElementById('file-input');
    const uploadBtn = document.getElementById('upload-btn');

    uploadArea.addEventListener('click', () => fileInput.click());

    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.style.borderColor = '#1a73e8';
    });

    uploadArea.addEventListener('dragleave', () => {
        uploadArea.style.borderColor = '#ccc';
    });

    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.style.borderColor = '#ccc';
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            uploadFile(files[0]);
        }
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            uploadFile(e.target.files[0]);
        }
    });

    uploadBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        fileInput.click();
    });
}

async function uploadFile(file) {
    if (!file.name.toLowerCase().endsWith('.zip')) {
        showStatus('upload-status', '只支持ZIP文件', 'error');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    showStatus('upload-status', '上传中...', '');

    try {
        const response = await fetch('/api/data/upload', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (result.success) {
            showStatus('upload-status', result.message, 'success');
            loadStocks();
        } else {
            showStatus('upload-status', result.message, 'error');
        }
    } catch (error) {
        showStatus('upload-status', '上传失败: ' + error.message, 'error');
    }
}

async function loadStocks() {
    try {
        const response = await fetch('/api/data/stocks');
        const result = await response.json();

        if (result.success) {
            renderStocksTable(result.stocks);
        }
    } catch (error) {
        console.error('Failed to load stocks:', error);
    }
}

function renderStocksTable(stocks) {
    const tbody = document.querySelector('#stocks-table tbody');
    tbody.innerHTML = '';

    if (stocks.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;">暂无数据</td></tr>';
        return;
    }

    stocks.forEach(stock => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${stock.code}</td>
            <td>${stock.name}</td>
            <td>${stock.data_count}</td>
            <td><button class="btn" onclick="deleteStock(${stock.id})">删除</button></td>
        `;
        tbody.appendChild(tr);
    });
}

async function deleteStock(stockId) {
    if (!confirm('确定要删除这只股票的数据吗？')) return;

    try {
        const response = await fetch(`/api/data/stocks/${stockId}`, {
            method: 'DELETE'
        });

        const result = await response.json();

        if (result.success) {
            loadStocks();
        } else {
            alert(result.message);
        }
    } catch (error) {
        alert('删除失败: ' + error.message);
    }
}

function initSelect() {
    const runSelectBtn = document.getElementById('run-select-btn');
    const toBacktestBtn = document.getElementById('to-backtest-btn');

    runSelectBtn.addEventListener('click', runSelect);
    toBacktestBtn.addEventListener('click', goToBacktest);
}

async function runSelect() {
    const formulaInput = document.getElementById('formula-input').value.trim();
    const dateStart = document.getElementById('select-date-start').value.replace(/-/g, '');
    const dateEnd = document.getElementById('select-date-end').value.replace(/-/g, '');
    const combineMode = document.getElementById('combine-mode').value;

    if (!formulaInput) {
        showStatus('select-status', '请输入选股公式', 'error');
        return;
    }

    if (!dateStart || !dateEnd) {
        showStatus('select-status', '请选择日期范围', 'error');
        return;
    }

    const formulas = formulaInput.split('\n').filter(f => f.trim());
    const statusEl = document.getElementById('select-status');
    statusEl.textContent = '选股中...';
    statusEl.className = 'status';
    statusEl.style.display = 'block';

    try {
        const response = await fetch('/api/select', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                formulas: formulas,
                stock_ids: [],
                date_start: parseInt(dateStart),
                date_end: parseInt(dateEnd),
                combine_mode: combineMode
            })
        });

        const result = await response.json();

        if (result.success) {
            renderSelectResults(result.results);
            showStatus('select-status', `选股完成，找到 ${result.count} 只符合条件的股票`, 'success');
        } else {
            showStatus('select-status', result.message, 'error');
        }
    } catch (error) {
        showStatus('select-status', '选股失败: ' + error.message, 'error');
    }
}

function renderSelectResults(results) {
    const tbody = document.querySelector('#select-results-table tbody');
    tbody.innerHTML = '';
    selectedStocks = [];

    if (results.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;">没有符合条件的股票</td></tr>';
        document.getElementById('to-backtest-btn').disabled = true;
        return;
    }

    results.forEach((stock, index) => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${stock.code}</td>
            <td>${stock.name}</td>
            <td>${stock.values.map((v, i) => `公式${i+1}: ${v.toFixed(4)}`).join('<br>')}</td>
            <td><input type="checkbox" class="stock-checkbox" data-stock-id="${stock.stock_id}" checked></td>
        `;
        tbody.appendChild(tr);
        selectedStocks.push({stock_id: stock.stock_id, code: stock.code, name: stock.name});
    });

    document.getElementById('to-backtest-btn').disabled = results.length === 0;
}

function goToBacktest() {
    const checkedStocks = selectedStocks.filter(s => {
        const checkbox = document.querySelector(`[data-stock-id="${s.stock_id}"]`);
        return checkbox && checkbox.checked;
    });

    if (checkedStocks.length === 0) {
        alert('请至少选择一只股票进行回测');
        return;
    }

    const dateStart = document.getElementById('select-date-start').value;
    const dateEnd = document.getElementById('select-date-end').value;
    const formula = document.getElementById('formula-input').value.trim().split('\n')[0];

    document.getElementById('backtest-formula').value = formula;
    document.getElementById('backtest-date-start').value = dateStart;
    document.getElementById('backtest-date-end').value = dateEnd;

    document.querySelector('[data-tab="backtest"]').click();
}

function initBacktest() {
    const runBacktestBtn = document.getElementById('run-backtest-btn');

    runBacktestBtn.addEventListener('click', runBacktest);
}

async function runBacktest() {
    const formula = document.getElementById('backtest-formula').value.trim();
    const dateStart = document.getElementById('backtest-date-start').value.replace(/-/g, '');
    const dateEnd = document.getElementById('backtest-date-end').value.replace(/-/g, '');
    const initialCapital = parseFloat(document.getElementById('initial-capital').value);
    const commissionRate = parseFloat(document.getElementById('commission-rate').value);
    const slippage = parseFloat(document.getElementById('slippage').value);

    if (!formula) {
        showStatus('backtest-status', '请输入选股公式', 'error');
        return;
    }

    if (!dateStart || !dateEnd) {
        showStatus('backtest-status', '请选择回测日期', 'error');
        return;
    }

    const checkedStocks = selectedStocks.filter(s => {
        const checkbox = document.querySelector(`[data-stock-id="${s.stock_id}"]`);
        return checkbox && checkbox.checked;
    });

    if (checkedStocks.length === 0) {
        showStatus('backtest-status', '请至少选择一只股票', 'error');
        return;
    }

    showStatus('backtest-status', '回测中...', '');

    try {
        const response = await fetch('/api/backtest/run', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                formula: formula,
                stock_ids: checkedStocks.map(s => s.stock_id),
                date_start: parseInt(dateStart),
                date_end: parseInt(dateEnd),
                initial_capital: initialCapital,
                commission_rate: commissionRate,
                slippage: slippage
            })
        });

        const result = await response.json();

        if (result.success) {
            currentBacktestResultId = result.id;
            renderBacktestMetrics(result);
            showStatus('backtest-status', '回测完成', 'success');
            document.querySelector('[data-tab="report"]').click();
            loadReport(result.id);
        } else {
            showStatus('backtest-status', result.message, 'error');
        }
    } catch (error) {
        showStatus('backtest-status', '回测失败: ' + error.message, 'error');
    }
}

function renderBacktestMetrics(result) {
    const metricsGrid = document.getElementById('backtest-metrics');
    const m = result.metrics;

    metricsGrid.innerHTML = `
        <div class="metric-card">
            <div class="label">总收益率</div>
            <div class="value ${m.total_return >= 0 ? 'positive' : 'negative'}">${m.total_return}%</div>
        </div>
        <div class="metric-card">
            <div class="label">年化收益率</div>
            <div class="value ${m.annual_return >= 0 ? 'positive' : 'negative'}">${m.annual_return}%</div>
        </div>
        <div class="metric-card">
            <div class="label">夏普比率</div>
            <div class="value">${m.sharpe_ratio}</div>
        </div>
        <div class="metric-card">
            <div class="label">最大回撤</div>
            <div class="value negative">${m.max_drawdown}%</div>
        </div>
        <div class="metric-card">
            <div class="label">胜率</div>
            <div class="value">${m.win_rate}%</div>
        </div>
        <div class="metric-card">
            <div class="label">交易次数</div>
            <div class="value">${m.total_trades}</div>
        </div>
    `;
}

async function loadReport(resultId) {
    try {
        const response = await fetch(`/api/backtest/report/${resultId}`);
        const result = await response.json();

        if (result.success) {
            renderReport(result);
        }
    } catch (error) {
        console.error('Failed to load report:', error);
    }
}

function renderReport(result) {
    const metricsGrid = document.getElementById('report-metrics');
    const m = result.metrics;

    metricsGrid.innerHTML = `
        <div class="metric-card">
            <div class="label">初始资金</div>
            <div class="value">${result.initial_capital.toFixed(2)}</div>
        </div>
        <div class="metric-card">
            <div class="label">最终资产</div>
            <div class="value">${result.final_asset.toFixed(2)}</div>
        </div>
        <div class="metric-card">
            <div class="label">总收益率</div>
            <div class="value ${m.total_return >= 0 ? 'positive' : 'negative'}">${m.total_return}%</div>
        </div>
        <div class="metric-card">
            <div class="label">年化收益率</div>
            <div class="value ${m.annual_return >= 0 ? 'positive' : 'negative'}">${m.annual_return}%</div>
        </div>
        <div class="metric-card">
            <div class="label">夏普比率</div>
            <div class="value">${m.sharpe_ratio}</div>
        </div>
        <div class="metric-card">
            <div class="label">最大回撤</div>
            <div class="value negative">${m.max_drawdown}%</div>
        </div>
    `;

    renderEquityChart(result.equity_curve);
    renderTradesTable(result.trades);
}

function renderEquityChart(equityCurve) {
    const chartDom = document.getElementById('equity-chart');

    if (equityChart) {
        equityChart.dispose();
    }

    equityChart = echarts.init(chartDom);

    const dates = equityCurve.map(p => p.date.toString());
    const assets = equityCurve.map(p => p.asset);

    const option = {
        tooltip: {
            trigger: 'axis'
        },
        xAxis: {
            type: 'category',
            data: dates,
            axisLabel: {
                rotate: 45,
                fontSize: 10
            }
        },
        yAxis: {
            type: 'value',
            name: '资产'
        },
        series: [{
            name: '资产',
            type: 'line',
            data: assets,
            smooth: true,
            itemStyle: {
                color: '#1a73e8'
            },
            areaStyle: {
                color: 'rgba(26, 115, 232, 0.1)'
            }
        }]
    };

    equityChart.setOption(option);
}

function renderTradesTable(trades) {
    const tbody = document.querySelector('#trades-table tbody');
    tbody.innerHTML = '';

    if (trades.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;">暂无交易记录</td></tr>';
        return;
    }

    trades.forEach(trade => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${trade.date}</td>
            <td>${trade.stock_code} (${trade.stock_name})</td>
            <td>${trade.action === 'BUY' ? '买入' : '卖出'}</td>
            <td>${trade.price.toFixed(2)}</td>
            <td>${trade.quantity}</td>
            <td>${trade.amount.toFixed(2)}</td>
            <td>${trade.commission.toFixed(2)}</td>
        `;
        tbody.appendChild(tr);
    });
}

function initReport() {
    const exportPdfBtn = document.getElementById('export-pdf-btn');
    const exportCsvBtn = document.getElementById('export-csv-btn');

    exportPdfBtn.addEventListener('click', () => exportReport('pdf'));
    exportCsvBtn.addEventListener('click', () => exportReport('csv'));
}

async function exportReport(format) {
    if (!currentBacktestResultId) {
        alert('请先运行回测');
        return;
    }

    window.open(`/api/backtest/export/${currentBacktestResultId}?format=${format}`, '_blank');
}

function showStatus(elementId, message, type) {
    const el = document.getElementById(elementId);
    el.textContent = message;
    el.className = 'status' + (type ? ' ' + type : '');
    el.style.display = type ? 'block' : 'none';
}
