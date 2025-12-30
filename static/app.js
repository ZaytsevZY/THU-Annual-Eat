// 全局变量
let consumptionData = [];
let barChart = null;
let pieChart = null;
let lineChart = null;

// 声明Chart为全局变量（用于TypeScript检查）
/* global Chart */

// 页面加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    setupFormValidation();
    handleURLParameters();
});

// 处理URL参数（兼容GET和POST）
function handleURLParameters() {
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.has('idserial')) {
        document.getElementById('idserial').value = urlParams.get('idserial');
    }
    if (urlParams.has('servicehall')) {
        document.getElementById('servicehall').value = urlParams.get('servicehall');
    }
    if (urlParams.has('startDate')) {
        document.getElementById('startDate').value = urlParams.get('startDate');
    }
    if (urlParams.has('endDate')) {
        document.getElementById('endDate').value = urlParams.get('endDate');
    }

    // 如果有URL参数，自动提交分析
    if (urlParams.has('idserial') && urlParams.has('servicehall')) {
        setTimeout(() => {
            analyzeData();
        }, 1000);
    }
}


// 设置表单验证
function setupFormValidation() {
    const form = document.getElementById('analysisForm');
    const button = form.querySelector('button');
    if (button) {
        // 移除可能存在的旧事件监听器，避免重复绑定
        button.removeEventListener('click', analyzeData);
        button.addEventListener('click', analyzeData);

        // 防止表单默认提交行为
        form.addEventListener('submit', function(e) {
            e.preventDefault();
        });
    }
}

// 分析数据 - 添加防抖机制
window.isAnalyzing = false;
window.analyzeData = async function analyzeData() {
    // 防止重复点击
    if (window.isAnalyzing) {
        console.log('分析已在进行中，请稍候...');
        return;
    }

    window.isAnalyzing = true;

    // 禁用按钮
    const button = document.querySelector('#analysisForm button');
    if (button) {
        button.disabled = true;
        button.innerHTML = '<i class="bi bi-hourglass-split"></i> 分析中...';
    }

    console.log('开始分析数据...');

    const idserial = document.getElementById('idserial').value.trim();
    const servicehall = document.getElementById('servicehall').value.trim();
    const startDate = document.getElementById('startDate').value || '2025-01-01';
    const endDate = document.getElementById('endDate').value || '2025-12-31';

    if (!idserial || !servicehall) {
        alert('请填写学号和服务代码');
        window.isAnalyzing = false;
        if (button) {
            button.disabled = false;
            button.innerHTML = '<i class="bi bi-search"></i> 开始分析';
        }
        return;
    }

    console.log('参数:', {idserial, servicehall, startDate, endDate});

    hideResults();

    try {
        const formData = new FormData();
        formData.append('idserial', idserial);
        formData.append('servicehall', servicehall);
        formData.append('start_date', startDate);
        formData.append('end_date', endDate);

        const response = await fetch('/api/analyze', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();
        console.log('API Response:', result);

        if (result.success) {
            consumptionData = result.data;
            displayResults(result);
            showResults();
        } else {
            alert('分析失败: ' + result.error);
        }
    } catch (error) {
        console.error('详细错误:', error);
        alert('请求失败: ' + error.message);
    } finally {
        // 恢复按钮状态
        window.isAnalyzing = false;
        const button = document.querySelector('#analysisForm button');
        if (button) {
            button.disabled = false;
            button.innerHTML = '<i class="bi bi-search"></i> 开始分析';
        }
    }
}

// 显示结果
function displayResults(data) {
    console.log('显示结果:', data);
    window.analysisResult = data; // 存储完整分析结果
    updateStatistics(data);
    createBarChart();
    createRestaurantPieChart();
    createVendorPieChart();
    createMonthlyTotalChart();
    displayRestaurantRankingList();
    displayVendorRankingList();
    createMonthlyTop3Chart();
    populateTable();
}

// 更新统计信息
function updateStatistics(data) {
    document.getElementById('totalAmount').textContent = data.total.toFixed(2);
    document.getElementById('merchantCount').textContent = data.count;
    document.getElementById('avgAmount').textContent = data.average.toFixed(2);
    document.getElementById('dateRange').textContent = `${data.start_date} 至 ${data.end_date}`;
}

// 创建柱状图
function createBarChart() {
    const ctx = document.getElementById('barChart').getContext('2d');

    if (typeof Chart === 'undefined') {
        console.error('Chart.js 未加载');
        return;
    }

    if (barChart) {
        barChart.destroy();
    }

    const topMerchants = consumptionData.slice(0, 10);
    const labels = topMerchants.map(item => item.merchant);
    const data = topMerchants.map(item => item.amount);

    // 使用与饼图相同的哈希函数
    const restaurantColors = generateRestaurantColors(consumptionData);
    const colors = topMerchants.map(item => getStallColor(restaurantColors, item.merchant));

    barChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: '消费金额（元）',
                data: data,
                backgroundColor: colors,
                borderColor: colors.map(color => color.replace('0.8', '1')),
                borderWidth: 2,
                borderRadius: 5,
                maxBarThickness: 60
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const percentage = ((context.parsed.y / getTotalAmount()) * 100).toFixed(1);
                            return `${context.parsed.y}元 (${percentage}%)`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return value + '元';
                        }
                    }
                },
                x: {
                    ticks: {
                        maxRotation: 45,
                        minRotation: 0
                    }
                }
            }
        }
    });
}

// 创建饼状图
function createPieChart() {
    const ctx = document.getElementById('pieChart').getContext('2d');

    if (typeof Chart === 'undefined') {
        console.error('Chart.js 未加载');
        return;
    }

    if (pieChart) {
        pieChart.destroy();
    }

    const totalAmount = getTotalAmount();
    const threshold = totalAmount * 0.05; // 5%阈值

    // 分离数据：大于5%的显示名称，小于5%的合并为"其他"
    const significantData = [];
    const otherData = { label: '其他', amount: 0 };

    consumptionData.forEach(item => {
        if (item.amount >= threshold) {
            significantData.push(item);
        } else {
            otherData.amount += item.amount;
        }
    });

    const finalData = [...significantData];
    if (otherData.amount > 0) {
        finalData.push(otherData);
    }

    const labels = finalData.map(item => item.label || item.merchant);
    const data = finalData.map(item => item.amount);
    const colors = generateGradientColors(finalData.length);

    pieChart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: colors,
                borderColor: colors.map(color => color.replace('0.8', '1')),
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 15,
                        boxWidth: 10,
                        font: {
                            size: 12
                        }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const percentage = ((context.parsed / totalAmount) * 100).toFixed(1);
                            return `${context.label}: ${context.parsed}元 (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

// 创建月度总消费折线图
function createMonthlyTotalChart() {
    const ctx = document.getElementById('monthlyTotalChart').getContext('2d');

    if (typeof Chart === 'undefined') {
        console.error('Chart.js 未加载');
        return;
    }

    if (window.monthlyTotalChartInstance) {
        window.monthlyTotalChartInstance.destroy();
    }

    // 从真实数据计算月度消费
    const monthlyData = calculateMonthlyData(window.analysisResult || consumptionData);
    const months = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月'];

    window.monthlyTotalChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: months,
            datasets: [{
                label: '月度总消费',
                data: monthlyData.totals,
                borderColor: '#667eea',
                backgroundColor: 'rgba(102, 126, 234, 0.1)',
                borderWidth: 3,
                fill: true,
                tension: 0.4,
                pointBackgroundColor: '#667eea',
                pointBorderColor: '#fff',
                pointBorderWidth: 2,
                pointRadius: 5
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `总消费: ${context.parsed.y}元`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return value + '元';
                        }
                    }
                }
            }
        }
    });
}


// 计算月度数据（使用后端返回的真实数据）
function calculateMonthlyData(data) {
    if (!data.monthly_trends) {
        // 如果没有月度数据，返回空数组
        console.log('没有月度数据');
        return { totals: new Array(12).fill(0) };
    }

    const monthly_trends = data.monthly_trends;
    const totals = new Array(12).fill(0);

    console.log('月度数据:', monthly_trends);

    // 从真实数据中提取月度消费总额
    Object.keys(monthly_trends).forEach(month_key => {
        // month_key 格式为 "YYYY-MM"
        const parts = month_key.split('-');
        if (parts.length === 2) {
            const month_num = parseInt(parts[1]);
            const month_index = month_num - 1;
            if (month_index >= 0 && month_index < 12) {
                const month_data = monthly_trends[month_key];
                if (month_data && month_data.total !== undefined) {
                    totals[month_index] = month_data.total || 0;
                    console.log(`${month_key}: ${month_data.total}`);
                }
            }
        }
    });

    console.log('月度总消费:', totals);
    return { totals };
}

// 创建月度TOP3档口趋势折线图
function createMonthlyTop3Chart() {
    const ctx = document.getElementById('monthlyTop3Chart').getContext('2d');

    if (typeof Chart === 'undefined') {
        console.error('Chart.js 未加载');
        return;
    }

    if (window.monthlyTop3ChartInstance) {
        window.monthlyTop3ChartInstance.destroy();
    }

    if (!window.analysisResult || !window.analysisResult.monthly_trends) {
        console.log('没有月度趋势数据');
        return;
    }

    const months = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月'];
    const year = window.analysisResult.start_date ? window.analysisResult.start_date.substring(0, 4) : '2025';
    const monthKeys = Array.from({length: 12}, (_, i) => `${year}-${String(i + 1).padStart(2, '0')}`);

    const monthly_trends = window.analysisResult.monthly_trends;

    // 收集所有月份前三名档口的并集
    const allTopStalls = new Set();

    // 为每个月计算前三名并收集并集
    Object.keys(monthly_trends).forEach(month_key => {
        const month_data = monthly_trends[month_key];
        if (month_data && month_data.all_stalls) {
            const sorted_stalls = Object.entries(month_data.all_stalls)
                .sort((a, b) => b[1] - a[1])
                .slice(0, 3);
            sorted_stalls.forEach(([stall, amount]) => {
                allTopStalls.add(stall);
            });
        }
    });

    // 为TOP3并集中的档口准备12个月的完整数据
    const monthlyTop3Data = {};
    allTopStalls.forEach(stall => {
        monthlyTop3Data[stall] = new Array(12).fill(0);
    });

    // 为每个TOP3档口填充所有12个月的数据
    monthKeys.forEach((month_key, index) => {
        if (monthly_trends[month_key] && monthly_trends[month_key].all_stalls) {
            const month_data = monthly_trends[month_key].all_stalls;
            allTopStalls.forEach(stall => {
                monthlyTop3Data[stall][index] = month_data[stall] || 0;
            });
        }
    });

    // 获取所有档口的并集
    const topStallsArray = Array.from(allTopStalls);
    console.log('TOP3档口并集:', topStallsArray);

    // 使用与柱状图相同的颜色映射系统
    const restaurantColors = generateRestaurantColors(consumptionData);

    // 创建数据集 - TOP3档口线条加粗到3倍，使用哈希颜色
    const datasets = topStallsArray.map((stall) => {
        const stallColor = getStallColor(restaurantColors, stall);
        return {
            label: stall,
            data: monthlyTop3Data[stall] || new Array(12).fill(0),
            borderColor: stallColor.replace('0.8', '1'), // 使用不透明边框颜色
            backgroundColor: stallColor.replace('0.8', '0.2'), // 使用半透明背景色
            borderWidth: 6,  // 从2增加到6，加粗3倍
            fill: false,
            tension: 0.4,
            pointBackgroundColor: stallColor.replace('0.8', '1'),
            pointBorderColor: '#fff',
            pointBorderWidth: 2,
            pointRadius: 4
        };
    });

    window.monthlyTop3ChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: months,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        padding: 15,
                        boxWidth: 12,
                        font: {
                            size: 12
                        }
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label: function(context) {
                            // 忽略所有零元的数值
                            if (context.parsed.y === 0) {
                                return null;
                            }
                            return `${context.dataset.label}: ${context.parsed.y}元`;
                        },
                        filter: function(tooltipItem) {
                            // 过滤掉零元的数值
                            return tooltipItem.parsed.y !== 0;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return value + '元';
                        }
                    }
                }
            }
        }
    });
}

// 填充表格
function populateTable() {
    const tableBody = document.getElementById('tableBody');
    tableBody.innerHTML = '';

    consumptionData.forEach((item, index) => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${index + 1}</td>
            <td>${item.merchant}</td>
            <td class="text-center"><strong>${item.amount.toFixed(2)}</strong></td>
            <td>
                <div class="progress">
                    <div class="progress-bar" style="width: ${item.percentage}%">${item.percentage.toFixed(2)}%</div>
                </div>
            </td>
            <td>
                <button class="btn btn-sm btn-outline-primary" onclick="showMerchantDetails('${item.merchant}')">
                    <i class="bi bi-eye"></i>
                </button>
            </td>
        `;
        tableBody.appendChild(row);
    });

    // 初始化DataTable - 使用内联配置避免外部资源加载
    if ($.fn.DataTable.isDataTable('#consumptionTable')) {
        $('#consumptionTable').DataTable().destroy();
    }

    $('#consumptionTable').DataTable({
        language: {
            lengthMenu: "显示 _MENU_ 项结果",
            search: "搜索:",
            info: "显示第 _START_ 至 _END_ 项结果，共 _TOTAL_ 项",
            paginate: {
                first: "首页",
                last: "末页",
                next: "下页",
                previous: "上页"
            },
            emptyTable: "没有数据",
            loadingRecords: "加载中...",
            processing: "处理中...",
            zeroRecords: "没有找到匹配的记录"
        },
        pageLength: 10,
        order: [[2, 'desc']],
        columnDefs: [
            { orderable: false, targets: [4] }
        ]
    });
}

// 数据分割工具函数
function splitMerchantData(data) {
    const restaurantData = {};
    const vendorData = {};

    data.forEach(item => {
        const merchant = item.merchant;
        const parts = merchant.split('_');

        if (parts.length >= 2) {
            // 有下划线，格式为：餐厅_档口
            const restaurant = parts[0];
            const vendor = merchant;

            // 餐厅数据合并
            if (!restaurantData[restaurant]) {
                restaurantData[restaurant] = 0;
            }
            restaurantData[restaurant] += item.amount;

            // 档口数据保持独立
            if (!vendorData[vendor]) {
                vendorData[vendor] = 0;
            }
            vendorData[vendor] = item.amount;
        } else {
            // 没有下划线，视为餐厅
            const restaurant = merchant;
            if (!restaurantData[restaurant]) {
                restaurantData[restaurant] = 0;
            }
            restaurantData[restaurant] += item.amount;

            // 同时作为档口
            if (!vendorData[restaurant]) {
                vendorData[restaurant] = 0;
            }
            vendorData[restaurant] += item.amount;
        }
    });

    return {
        restaurantData: Object.entries(restaurantData).map(([name, amount]) => ({ merchant: name, amount })),
        vendorData: Object.entries(vendorData).map(([name, amount]) => ({ merchant: name, amount }))
    };
}

// 创建餐厅饼图（合并相同餐厅）
function createRestaurantPieChart() {
    const ctx = document.getElementById('restaurantPieChart').getContext('2d');

    if (typeof Chart === 'undefined') {
        console.error('Chart.js 未加载');
        return;
    }

    if (window.restaurantPieChartInstance) {
        window.restaurantPieChartInstance.destroy();
    }

    const { restaurantData } = splitMerchantData(consumptionData);
    const totalAmount = getTotalAmount();
    const threshold = totalAmount * 0.02; // 2%阈值

    // 分离数据：大于2%的显示名称和颜色，小于2%的合并为"其他"
    const significantData = [];
    const otherData = { label: '其他', amount: 0 };

    restaurantData.forEach(item => {
        if (item.amount >= threshold) {
            significantData.push(item);
        } else {
            otherData.amount += item.amount;
        }
    });

    // 按金额从多到少排序
    significantData.sort((a, b) => b.amount - a.amount);

    // 合并数据：所有大于2%的显示名称和颜色，其他合并为"其他"
    const finalData = [...significantData];
    if (otherData.amount > 0) {
        finalData.push(otherData);
    }

    const labels = finalData.map(item => item.label || item.merchant || '');
    const data = finalData.map(item => item.amount);

    // 使用餐厅颜色映射
    const restaurantColors = generateRestaurantColors(consumptionData);
    const colors = finalData.map(item => {
        if (item.label === '其他') {
            return 'rgba(200, 200, 200, 0.8)'; // 其他类别颜色
        }
        if (item.merchant) {
            return restaurantColors[item.merchant]?.color || 'rgba(128, 128, 128, 0.8)';
        }
        return 'rgba(200, 200, 200, 0.8)';
    });

    window.restaurantPieChartInstance = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: colors,
                borderColor: colors.map(color => color.replace('0.8', '1')),
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 10,
                        boxWidth: 8,
                        font: {
                            size: 10
                        },
                        filter: function(item, data) {
                            // 只显示有名称的图例
                            return item.text !== '';
                        }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const percentage = ((context.parsed / totalAmount) * 100).toFixed(1);
                            const label = context.label || '其他';
                            return `${label}: ${context.parsed.toFixed(2)}元 (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

// 创建档口饼图（按具体条目，不合并）
function createVendorPieChart() {
    const ctx = document.getElementById('vendorPieChart').getContext('2d');

    if (typeof Chart === 'undefined') {
        console.error('Chart.js 未加载');
        return;
    }

    if (window.vendorPieChartInstance) {
        window.vendorPieChartInstance.destroy();
    }

    const { vendorData } = splitMerchantData(consumptionData);
    const totalAmount = getTotalAmount();
    const threshold = totalAmount * 0.02; // 2%阈值

    // 分离数据：大于2%的显示名称和颜色，小于2%的合并为"其他"
    const significantData = [];
    const otherData = { label: '其他', amount: 0 };

    vendorData.forEach(item => {
        if (item.amount >= threshold) {
            significantData.push(item);
        } else {
            otherData.amount += item.amount;
        }
    });

    // 合并数据：所有大于2%的显示名称和颜色，其他合并为"其他"
    const finalData = [...significantData];
    if (otherData.amount > 0) {
        finalData.push(otherData);
    }

    const labels = finalData.map(item => item.label || item.merchant || '');
    const data = finalData.map(item => item.amount);

    // 使用档口颜色映射
    const restaurantColors = generateRestaurantColors(consumptionData);
    const colors = finalData.map(item => {
        if (item.label === '其他') {
            return 'rgba(200, 200, 200, 0.8)'; // 其他类别颜色
        }
        if (item.merchant) {
            return getStallColor(restaurantColors, item.merchant);
        }
        return 'rgba(200, 200, 200, 0.8)';
    });

    window.vendorPieChartInstance = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: colors,
                borderColor: colors.map(color => color.replace('0.8', '1')),
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 10,
                        boxWidth: 8,
                        font: {
                            size: 10
                        },
                        filter: function(item, data) {
                            // 只显示有名称的图例
                            return item.text !== '';
                        }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const percentage = ((context.parsed / totalAmount) * 100).toFixed(1);
                            const label = context.label || '其他';
                            return `${label}: ${context.parsed.toFixed(2)}元 (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

// 显示餐厅榜单
function displayRestaurantRankingList() {
    const { restaurantData } = splitMerchantData(consumptionData);
    const sortedData = restaurantData.sort((a, b) => b.amount - a.amount).slice(0, 5);
    const container = document.getElementById('restaurantRankingList');

    container.innerHTML = '';
    sortedData.forEach((item, index) => {
        const rankingItem = document.createElement('div');
        rankingItem.className = 'ranking-item';
        rankingItem.innerHTML = `
            <div class="ranking-number">${index + 1}</div>
            <div class="ranking-info">
                <div class="ranking-name">${item.merchant}</div>
                <div class="ranking-amount">${item.amount.toFixed(2)}元</div>
            </div>
        `;
        container.appendChild(rankingItem);
    });
}

// 显示档口榜单
function displayVendorRankingList() {
    const { vendorData } = splitMerchantData(consumptionData);
    const sortedData = vendorData.sort((a, b) => b.amount - a.amount).slice(0, 5);
    const container = document.getElementById('vendorRankingList');

    container.innerHTML = '';
    sortedData.forEach((item, index) => {
        const rankingItem = document.createElement('div');
        rankingItem.className = 'ranking-item';
        rankingItem.innerHTML = `
            <div class="ranking-number">${index + 1}</div>
            <div class="ranking-info">
                <div class="ranking-name">${item.merchant}</div>
                <div class="ranking-amount">${item.amount.toFixed(2)}元</div>
            </div>
        `;
        container.appendChild(rankingItem);
    });
}

// 显示热门榜单
function displayRankingList() {
    // 已替换为双榜单功能
}

// 显示商家详情
function showMerchantDetails(merchant) {
    const item = consumptionData.find(d => d.merchant === merchant);
    if (item) {
        alert(`商家: ${item.merchant}\n消费金额: ${item.amount.toFixed(2)}元\n占比: ${item.percentage.toFixed(2)}%`);
    }
}

// 计算两个HSL颜色之间的角度距离
function colorDistance(hue1, hue2) {
    const diff = Math.abs(hue1 - hue2);
    return Math.min(diff, 360 - diff);
}

// 为新餐厅选择一个与现有颜色有足够距离的颜色
function selectDistinctColor(existingHues, minDistance = 30) {
    const maxAttempts = 100;
    let bestHue = null;
    let maxMinDistance = 0;

    for (let attempt = 0; attempt < maxAttempts; attempt++) {
        // 生成一个随机色调
        const newHue = Math.floor(Math.random() * 360);

        // 计算与所有现有颜色的最小距离
        let minCurrentDistance = 360;
        for (const existingHue of existingHues) {
            const distance = colorDistance(newHue, existingHue);
            minCurrentDistance = Math.min(minCurrentDistance, distance);
        }

        // 如果满足最小距离要求，直接返回
        if (minCurrentDistance >= minDistance) {
            return {
                hue: newHue,
                color: `hsla(${newHue}, 70%, 60%, 0.8)`,
                baseColor: `hsl(${newHue}, 70%, 60%)`
            };
        }

        // 记录最佳候选
        if (minCurrentDistance > maxMinDistance) {
            maxMinDistance = minCurrentDistance;
            bestHue = newHue;
        }
    }

    // 如果没有找到理想的颜色，返回最佳候选
    return {
        hue: bestHue || Math.floor(Math.random() * 360),
        color: `hsla(${bestHue || 0}, 70%, 60%, 0.8)`,
        baseColor: `hsl(${bestHue || 0}, 70%, 60%)`
    };
}

// 生成餐厅颜色映射 - 确保颜色差异
function generateRestaurantColors(data) {
    const restaurantColors = {};
    const restaurantNames = [];
    const existingHues = [];

    // 收集所有餐厅名称
    data.forEach(item => {
        const merchant = item.merchant;
        const parts = merchant.split('_');
        const restaurant = parts[0]; // 餐厅名称
        if (!restaurantNames.includes(restaurant)) {
            restaurantNames.push(restaurant);
        }
    });

    // 为每个餐厅选择不同的颜色
    restaurantNames.forEach(restaurant => {
        const colorInfo = selectDistinctColor(existingHues, 30); // 至少30度差异
        restaurantColors[restaurant] = colorInfo;
        existingHues.push(colorInfo.hue);
    });

    return restaurantColors;
}

// 根据餐厅和档口生成颜色
function getStallColor(restaurantColors, merchant) {
    const parts = merchant.split('_');
    const restaurant = parts[0];
    const stallName = parts.length > 1 ? parts[1] : merchant;

    if (!restaurantColors[restaurant]) {
        restaurantColors[restaurant] = hashStringToColor(restaurant);
    }

    const baseHue = restaurantColors[restaurant].hue;

    // 根据档口名称生成小的偏移量（±20度范围内）
    let stallHash = 0;
    for (let i = 0; i < stallName.length; i++) {
        stallHash = stallName.charCodeAt(i) + ((stallHash << 3) - stallHash);
    }

    // 计算偏移量，范围在 -20 到 +20 之间
    const offset = (Math.abs(stallHash) % 41) - 20;
    const newHue = (baseHue + offset + 360) % 360;

    return `hsla(${newHue}, 75%, 65%, 0.8)`;
}

// 工具函数
function showResults() {
    const container = document.getElementById('resultsContainer');
    if (container) {
        container.style.display = 'block';
        container.scrollIntoView();
    }
}

function hideResults() {
    const container = document.getElementById('resultsContainer');
    if (container) {
        container.style.display = 'none';
    }
}

function getTotalAmount() {
    return consumptionData.reduce((sum, item) => sum + item.amount, 0);
}

function generateGradientColors(count) {
    const colors = [];
    for (let i = 0; i < count; i++) {
        const hue = (i * 360 / count) % 360;
        colors.push(`hsla(${hue}, 70%, 60%, 0.8)`);
    }
    return colors;
}


// 响应式处理
window.addEventListener('resize', function() {
    if (barChart) {
        barChart.resize();
    }
    if (pieChart) {
        pieChart.resize();
    }
    if (lineChart) {
        lineChart.resize();
    }
    if (window.restaurantPieChartInstance) {
        window.restaurantPieChartInstance.resize();
    }
    if (window.vendorPieChartInstance) {
        window.vendorPieChartInstance.resize();
    }
    if (window.monthlyTotalChartInstance) {
        window.monthlyTotalChartInstance.resize();
    }
    if (window.monthlyTop3ChartInstance) {
        window.monthlyTop3ChartInstance.resize();
    }
});