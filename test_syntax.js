window = { addEventListener: function() {} }; document = { addEventListener: function() {}, getElementById: function() { return { value: '', addEventListener: function() {} }; } }; Chart = undefined; $ = undefined;
async function analyzeData() {
    console.log('开始分析数据...');

    const idserial = document.getElementById('idserial').value.trim();
    const servicehall = document.getElementById('servicehall').value.trim();
    const startDate = document.getElementById('startDate').value || '2025-01-01';
    const endDate = document.getElementById('endDate').value || '2025-12-31';

    if (!idserial || !servicehall) {
        alert('请填写学号和服务代码');
        return;
    }

    console.log('参数:', {idserial, servicehall, startDate, endDate});

    hideResults();

    try {
        const formData = new FormData();
        formData.append('idserial', idserial);
