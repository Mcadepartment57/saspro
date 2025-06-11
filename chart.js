window.chartInstances = window.chartInstances || {};

        // Chart IDs for reference
        const chartIds = [
            'salesTrendChart',
            'salesRegionChart',
            'salesFunnelChart',
            'salesCustomerChart',
            'salesSalespersonChart',
            'salesTargetAchievementChart',
            'salesByCategoryChart',
            'salesGrowthRateChart',
            'repeatVsNewSalesChart'
        ];

        // Object to store chart-specific date filters
        const chartFilters = {
            salesTrendChart: { selectedDate: null },
            salesRegionChart: { selectedDate: null },
            salesFunnelChart: { selectedDate: null },
            salesCustomerChart: { selectedDate: null },
            salesSalespersonChart: { selectedDate: null },
            salesTargetAchievementChart: { selectedDate: null },
            salesByCategoryChart: { selectedDate: null },
            salesGrowthRateChart: { selectedDate: null },
            repeatVsNewSalesChart: { selectedDate: null }
        };

        // Object to track if a chart is currently being updated
        const chartUpdating = {};

        // Global lock for loadDashboardData
        let isLoadingDashboard = false;

        // Filter popup toggle
        const filterBtn = document.getElementById('filterBtn');
        const filterPopup = document.getElementById('filterPopup');
        const filterPopupOverlay = document.getElementById('filterPopupOverlay');
        const closeFilterPopup = document.getElementById('closeFilterPopup');

        filterBtn.addEventListener('click', () => {
            filterPopup.classList.toggle('show');
            filterPopupOverlay.classList.toggle('show');
        });

        closeFilterPopup.addEventListener('click', () => {
            filterPopup.classList.remove('show');
            filterPopupOverlay.classList.remove('show');
        });

        filterPopupOverlay.addEventListener('click', () => {
            filterPopup.classList.remove('show');
            filterPopupOverlay.classList.remove('show');
        });

        // Helper function to format currency
        function formatCurrency(value) {
            return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(value);
        }

        // Helper function to format numbers in Indian number format (lakhs, crores)
        function formatNumber(value) {
            return new Intl.NumberFormat('en-IN').format(value);
        }

        // Helper function to format date for input
        function formatDateForInput(date) {
            return date.toISOString().split('T')[0];
        }

        // Helper function to format chart labels
        function formatChartLabels(labels, periodType) {
            if (!Array.isArray(labels)) {
                console.error('formatChartLabels: labels is not an array:', labels);
                return [];
            }
            if (typeof periodType !== 'string') {
                console.error('formatChartLabels: periodType is not a string:', periodType);
                return labels;
            }
            return labels.map(label => {
                if (typeof label !== 'string') {
                    console.error('formatChartLabels: label is not a string:', label);
                    return String(label);
                }
                switch (periodType) {
                    case 'MS':
                        const [year, month] = label.split('-');
                        const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
                        if (!year || !month || isNaN(parseInt(month))) {
                            console.error('formatChartLabels: Invalid date format for MS period:', label);
                            return label;
                        }
                        return `${monthNames[parseInt(month) - 1]} ${year}`;
                    case 'YS':
                        return label;
                    case 'QS':
                        const [yearQ, quarter] = label.split('-Q');
                        if (!yearQ || !quarter) {
                            console.error('formatChartLabels: Invalid date format for QS period:', label);
                            return label;
                        }
                        return `${yearQ}-Q${quarter}`;
                    default:
                        return label;
                }
            });
        }

        // Helper function to get period label
        function getPeriodLabel(periodType) {
            switch (periodType) {
                case 'MS':
                    return 'Month';
                case 'YS':
                    return 'Year';
                case 'QS':
                    return 'Quarter';
                default:
                    return 'Period';
            }
        }

        // Function to get filter parameters
        function getFilterParams() {
            return {
                periodType: document.getElementById('periodType').value || 'MS',
                startDate: document.getElementById('startDate').value || '2024-01-01',
                endDate: document.getElementById('endDate').value || '2025-12-31',
                forecastStart: document.getElementById('forecastStart').value || '2026-01-01',
                region: document.getElementById('regionSelect').value || 'all'
            };
        }

        // Function to populate date dropdowns
    function populateDateDropdowns() {
    const startDate = new Date('2023-01-01');
    const endDate = new Date('2025-05-01');
    const months = [];
    const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

    let current = new Date(startDate);
    while (current <= endDate) {
        const year = current.getFullYear();
        const month = current.getMonth();
        const formatted = `${monthNames[month]} ${year}`;
        const value = `${year}-${String(month + 1).padStart(2, '0')}-01`;
        months.push({ formatted, value });
        current.setMonth(current.getMonth() + 1);
    }
    months.reverse();

    const selects = document.querySelectorAll('.chart-date-select');
    if (selects.length === 0) {
        console.warn('No elements with class "chart-date-select" found in the DOM.');
        return;
    }

    selects.forEach(select => {
        if (!select) {
            console.error('Invalid select element encountered:', select);
            return;
        }
        select.innerHTML = '<option value="">Select Date</option>';
        months.forEach(month => {
            const option = document.createElement('option');
            option.value = month.value;
            option.textContent = month.formatted;
            select.appendChild(option);
        });
        select.value = '2025-05-01';
        const dropdown = select.closest('.options-dropdown');
        if (!dropdown) {
            console.warn('No parent .options-dropdown found for select:', select);
            return;
        }
        const chartId = dropdown.getAttribute('data-chart-id');
        if (!chartId) {
            console.warn('No data-chart-id attribute found for dropdown:', dropdown);
            return;
        }
        if (!chartFilters[chartId]) {
            console.warn(`chartFilters[${chartId}] is not defined.`);
            chartFilters[chartId] = { selectedDate: '2025-05-01' };
        }
        chartFilters[chartId].selectedDate = '2025-05-01';
    });
}

        // Function to populate regions
        

        // Function to update metric cards, top performers, and recent activity
        function loadMetricsAndPerformers(params) {
            const { startDate, endDate, region } = params;

            fetch(`/api/summary-metrics?start_date=${startDate}&end_date=${endDate}${region !== 'all' ? `&region=${region}` : ''}`)
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        document.getElementById('total-sales-error').style.display = 'block';
                        document.getElementById('total-sales-error').textContent = data.error;
                        document.getElementById('avg-order-value-error').style.display = 'block';
                        document.getElementById('avg-order-value-error').textContent = data.error;
                        return;
                    }
                    document.getElementById('total-sales').textContent = formatCurrency(data.total_sales);
                    document.getElementById('total-sales-subtext').textContent = 'Updated';
                    document.getElementById('avg-order-value').textContent = formatCurrency(data.avg_order_value);
                    document.getElementById('avg-order-value-subtext').textContent = 'Updated';
                })
                .catch(error => {
                    document.getElementById('total-sales-error').style.display = 'block';
                    document.getElementById('total-sales-error').textContent = 'Failed to load data';
                    document.getElementById('avg-order-value-error').style.display = 'block';
                    document.getElementById('avg-order-value-error').textContent = 'Failed to load data';
                });

            fetch(`/api/sales-orders-unique-customers?start_date=${startDate}&end_date=${endDate}${region !== 'all' ? `&region=${region}` : ''}`)
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        document.getElementById('new-customers-error').style.display = 'block';
                        document.getElementById('new-customers-error').textContent = data.error;
                        return;
                    }
                    document.getElementById('new-customers').textContent = formatNumber(data.new_customers);
                    document.getElementById('new-customers-subtext').textContent = 'Updated';
                })
                .catch(error => {
                    document.getElementById('new-customers-error').style.display = 'block';
                    document.getElementById('new-customers-error').textContent = 'Failed to load new customers';
                });

            fetch(`/api/sales-funnel?start_date=${startDate}&end_date=${endDate}${region !== 'all' ? `&region=${region}` : ''}`)
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        document.getElementById('conversion-rate-error').style.display = 'block';
                        document.getElementById('conversion-rate-error').textContent = data.error;
                        return;
                    }
                    const conversionRate = data.orders > 0 ? ((data.invoices / data.orders) * 100).toFixed(2) : 0;
                    document.getElementById('conversion-rate').textContent = `${conversionRate}%`;
                    document.getElementById('conversion-rate-subtext').textContent = 'Updated';
                })
                .catch(error => {
                    document.getElementById('conversion-rate-error').style.display = 'block';
                    document.getElementById('conversion-rate-error').textContent = 'Failed to load data';
                });

            fetch(`/api/sales-by-salesperson?start_date=${startDate}&end_date=${endDate}${region !== 'all' ? `&region=${region}` : ''}`)
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        document.getElementById('top-performers-error').style.display = 'block';
                        document.getElementById('top-performers-error').textContent = data.error;
                        return;
                    }
                    const topPerformersList = document.getElementById('top-performers');
                    topPerformersList.innerHTML = '';
                    data.salespersons.slice(0, 3).forEach((salesperson, index) => {
                        const sales = data.sales[index];
                        const li = document.createElement('li');
                        li.className = 'performer-item';
                        li.innerHTML = `
                            <img src="https://via.placeholder.com/48" alt="Profile">
                            <div class="performer-info">
                                <div class="performer-name">${salesperson}</div>
                                <div class="performer-sales">${formatCurrency(sales)} in sales</div>
                                <div class="performer-progress">
                                    <div class="performer-progress-bar" style="width: ${90 - index * 15}%;"></div>
                                </div>
                            </div>
                        `;
                        topPerformersList.appendChild(li);
                    });
                })
                .catch(error => {
                    document.getElementById('top-performers-error').style.display = 'block';
                    document.getElementById('top-performers-error').textContent = 'Failed to load data';
                });

            fetch(`/api/recent-activity?start_date=${startDate}&end_date=${endDate}${region !== 'all' ? `&region=${region}` : ''}`)
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        document.getElementById('recent-activity').innerHTML = `<li>Error: ${data.error}</li>`;
                        return;
                    }
                    const recentActivityList = document.getElementById('recent-activity');
                    recentActivityList.innerHTML = '';
                    data.activities.forEach(activity => {
                        const li = document.createElement('li');
                        li.className = `activity-item ${activity.type}`;
                        li.innerHTML = `
                            <i class="fas ${activity.type === 'order' ? 'fa-shopping-cart' : 'fa-user-plus'} activity-icon"></i>
                            <div class="activity-content">
                                <div class="activity-title">${activity.description}</div>
                                <div class="activity-details">${activity.details}</div>
                            </div>                        `;
                        recentActivityList.appendChild(li);
                    });
                })
                .catch(error => {
                    document.getElementById('recent-activity').innerHTML = `<li>Failed to load recent activity</li>`;
                });
        }

        // Function to destroy any existing chart on a canvas
        // Function to destroy any existing chart on a canvas
function destroyChart(chartId, canvasElement) {
    try {
        // Destroy chart instance from window.chartInstances if it exists
        if (window.chartInstances[chartId]) {
            console.log(`Destroying chart instance for ${chartId} from window.chartInstances`);
            window.chartInstances[chartId].destroy();
            window.chartInstances[chartId] = null;
            delete window.chartInstances[chartId]; // Explicitly remove from object
        }

        // Clear all Chart.js instances associated with this canvas
        Object.values(Chart.instances).forEach(chart => {
            if (chart.canvas === canvasElement) {
                console.log(`Destroying chart instance with ID ${chart.id} on canvas ${chartId}`);
                chart.destroy();
            }
        });

        // Force clear Chart.js internal registry for this canvas
        Object.keys(Chart.instances).forEach(id => {
            if (Chart.instances[id] && Chart.instances[id].canvas === canvasElement) {
                console.log(`Removing chart ID ${id} from Chart.js registry`);
                delete Chart.instances[id];
            }
        });

        // Clear canvas context and reset attributes
        if (canvasElement) {
            const ctx = canvasElement.getContext('2d');
            if (ctx) {
                ctx.clearRect(0, 0, canvasElement.width, canvasElement.height);
                canvasElement.width = canvasElement.width; // Reset canvas size
                canvasElement.height = canvasElement.height; // Ensure height is reset
            }
        }

        // Verify no charts remain
        const remainingCharts = Object.values(Chart.instances).filter(chart => chart.canvas === canvasElement);
        if (remainingCharts.length > 0) {
            console.warn(`Charts still exist on canvas ${chartId} after destruction:`, remainingCharts);
        } else {
            console.log(`Canvas ${chartId} is clear of Chart.js instances`);
        }
    } catch (error) {
        console.error(`Error destroying chart for ${chartId}:`, error);
    }
}

        // Function to update charts with strict update control
        function updateCharts(params, specificChartId = null) {
            const { periodType, startDate, endDate, region, forecastStart } = params;

            const chartsToUpdate = specificChartId ? [specificChartId] : chartIds;

            chartsToUpdate.forEach(chartId => {
                // Skip if this chart is already being updated
                if (chartUpdating[chartId]) {
                    console.log(`Chart ${chartId} is already being updated. Skipping this update.`);
                    return;
                }

                // Mark this chart as being updated
                chartUpdating[chartId] = true;

                const canvasElement = document.getElementById(chartId);
if (!canvasElement) {
    console.warn(`Canvas element for chart ID "${chartId}" not found in the DOM. Skipping chart update.`);
    chartUpdating[chartId] = false;
    return;
}
const ctx = canvasElement.getContext('2d');
if (!ctx) {
    console.warn(`Failed to get 2D context for canvas ID "${chartId}". Skipping chart update.`);
    chartUpdating[chartId] = false;
    return;
}

                const loadingErrorMap = {
                    'salesTrendChart': { loading: 'chartLoading', error: 'sales-trend-error' },
                    'salesRegionChart': { loading: 'regionChartLoading', error: 'sales-region-error' },
                    'salesFunnelChart': { loading: 'funnelLoading', error: 'sales-funnel-error' },
                    'salesCustomerChart': { loading: 'customerLoading', error: 'sales-customer-error' },
                    'salesSalespersonChart': { loading: 'salespersonLoading', error: 'sales-salesperson-error' },
            'salesTargetAchievementChart': { loading: 'targetAchievementLoading', error: 'sales-target-achievement-error' },
            'salesByCategoryChart': { loading: 'categoryLoading', error: 'sales-category-error' },
            'salesGrowthRateChart': { loading: 'growthRateLoading', error: 'sales-growth-rate-error' },
            'repeatVsNewSalesChart': { loading: 'repeatVsNewLoading', error: 'repeat-vs-new-error' }
        };

        const loadingElement = document.getElementById(loadingErrorMap[chartId].loading);
        const errorElement = document.getElementById(loadingErrorMap[chartId].error);
        const chartTypeSelect = document.querySelector(`select[data-chart-id="${chartId}"]`);
        const chartType = chartTypeSelect ? chartTypeSelect.value : 'bar';

        if (!loadingElement || !errorElement) {
            console.warn(`Loading or error element missing for chart ID "${chartId}". Proceeding without loading/error display.`);
        }

        if (loadingElement) loadingElement.style.display = 'flex';
        if (errorElement) errorElement.style.display = 'none';

        // Destroy any existing chart on this canvas
        destroyChart(chartId, canvasElement);

        let endpoint, chartConfig;
const selectedDate = chartFilters[chartId].selectedDate;
switch (chartId) {
    case 'salesTrendChart':
    console.log(`Initializing salesTrendChart with endpoint: ${endpoint}`);
    endpoint = `/api/sales-trend?period_type=${periodType}&start_date=${startDate}&end_date=${endDate}&forecast_start=${forecastStart}${selectedDate ? `&selected_date=${selectedDate}` : ''}`;
    chartConfig = (data) => {
        // Validate data structure
        if (!data || !data.actual || !data.predicted || !data.forecast) {
            console.error('Invalid data structure:', data);
            throw new Error('Invalid or missing sales trend data');
        }
        const allPeriods = [...new Set([
            ...(data.actual.periods || []),
            ...(data.predicted.periods || []),
            ...(data.forecast.periods || [])
        ])].sort();
        const actualSales = allPeriods.map(period => {
            const idx = data.actual.periods ? data.actual.periods.indexOf(period) : -1;
            return idx !== -1 ? data.actual.sales[idx] : null;
        });
        const predictedSales = allPeriods.map(period => {
            const idx = data.predicted.periods ? data.predicted.periods.indexOf(period) : -1;
            return idx !== -1 ? data.predicted.sales[idx] : null;
        });
        const forecastSales = allPeriods.map(period => {
            const idx = data.forecast.periods ? data.forecast.periods.indexOf(period) : -1;
            return idx !== -1 ? data.forecast.sales[idx] : null;
        });
        return {
            type: chartType === 'area' ? 'line' : chartType,
            data: {
                labels: formatChartLabels(allPeriods, data.period_type || periodType),
                datasets: [
                    {
                        label: 'Actual Sales ($)',
                        data: actualSales,
                        borderColor: '#4e73df',
                        backgroundColor: chartType === 'area' ? 'rgba(78, 115, 223, 0.2)' : 'rgba(78, 115, 223, 0.6)',
                        fill: chartType === 'area',
                        pointRadius: 5,
                        pointBackgroundColor: '#4e73df',
                        spanGaps: true
                    },
                    {
                        label: 'Predicted Sales ($)',
                        data: predictedSales,
                        borderColor: '#1cc88a',
                        backgroundColor: chartType === 'area' ? 'rgba(28, 200, 138, 0.2)' : 'rgba(28, 200, 138, 0.6)',
                        borderDash: [5, 5],
                        fill: chartType === 'area',
                        pointRadius: 5,
                        pointBackgroundColor: '#1cc88a',
                        spanGaps: true
                    },
                    {
                        label: 'Forecasted Sales ($)',
                        data: forecastSales,
                        borderColor: '#f6c23e',
                        backgroundColor: chartType === 'area' ? 'rgba(246, 194, 62, 0.2)' : 'rgba(246, 194, 62, 0.6)',
                        borderDash: [5, 5],
                        fill: chartType === 'area',
                        pointRadius: 5,
                        pointBackgroundColor: '#f6c23e',
                        spanGaps: true
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        title: { display: true, text: getPeriodLabel(data.period_type || periodType) },
                        grid: { display: false }
                    },
                    y: {
                        title: { display: true, text: 'Sales Amount ($)' },
                        beginAtZero: true,
                        ticks: {
                            callback: (value) => `$${value.toLocaleString()}`
                        }
                    }
                },
                plugins: {
                    legend: { display: true, position: 'top' },
                    tooltip: {
                        callbacks: {
                            label: (tooltipItem) => {
                                const value = tooltipItem.raw;
                                return value !== null ? `${tooltipItem.dataset.label}: $${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '';
                            }
                        }
                    },
                    title: { display: true, text: 'Monthly Sales Trend (2024-2025)' }
                }
            }
        };
    };
    break;
case 'salesRegionChart':
console.log(`Initializing salesRegionChart with endpoint: ${endpoint}`);
    endpoint = `/api/sales-by-region${region !== 'all' ? `?region_label=${encodeURIComponent(region)}` : ''}${selectedDate ? `${region !== 'all' ? '&' : '?'}${selectedDate}` : ''}`;
    chartConfig = (data) => ({
        type: chartType,
        data: {
            labels: data.regions,
            datasets: [{
                label: 'Sales ($)',
                data: data.sales,
                backgroundColor: 'rgba(153, 102, 255, 0.6)',
                borderColor: 'rgba(153, 102, 255, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { title: { display: true, text: 'Region' }, ticks: { autoSkip: true, maxRotation: 45, minRotation: 45 }, grid: { display: false } },
                y: { title: { display: true, text: 'Sales Amount ($)' }, beginAtZero: true }
            },
            plugins: { legend: { display: true, position: 'top' }, tooltip: { callbacks: { label: (tooltipItem) => `${tooltipItem.dataset.label}: $${tooltipItem.raw.toFixed(2)}` } } }
        }
    });
    break;

            case 'salesFunnelChart':
                endpoint = `/api/sales-funnel${selectedDate ? `?selected_date=${selectedDate}` : ''}`;
                chartConfig = (data) => {
                    const chartTypeFinal = (chartType === 'funnel' && typeof Chart.FunnelChart !== 'undefined') ? 'funnel' : 'bar';
                    return {
                        type: chartTypeFinal,
                        data: {
                            labels: ['Leads', 'Quotes', 'Orders', 'Invoices'],
                            datasets: [{
                                label: 'Count',
                                data: [data.leads, data.quotes, data.orders, data.invoices],
                                backgroundColor: [
                                    'rgba(255, 99, 132, 0.6)',
                                    'rgba(54, 162, 235, 0.6)',
                                    'rgba(75, 192, 192, 0.6)',
                                    'rgba(255, 206, 86, 0.6)'
                                ],
                                borderColor: [
                                    'rgba(255, 99, 132, 1)',
                                    'rgba(54, 162, 235, 1)',
                                    'rgba(75, 192, 192, 1)',
                                    'rgba(255, 206, 86, 1)'
                                ],
                                borderWidth: 1
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            scales: chartTypeFinal === 'funnel' ? { x: { display: false }, y: { display: false } } : {
                                x: { title: { display: true, text: 'Count' }, beginAtZero: true, reverse: true },
                                y: { title: { display: true, text: 'Stage' }, grid: { display: false } }
                            },
                            indexAxis: chartTypeFinal === 'bar' ? 'y' : undefined,
                            plugins: { legend: { display: true, position: 'top' }, tooltip: { callbacks: { label: (tooltipItem) => `${tooltipItem.dataset.label}: ${tooltipItem.raw}` } } }
                        }
                    };
                };
                break;

            case 'salesCustomerChart':
                endpoint = `/api/sales-by-customer${selectedDate ? `?selected_date=${selectedDate}` : ''}`;
                chartConfig = (data) => ({
                    type: chartType,
                    data: {
                        labels: data.customers.slice(0, 10),
                        datasets: [
                            {
                                label: 'Revenue ($)',
                                data: data.revenues.slice(0, 10),
                                backgroundColor: 'rgba(75, 192, 192, 0.6)',
                                borderColor: 'rgba(75, 192, 192, 1)',
                                borderWidth: 1,
                                yAxisID: 'y'
                            },
                            {
                                label: 'Cumulative %',
                                data: data.cumulative_percentages.slice(0, 10),
                                type: 'line',
                                borderColor: 'rgba(255, 99, 132, 1)',
                                backgroundColor: 'rgba(255, 99, 132, 0.2)',
                                fill: false,
                                yAxisID: 'y1',
                                pointRadius: 5
                            }
                        ]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            x: { title: { display: true, text: 'Customer' }, grid: { display: false } },
                            y: { title: { display: true, text: 'Revenue ($)' }, beginAtZero: true, position: 'left' },
                            y1: { title: { display: true, text: 'Cumulative %' }, beginAtZero: true, position: 'right', max: 100, ticks: { callback: (value) => `${value}%` } }
                        },
                        plugins: {
                            legend: { display: true, position: 'top' },
                            tooltip: {
                                callbacks: {
                                    label: (tooltipItem) => tooltipItem.dataset.label === 'Cumulative %' ? `${tooltipItem.dataset.label}: ${tooltipItem.raw.toFixed(2)}%` : `${tooltipItem.dataset.label}: $${tooltipItem.raw.toFixed(2)}`
                                }
                            }
                        }
                    }
                });
                break;

            case 'salesSalespersonChart':
                endpoint = `/api/sales-by-salesperson${selectedDate ? `?selected_date=${selectedDate}` : ''}`;
                chartConfig = (data) => ({
                    type: chartType,
                    data: {
                        labels: data.salespersons,
                        datasets: [{
                            label: 'Sales ($)',
                            data: data.sales,
                            backgroundColor: 'rgba(54, 162, 235, 0.6)',
                            borderColor: 'rgba(54, 162, 235, 1)',
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            x: { title: { display: true, text: 'Salesperson' }, ticks: { autoSkip: true, maxRotation: 45, minRotation: 45 }, grid: { display: false } },
                            y: { title: { display: true, text: 'Sales Amount ($)' }, beginAtZero: true }
                        },
                        plugins: { legend: { display: true, position: 'top' }, tooltip: { callbacks: { label: (tooltipItem) => `${tooltipItem.dataset.label}: $${tooltipItem.raw.toFixed(2)}` } } }
                    }
                });
                break;

            case 'salesTargetAchievementChart':
                endpoint = `/api/sales-target-vs-achievement${selectedDate ? `?selected_date=${selectedDate}` : ''}`;
                chartConfig = (data) => ({
                    type: chartType,
                    data: {
                        labels: data.labels,
                        datasets: [
                            {
                                label: 'Target (₹)',
                                data: data.targets,
                                backgroundColor: 'rgba(255, 99, 132, 0.6)',
                                borderColor: 'rgba(255, 99, 132, 1)',
                                borderWidth: 1
                            },
                            {
                                label: 'Achieved (₹)',
                                data: data.achieved,
                                backgroundColor: 'rgba(75, 192, 192, 0.6)',
                                borderColor: 'rgba(75, 192, 192, 1)',
                                borderWidth: 1
                            }
                        ]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            x: { title: { display: true, text: 'Salesperson - Period' }, ticks: { autoSkip: true, maxRotation: 45, minRotation: 45 }, grid: { display: false } },
                            y: {
                                title: { display: true, text: 'Amount (₹)' },
                                beginAtZero: false,
                                min: 1000000,
                                ticks: { callback: (value) => `₹${(value / 100000).toFixed(0)}L` }
                            }
                        },
                        plugins: {
                            legend: { display: true, position: 'top' },
                            tooltip: {
                                callbacks: {
                                    label: (tooltipItem) => {
                                        const index = tooltipItem.dataIndex;
                                        const percentage = data.percentages[index];
                                        return `${tooltipItem.dataset.label}: ₹${(tooltipItem.raw / 100000).toFixed(2)}L${tooltipItem.dataset.label === 'Achieved' ? ` (${percentage.toFixed(2)}% of Target)` : ''}`;
                                    }
                                }
                            }
                        }
                    }
                });
                break;

            case 'salesByCategoryChart':
                endpoint = `/api/sales-by-category?period_type=${periodType}${selectedDate ? `&selected_date=${selectedDate}` : `&start_date=${startDate}&end_date=${endDate}`}`;
                chartConfig = (data) => ({
                    type: chartType,
                    data: {
                        labels: data.categories,
                        datasets: [{
                            label: 'Sales Distribution (%)',
                            data: data.sales,
                            backgroundColor: [
                                'rgba(255, 99, 132, 0.6)',
                                'rgba(54, 162, 235, 0.6)',
                                'rgba(75, 192, 192, 0.6)',
                                'rgba(255, 206, 86, 0.6)',
                                'rgba(153, 102, 255, 0.6)'
                            ],
                            borderColor: [
                                'rgba(255, 99, 132, 1)',
                                'rgba(54, 162, 235, 1)',
                                'rgba(75, 192, 192, 1)',
                                'rgba(255, 206, 86, 1)',
                                'rgba(153, 102, 255, 1)'
                            ],
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { display: true, position: 'top' }, tooltip: { callbacks: { label: (tooltipItem) => `${tooltipItem.label}: ${tooltipItem.raw}%` } } }
                    }
                });
                break;

            case 'salesGrowthRateChart':
                endpoint = '/api/sales-growth-rate?period_type=MS';
                if (selectedDate && selectedDate !== 'all') {
                    const selected = new Date(selectedDate);
                    const year = selected.getFullYear();
                    const month = selected.getMonth();
                    const selectedMonthStart = `${year}-${String(month + 1).padStart(2, '0')}-01`;
                    const selectedMonthEnd = new Date(year, month + 1, 0).toISOString().split('T')[0];
                    const prevMonthStart = new Date(year, month - 1, 1).toISOString().split('T')[0];
                    endpoint += `&start_date=${prevMonthStart}&end_date=${selectedMonthEnd}`;
                } else {
                    endpoint += `&start_date=${startDate}&end_date=${endDate}`;
                }
                chartConfig = (data) => {
                    const isAllMonths = selectedDate === 'all' || !selectedDate;
                    const chartTypeFinal = isAllMonths || data.growth_rates.length > 1 ? 'line' : 'bar';
                    const selectedIndex = data.periods.length - 1;
                    const selectedDateLabel = formatChartLabels(data.periods, data.period_type)[selectedIndex];
                    const annotationConfig = (!isAllMonths && selectedDateLabel && data.growth_rates[selectedIndex]) ? {
                        annotations: {
                            selectedPoint: {
                                type: chartTypeFinal === 'bar' ? 'box' : 'point',
                                xMin: selectedDateLabel,
                                xMax: selectedDateLabel,
                                yMin: chartTypeFinal === 'bar' ? 0 : data.growth_rates[selectedIndex],
                                yMax: data.growth_rates[selectedIndex],
                                backgroundColor: chartTypeFinal === 'bar' ? 'rgba(255, 99, 132, 0.2)' : undefined,
                                radius: chartTypeFinal === 'line' ? 8 : undefined,
                                borderColor: 'rgba(255, 99, 132, 1)',
                                borderWidth: chartTypeFinal === 'bar' ? 2 : undefined,
                                label: {
                                    display: true,
                                    content: `Growth: ${data.growth_rates[selectedIndex].toFixed(2)}%`,
                                    backgroundColor: 'rgba(255, 99, 132, 0.8)',
                                    color: '#fff',
                                    font: { weight: 'bold', size: 12 },
                                    position: 'center',
                                    yAdjust: chartTypeFinal === 'bar' ? -20 : -20
                                }
                            }
                        }
                    } : {};
                    return {
                        type: chartTypeFinal,
                        data: {
                            labels: formatChartLabels(data.periods, data.period_type),
                            datasets: [{
                                label: 'Growth Rate (%)',
                                data: data.growth_rates,
                                borderColor: 'rgba(255, 99, 132, 1)',
                                backgroundColor: chartTypeFinal === 'bar' ? 'rgba(255, 99, 132, 0.6)' : 'rgba(255, 99, 132, 0.2)',
                                fill: chartTypeFinal === 'line' ? false : true,
                                pointRadius: chartTypeFinal === 'line' ? 5 : 0,
                                pointBackgroundColor: 'rgba(255, 99, 132, 1)',
                                spanGaps: true
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            scales: {
                                x: { title: { display: true, text: 'Month' }, grid: { display: false }, ticks: { autoSkip: isAllMonths, maxRotation: isAllMonths ? 45 : 0, minRotation: isAllMonths ? 45 : 0 } },
                                y: { title: { display: true, text: 'Growth Rate (%)' }, beginAtZero: false, ticks: { callback: (value) => `${value}%` } }
                            },
                            plugins: { legend: { display: true, position: 'top' }, tooltip: { callbacks: { label: (tooltipItem) => `${tooltipItem.dataset.label}: ${tooltipItem.raw.toFixed(2)}%` } }, annotation: annotationConfig }
                        }
                    };
                };
                break;

            case 'repeatVsNewSalesChart':
                endpoint = `/api/repeat-vs-new-sales?period_type=${periodType}${selectedDate ? `&selected_date=${selectedDate}` : `&start_date=${startDate}&end_date=${endDate}`}`;
                chartConfig = (data) => ({
                    type: chartType,
                    data: {
                        labels: formatChartLabels(data.periods, data.period_type),
                        datasets: [
                            {
                                label: 'Repeat Customer Sales ($)',
                                data: data.repeat_sales,
                                backgroundColor: 'rgba(54, 162, 235, 0.6)',
                                borderColor: 'rgba(54, 162, 235, 1)',
                                borderWidth: 1
                            },
                            {
                                label: 'New Customer Sales ($)',
                                data: data.new_sales,
                                backgroundColor: 'rgba(255, 99, 132, 0.6)',
                                borderColor: 'rgba(255, 99, 132, 1)',
                                borderWidth: 1
                            }
                        ]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            x: { title: { display: true, text: getPeriodLabel(data.period_type) }, grid: { display: false } },
                            y: { title: { display: true, text: 'Sales Amount ($)' }, beginAtZero: true }
                        },
                        plugins: { legend: { display: true, position: 'top' }, tooltip: { callbacks: { label: (tooltipItem) => `${tooltipItem.dataset.label}: $${tooltipItem.raw.toFixed(2)}` } } }
                    }
                });
                break;

            default:
                chartUpdating[chartId] = false;
                return;
        }

        console.log(`Fetching ${chartId} data from: ${endpoint}`);
        fetch(endpoint)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`Failed to fetch ${chartId} data: ${response.status} ${response.statusText}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.error) {
                    if (loadingElement) loadingElement.style.display = 'none';
                    if (errorElement) {
                        errorElement.textContent = data.error;
                        errorElement.style.display = 'block';
                    } else {
                        console.warn(`No error element to display error for ${chartId}: ${data.error}`);
                    }
                    return;
                }
                try {
                    const ctx = canvasElement.getContext('2d');
                    // Reset canvas attributes to ensure a clean state
                    canvasElement.width = canvasElement.width; // Forces a reset of the canvas
                    ctx.clearRect(0, 0, canvasElement.width, canvasElement.height);
                    console.log(`Creating new chart for ${chartId}`);
                    window.chartInstances[chartId] = new Chart(ctx, chartConfig(data));
                    if (loadingElement) loadingElement.style.display = 'none';
                    document.querySelector(`button[data-chart-id="${chartId}"]`)?.classList.remove('disabled');
                } catch (error) {
                    console.error(`Error creating chart for ${chartId}:`, error);
                    throw error;
                }
            })
            .catch(error => {
                console.error(`Error fetching ${chartId} data:`, error);
                if (loadingElement) loadingElement.style.display = 'none';
                if (errorElement) {
                    errorElement.textContent = `Failed to load chart data: ${error.message}`;
                    errorElement.style.display = 'block';
                } else {
                    console.warn(`No error element to display error for ${chartId}: ${error.message}`);
                }
                document.querySelector(`button[data-chart-id="${chartId}"]`)?.classList.add('disabled');
            })
            .finally(() => {
                // Mark this chart as no longer being updated
                chartUpdating[chartId] = false;
                console.log(`Finished updating chart ${chartId}`);
            });
    });
}

// Function to load all dashboard data with a global lock
function loadDashboardData() {
    if (isLoadingDashboard) {
        console.log('Dashboard is already loading. Skipping this call.');
        return;
    }

    isLoadingDashboard = true;
    const params = getFilterParams();
    loadMetricsAndPerformers(params);
    updateCharts(params);
    isLoadingDashboard = false;
}

// Apply and Reset Filters (Global Filter)
document.getElementById('applyFilters').addEventListener('click', () => {
    const params = getFilterParams();
    const startDateObj = new Date(params.startDate);
    const endDateObj = new Date(params.endDate);
    const forecastStartObj = new Date(params.forecastStart);
    if (startDateObj > endDateObj) {
        alert('Start Date cannot be after End Date.');
        return;
    }
    if (forecastStartObj <= endDateObj) {
        alert('Forecast Start must be after End Date.');
        return;
    }
    Object.keys(chartFilters).forEach(chartId => {
        chartFilters[chartId].selectedDate = null;
    });
    populateDateDropdowns();
    loadDashboardData();
    filterPopup.classList.remove('show');
    filterPopupOverlay.classList.remove('show');
});

document.getElementById('resetFilters').addEventListener('click', () => {
    console.log('Reset filters triggered, clearing charts and reloading data');
    document.getElementById('periodType').value = 'MS';
    const today = new Date();
    const twoYearsAgo = new Date();
    twoYearsAgo.setFullYear(today.getFullYear() - 2);
    document.getElementById('startDate').value = formatDateForInput(twoYearsAgo);
    document.getElementById('endDate').value = formatDateForInput(today);
    document.getElementById('forecastStart').value = '2026-01-01';
    document.getElementById('regionSelect').value = 'all';
    Object.keys(chartFilters).forEach(chartId => {
        chartFilters[chartId].selectedDate = null;
        const dropdown = document.querySelector(`.options-dropdown[data-chart-id="${chartId}"]`);
        if (dropdown) {
            const select = dropdown.querySelector('.chart-date-select');
            if (select) select.value = '';
        }
    });
    populateDateDropdowns();
    loadDashboardData();
    filterPopup.classList.remove('show');
    filterPopupOverlay.classList.remove('show');
});

// Chart-specific filter apply buttons (3-dot menu)
document.querySelectorAll('.apply-chart-filter').forEach(button => {
    button.addEventListener('click', (e) => {
        const chartId = button.getAttribute('data-chart-id');
        const dropdown = document.querySelector(`.options-dropdown[data-chart-id="${chartId}"]`);
        const dateSelect = dropdown.querySelector('.chart-date-select');
        chartFilters[chartId].selectedDate = dateSelect.value || null;
        dropdown.classList.remove('show');
        updateCharts(getFilterParams(), chartId);
    });
});

// Region select change (affects all charts)
document.getElementById('regionSelect').addEventListener('change', loadDashboardData);

// Full-Screen Functionality
const modal = document.getElementById('chartModal');
const modalCanvas = document.getElementById('modalCanvas');
const modalClose = document.querySelector('.modal-close');
let modalChart = null;

document.querySelectorAll('.fullscreen-btn').forEach(button => {
    button.addEventListener('click', (e) => {
        e.stopPropagation();
        const chartId = button.getAttribute('data-chart-id');
        const chartInstance = window.chartInstances[chartId];
        if (chartInstance) {
            if (modalChart) {
                modalChart.destroy();
                modalChart = null;
            }
            modal.style.display = 'flex';
            const ctx = modalCanvas.getContext('2d');
            ctx.clearRect(0, 0, modalCanvas.width, modalCanvas.height);
            modalCanvas.width = modalCanvas.width; // Reset canvas
            modalChart = new Chart(modalCanvas, {
                type: chartInstance.config.type,
                data: chartInstance.config.data,
                options: chartInstance.config.options
            });
        } else {
            alert('Chart is still loading. Please wait a moment and try again.');
        }
    });
});

modalClose.addEventListener('click', () => {
    modal.style.display = 'none';
    if (modalChart) {
        console.log('Destroying modal chart');
        modalChart.destroy();
        modalChart = null;
        // Clear modal canvas from Chart.js registry
        Object.keys(Chart.instances).forEach(id => {
            if (Chart.instances[id].canvas === modalCanvas) {
                console.log(`Removing modal chart ID ${id} from Chart.js registry`);
                delete Chart.instances[id];
            }
        });
    }
    const ctx = modalCanvas.getContext('2d');
    ctx.clearRect(0, 0, modalCanvas.width, modalCanvas.height);
    modalCanvas.width = modalCanvas.width; // Reset canvas
});

// Close dropdown when clicking outside
document.addEventListener('click', (e) => {
    if (!e.target.closest('.more-options-btn') && !e.target.closest('.options-dropdown')) {
        document.querySelectorAll('.options-dropdown').forEach(dropdown => {
            dropdown.classList.remove('show');
        });
    }
});

// Chart Type Change Handler
document.querySelectorAll('.chart-type-select').forEach(select => {
    select.addEventListener('change', (e) => {
        const chartId = e.target.getAttribute('data-chart-id');
        const newType = e.target.value;
        const chartInstance = window.chartInstances[chartId];
        if (chartInstance) {
            const originalScales = chartInstance.config.options.scales || {};
            const effectiveType = newType === 'area' ? 'line' : (newType === 'funnel' && typeof Chart.FunnelChart === 'undefined') ? 'bar' : newType;
            chartInstance.config.type = effectiveType;

            const updateBackgroundColor = (color, fromOpacity, toOpacity) => {
                if (Array.isArray(color)) {
                    return color.map(c => c.replace(fromOpacity, toOpacity));
                }
                return color.replace(fromOpacity, toOpacity);
            };

            if (newType === 'area') {
                chartInstance.config.data.datasets.forEach(dataset => {
                    dataset.fill = true;
                    dataset.backgroundColor = updateBackgroundColor(dataset.backgroundColor, '0.6', '0.2');
                });
            } else {
                chartInstance.config.data.datasets.forEach(dataset => {
                    dataset.fill = false;
                    dataset.backgroundColor = updateBackgroundColor(dataset.backgroundColor, '0.2', '0.6');
                });
            }

            if (newType === 'funnel' && effectiveType === 'bar') {
                chartInstance.config.options.indexAxis = 'y';
                chartInstance.config.options.scales = { 
                    x: { title: { display: true, text: 'Count' }, beginAtZero: true, reverse: true }, 
                    y: { title: { display: true, text: 'Stage' }, grid: { display: false } } 
                };
            } else if (effectiveType === 'bar' && !['funnel', 'area'].includes(newType)) {
                chartInstance.config.options.indexAxis = 'x';
                chartInstance.config.options.scales = { 
                    x: { title: { display: true, text: chartInstance.config.data.datasets[0].label.split(' ')[0] }, grid: { display: false } }, 
                    y: { title: { display: true, text: chartInstance.config.data.datasets[0].label }, beginAtZero: true } 
                };
            } else {
                chartInstance.config.options.indexAxis = undefined;
                chartInstance.config.options.scales = originalScales;
            }

            chartInstance.update();
        }
    });
});

// Initialize dashboard on page load
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM fully loaded, initializing dashboard');
    
    // Initialize filters
    const today = new Date();
    const twoYearsAgo = new Date();
    twoYearsAgo.setFullYear(today.getFullYear() - 2);
    document.getElementById('startDate').value = formatDateForInput(twoYearsAgo);
    document.getElementById('endDate').value = formatDateForInput(today);
    document.getElementById('forecastStart').value = '2026-01-01';
    
    // Populate dropdowns
    populateDateDropdowns();
    
    // Load dashboard data
    loadDashboardData();
    
    // Funnel chart warning
    if (typeof Chart.FunnelChart === 'undefined') {
        console.warn('Funnel chart type not loaded. Falling back to bar chart for funnel.');
    }
    
    // Recent activity and top performers
    const recentActivityFilter = document.getElementById('recentActivityFilter');
    const topPerformersFilter = document.getElementById('topPerformersFilter');
    const recentActivityList = document.getElementById('recent-activity');
    const topPerformersList = document.getElementById('top-performers');

    const updateRecentActivity = async (filter) => {
        try {
            const response = await fetch(`/api/recent-activity?filter=${filter}`);
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || 'Failed to fetch recent activity');
            recentActivityList.innerHTML = '';
            if (!data.activities || data.activities.length === 0) {
                recentActivityList.innerHTML = '<li>No activities found for this period.</li>';
                return;
            }
            data.activities.forEach(item => {
                const li = document.createElement('li');
                li.className = `activity-item ${item.type}`;
                li.innerHTML = `
                    <i class="fas fa-${item.type === 'order' ? 'shopping-cart' : 'user-plus'} activity-icon"></i>
                    <div class="activity-content">
                        <div class="activity-title">${item.description}</div>
                        <div class="activity-details">${item.details}</div>
                    </div>
                    ${item.time ? `<div class="activity-time">${item.time}</div>` : ''}
                `;
                recentActivityList.appendChild(li);
            });
        } catch (error) {
            console.error('Error fetching recent activity:', error);
            recentActivityList.innerHTML = `<li class="text-red-500">Error loading data: ${error.message}</li>`;
        }
    };

    const updateTopPerformers = async (filter) => {
        try {
            const response = await fetch(`/api/top-performers?filter=${filter}`);
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || 'Failed to fetch top performers');
            topPerformersList.innerHTML = '';
            if (!data || data.length === 0) {
                topPerformersList.innerHTML = '<li>No top performers found for this period.</li>';
                return;
            }
            data.forEach(item => {
                const li = document.createElement('li');
                li.className = 'performer-item';
                li.innerHTML = `
                    <img src="${item.image}" alt="Profile">
                    <div class="performer-info">
                        <div class="performer-name">${item.name}</div>
                        <div class="performer-sales">${item.sales}</div>
                        <div class="performer-progress">
                            <div class="performer-progress-bar" style="width: ${item.progress}%;"></div>
                        </div>
                    </div>
                `;
                topPerformersList.appendChild(li);
            });
        } catch (error) {
            console.error('Error fetching top performers:', error);
            topPerformersList.innerHTML = `<li class="text-red-500">Error loading data: ${error.message}</li>`;
        }
    };

    recentActivityFilter.addEventListener('change', (e) => {
        updateRecentActivity(e.target.value);
    });

    topPerformersFilter.addEventListener('change', (e) => {
        updateTopPerformers(e.target.value);
    });

    updateRecentActivity(recentActivityFilter.value);
    updateTopPerformers(topPerformersFilter.value);
});


// Function to fetch and update Pending Orders
const updatePendingOrders = async () => {
    const pendingOrdersBody = document.getElementById('pending-orders-body');
    try {
        const response = await fetch('/api/pending-orders');
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'Failed to fetch pending orders');

        // Clear current table body
        pendingOrdersBody.innerHTML = '';

        // Check if data exists
        if (!data || data.length === 0) {
            pendingOrdersBody.innerHTML = '<tr><td colspan="6">No pending orders found.</td></tr>';
            return;
        }

        // Populate with new data
        data.forEach(item => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td class="border p-2">${item.order_id}</td>
                <td class="border p-2">${item.customer_name}</td>
                <td class="border p-2">${item.salesperson_name}</td>
                <td class="border p-2">${item.order_date}</td>
                <td class="border p-2">${item.total_amount}</td>
                <td class="border p-2">
                    <span class="text-blue-500 hover:underline" onclick="alert('View details for Order ID: ${item.order_id}')">View Details</span>
                </td>
            `;
            pendingOrdersBody.appendChild(tr);
        });
    } catch (error) {
        console.error('Error fetching pending orders:', error);
        pendingOrdersBody.innerHTML = `<tr><td colspan="6" class="text-red-500">Error loading data: ${error.message}</td></tr>`;
    }
};

// Call the function on page load
updatePendingOrders();













document.addEventListener('DOMContentLoaded', function () {
    // Ensure we're using the global chartInstances
    if (!window.chartInstances) {
        window.chartInstances = {};
    }

    // Register the funnel chart type (chartjs-chart-funnel registers automatically)
    if (typeof Chart.FunnelChart !== 'undefined') {
        console.log('Funnel chart type available.');
    } else {
        console.warn('Funnel chart type not loaded. Falling back to bar chart for funnel.');
    }

    // Get DOM elements for Sales Trend Chart
    const chartContainer = document.getElementById('salesTrendChart');
    const periodTypeSelect = document.getElementById('periodType');
    const startDateInput = document.getElementById('startDate');
    const endDateInput = document.getElementById('endDate');
    const forecastStartInput = document.getElementById('forecastStart');
    const applyFiltersBtn = document.getElementById('applyFilters');
    const resetFiltersBtn = document.getElementById('resetFilters');
    const loadingElement = document.getElementById('chartLoading');
    const salesTrendErrorElement = document.getElementById('sales-trend-error');

    // Get DOM elements for Sales by Region Chart
    const regionChartContainer = document.getElementById('salesRegionChart');
    const regionLoadingElement = document.getElementById('regionChartLoading');
    const regionSelect = document.getElementById('regionSelect');

    // Get DOM elements for Sales Funnel Chart
    const funnelChartContainer = document.getElementById('salesFunnelChart');
    const funnelLoadingElement = document.getElementById('funnelLoading');

    // Get DOM elements for Sales by Customer Chart
    const customerChartContainer = document.getElementById('salesCustomerChart');
    const customerLoadingElement = document.getElementById('customerLoading');

    // Get DOM elements for Sales by Salesperson Chart
    const salespersonChartContainer = document.getElementById('salesSalespersonChart');
    const salespersonLoadingElement = document.getElementById('salespersonLoading');

    // Get DOM elements for Sales Target vs Achievement Chart
    const targetAchievementChartContainer = document.getElementById('salesTargetAchievementChart');
    const targetAchievementLoadingElement = document.getElementById('targetAchievementLoading');

    // Get DOM elements for Sales by Category Chart
    const categoryChartContainer = document.getElementById('salesByCategoryChart');
    const categoryLoadingElement = document.getElementById('categoryLoading');

    // Get DOM elements for Sales Growth Rate Chart
    const growthRateChartContainer = document.getElementById('salesGrowthRateChart');
    const growthRateLoadingElement = document.getElementById('growthRateLoading');

    // Get DOM elements for Repeat vs New Customer Sales Chart
    const repeatVsNewChartContainer = document.getElementById('repeatVsNewSalesChart');
    const repeatVsNewLoadingElement = document.getElementById('repeatVsNewLoading');


    // Chart instance variables
    let salesChart = null;
    let regionChart = null;
    let funnelChart = null;
    let customerChart = null;
    let salespersonChart = null;
    let targetAchievementChart = null;
    let categoryChart = null;
    let growthRateChart = null;
    let repeatVsNewChart = null;

    // Object to store chart-specific date filters
    const chartFilters = {
        salesTrendChart: { selectedDate: null },
        salesRegionChart: { selectedDate: null },
        salesFunnelChart: { selectedDate: null },
        salesCustomerChart: { selectedDate: null },
        salesSalespersonChart: { selectedDate: null },
        salesTargetAchievementChart: { selectedDate: null },
        salesByCategoryChart: { selectedDate: null },
        salesGrowthRateChart: { selectedDate: null },
        repeatVsNewSalesChart: { selectedDate: null }
    };

    // Set default date range for global filters (last 2 years to current date)
    const today = new Date();
    const twoYearsAgo = new Date();
    twoYearsAgo.setFullYear(today.getFullYear() - 2);

    startDateInput.value = formatDateForInput(twoYearsAgo);
    endDateInput.value = formatDateForInput(today);

    // Populate date dropdowns with the last 24 months
    populateDateDropdowns();

    // Initialize charts and populate regions
    populateRegions();
    loadRegionChartData();
    loadFunnelChartData();
    loadCustomerChartData();
    loadSalespersonChartData();
    loadTargetAchievementChartData();
    loadCategoryChartData();
    loadGrowthRateChartData();
    loadRepeatVsNewChartData();

    // Event listeners for global filters
    applyFiltersBtn.addEventListener('click', () => {
        loadChartData();
        loadCategoryChartData();
        loadGrowthRateChartData();
        loadRepeatVsNewChartData();
    });
    resetFiltersBtn.addEventListener('click', resetFilters);
    regionSelect.addEventListener('change', loadRegionChartData);

    // Event listeners for "More Options" buttons
    document.querySelectorAll('.more-options-btn').forEach(button => {
        button.addEventListener('click', (e) => {
            const chartId = button.getAttribute('data-chart-id');
            const dropdown = document.querySelector(`.options-dropdown[data-chart-id="${chartId}"]`);
            // Toggle dropdown visibility
            dropdown.classList.toggle('show');
            // Close other dropdowns
            document.querySelectorAll(`.options-dropdown:not([data-chart-id="${chartId}"])`).forEach(d => d.classList.remove('show'));
        });
    });

    // Event listeners for "Apply" buttons in chart-specific filters
    document.querySelectorAll('.apply-chart-filter').forEach(button => {
        button.addEventListener('click', (e) => {
            const chartId = button.getAttribute('data-chart-id');
            const dropdown = document.querySelector(`.options-dropdown[data-chart-id="${chartId}"]`);
            const dateSelect = dropdown.querySelector('.chart-date-select');

            // Update chartFilters with the selected date
            chartFilters[chartId].selectedDate = dateSelect.value || null;

            // Close the dropdown
            dropdown.classList.remove('show');

            // Reload the chart with the new filter
            switch (chartId) {
                case 'salesTrendChart':
                    loadChartData();
                    break;
                case 'salesRegionChart':
                    loadRegionChartData();
                    break;
                case 'salesFunnelChart':
                    loadFunnelChartData();
                    break;
                case 'salesCustomerChart':
                    loadCustomerChartData();
                    break;
                case 'salesSalespersonChart':
                    loadSalespersonChartData();
                    break;
                case 'salesTargetAchievementChart':
                    loadTargetAchievementChartData();
                    break;
                case 'salesByCategoryChart':
                    loadCategoryChartData();
                    break;
                case 'salesGrowthRateChart':
                    loadGrowthRateChartData();
                    break;
                case 'repeatVsNewSalesChart':
                    loadRepeatVsNewChartData();
                    break;
            }
        });
    });

    // Close dropdown when clicking outside
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.more-options-btn') && !e.target.closest('.options-dropdown')) {
            document.querySelectorAll('.options-dropdown').forEach(dropdown => {
                dropdown.classList.remove('show');
            });
        }
    });

    // Functions
    function populateDateDropdowns() {
    const startDate = new Date('2023-01-01'); // Adjust as needed
    const endDate = new Date('2025-05-01'); // Cap at May 2025
    const months = [];
    const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

    let current = new Date(startDate);
    while (current <= endDate) {
        const year = current.getFullYear();
        const month = current.getMonth();
        const formatted = `${monthNames[month]} ${year}`;
        const value = `${year}-${String(month + 1).padStart(2, '0')}-01`;
        months.push({ formatted, value });
        current.setMonth(current.getMonth() + 1);
    }
    months.reverse(); // Most recent first

    document.querySelectorAll('.chart-date-select').forEach(select => {
        select.innerHTML = '<option value="">Select Date</option>';
        months.forEach(month => {
            const option = document.createElement('option');
            option.value = month.value;
            option.textContent = month.formatted;
            select.appendChild(option);
        });
        // Set default to May 2025
        select.value = '2025-05-01';
        const chartId = select.closest('.options-dropdown').getAttribute('data-chart-id');
        chartFilters[chartId].selectedDate = '2025-05-01';
    });
}

    

    function resetFilters() {
        periodTypeSelect.value = 'MS';
        const today = new Date();
        const twoYearsAgo = new Date();
        twoYearsAgo.setFullYear(today.getFullYear() - 2);
        startDateInput.value = formatDateForInput(twoYearsAgo);
        endDateInput.value = formatDateForInput(today);
        forecastStartInput.value = '2026-02-01';

        // Reset chart-specific filters
        Object.keys(chartFilters).forEach(chartId => {
    chartFilters[chartId].selectedDate = null; // Reset to no specific date
    const dropdown = document.querySelector(`.options-dropdown[data-chart-id="${chartId}"]`);
    if (dropdown) {
        const select = dropdown.querySelector('.chart-date-select');
        if (select) select.value = '';
    }
});

        if (salesTrendErrorElement) {
            salesTrendErrorElement.textContent = '';
            salesTrendErrorElement.style.display = 'none';
        }

        if (salesChart) {
            salesChart.destroy();
            salesChart = null;
            delete window.chartInstances['salesTrendChart'];
            document.querySelector(`button[data-chart-id="salesTrendChart"]`).classList.add('disabled');
        }
        if (categoryChart) {
            categoryChart.destroy();
            categoryChart = null;
            delete window.chartInstances['salesByCategoryChart'];
            document.querySelector(`button[data-chart-id="salesByCategoryChart"]`).classList.add('disabled');
        }
        if (growthRateChart) {
            growthRateChart.destroy();
            growthRateChart = null;
            delete window.chartInstances['salesGrowthRateChart'];
            document.querySelector(`button[data-chart-id="salesGrowthRateChart"]`).classList.add('disabled');
        }
        if (repeatVsNewChart) {
            repeatVsNewChart.destroy();
            repeatVsNewChart = null;
            delete window.chartInstances['repeatVsNewSalesChart'];
            document.querySelector(`button[data-chart-id="repeatVsNewSalesChart"]`).classList.add('disabled');
        }

        // Reload all charts
        loadChartData();
        loadRegionChartData();
        loadFunnelChartData();
        loadCustomerChartData();
        loadSalespersonChartData();
        loadTargetAchievementChartData();
        loadCategoryChartData();
        loadGrowthRateChartData();
        loadRepeatVsNewChartData();
    }

    function formatDateForInput(date) {
        return date.toISOString().split('T')[0];
    }

    function formatChartLabels(labels, periodType) {
        // Ensure labels is an array; return empty array if not
        if (!Array.isArray(labels)) {
            console.error('formatChartLabels: labels is not an array:', labels);
            return [];
        }

        // Ensure periodType is a string
        if (typeof periodType !== 'string') {
            console.error('formatChartLabels: periodType is not a string:', periodType);
            return labels;
        }

        return labels.map(label => {
            // Ensure label is a string
            if (typeof label !== 'string') {
                console.error('formatChartLabels: label is not a string:', label);
                return String(label);
            }

            switch (periodType) {
                case 'MS':
                    const [year, month] = label.split('-');
                    const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
                    // Validate year and month before accessing monthNames
                    if (!year || !month || isNaN(parseInt(month))) {
                        console.error('formatChartLabels: Invalid date format for MS period:', label);
                        return label;
                    }
                    return `${monthNames[parseInt(month) - 1]} ${year}`;
                case 'YS':
                    return label;
                case 'QS':
                    const [yearQ, quarter] = label.split('-Q');
                    if (!yearQ || !quarter) {
                        console.error('formatChartLabels: Invalid date format for QS period:', label);
                        return label;
                    }
                    return `${yearQ}-Q${quarter}`;
                default:
                    return label;
            }
        });
    }

    function getPeriodLabel(periodType) {
        switch (periodType) {
            case 'MS':
                return 'Month';
            case 'YS':
                return 'Year';
            case 'QS':
                return 'Quarter';
            default:
                return 'Period';
        }
    }

    function loadChartData() {
        console.log('Period Type:', periodTypeSelect.value);
        console.log('Start Date:', startDateInput.value);
        console.log('End Date:', endDateInput.value);
        console.log('Forecast Start:', forecastStartInput.value);

        if (salesTrendErrorElement) {
            salesTrendErrorElement.textContent = '';
            salesTrendErrorElement.style.display = 'none';
        }

        const startDate = startDateInput.value;
        const endDate = endDateInput.value;
        const forecastStart = forecastStartInput.value || '2026-02-01';

        const startDateObj = new Date(startDate);
        const endDateObj = new Date(endDate);
        const forecastStartObj = new Date(forecastStart);

        if (startDate && endDate && startDateObj > endDateObj) {
            if (salesTrendErrorElement) {
                salesTrendErrorElement.textContent = 'Start Date cannot be after End Date.';
                salesTrendErrorElement.style.display = 'block';
                salesTrendErrorElement.style.color = 'red';
            }
            return;
        }

        if (endDate && forecastStart && forecastStartObj <= endDateObj) {
            if (salesTrendErrorElement) {
                salesTrendErrorElement.textContent = 'Forecast Start must be after End Date.';
                salesTrendErrorElement.style.display = 'block';
                salesTrendErrorElement.style.color = 'red';
            }
            return;
        }

        loadingElement.style.display = 'flex';

        const periodType = periodTypeSelect.value;
        let apiUrl = `/api/sales-trend?period_type=${periodType}&start_date=${startDate}&end_date=${endDate}&forecast_start=${forecastStart}`;
        const chartSelectedDate = chartFilters['salesTrendChart'].selectedDate;
        if (chartSelectedDate) {
            apiUrl += `&selected_date=${chartSelectedDate}`;
        }

        fetch(apiUrl)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                if (data.error) {
                    if (salesTrendErrorElement) {
                        salesTrendErrorElement.textContent = data.error;
                        salesTrendErrorElement.style.display = 'block';
                        salesTrendErrorElement.style.color = 'red';
                    }
                    loadingElement.style.display = 'none';
                    document.querySelector(`button[data-chart-id="salesTrendChart"]`).classList.add('disabled');
                    return;
                }

                updateChart(data);
                loadingElement.style.display = 'none';
                if (window.chartInstances['salesTrendChart']) {
                    document.querySelector(`button[data-chart-id="salesTrendChart"]`).classList.remove('disabled');
                }
            })
            .catch(error => {
                console.error('Error fetching data:', error);
                if (salesTrendErrorElement) {
                    salesTrendErrorElement.textContent = 'Failed to load Sales Trend data. Please try again.';
                    salesTrendErrorElement.style.display = 'block';
                    salesTrendErrorElement.style.color = 'red';
                }
                loadingElement.style.display = 'none';
                document.querySelector(`button[data-chart-id="salesTrendChart"]`).classList.add('disabled');
            });
    }

    function updateChart(data) {
        if (window.chartInstances['salesTrendChart']) {
            window.chartInstances['salesTrendChart'].destroy();
            delete window.chartInstances['salesTrendChart'];
        }
        if (salesChart) {
            salesChart.destroy();
            salesChart = null;
        }

        const allPeriods = [...new Set([
            ...(data.actual.periods || []),
            ...(data.predicted.periods || []),
            ...(data.forecast.periods || [])
        ])].sort();

        const actualSales = allPeriods.map(period => {
            const idx = data.actual.periods.indexOf(period);
            return idx !== -1 ? data.actual.sales[idx] : null;
        });

        const predictedSales = allPeriods.map(period => {
            const idx = data.predicted.periods.indexOf(period);
            return idx !== -1 ? data.predicted.sales[idx] : null;
        });

        const forecastSales = allPeriods.map(period => {
            const idx = data.forecast.periods.indexOf(period);
            return idx !== -1 ? data.forecast.sales[idx] : null;
        });

        const ctx = chartContainer.getContext('2d');
        salesChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: formatChartLabels(allPeriods, data.period_type),
                datasets: [
                    {
                        label: 'Actual Sales ($)',
                        data: actualSales,
                        borderColor: 'rgba(75, 192, 192, 1)',
                        backgroundColor: 'rgba(75, 192, 192, 0.2)',
                        fill: false,
                        pointRadius: 5,
                        pointBackgroundColor: 'rgba(75, 192, 192, 1)',
                        spanGaps: true
                    },
                    {
                        label: 'Predicted Sales ($)',
                        data: predictedSales,
                        borderColor: 'rgba(255, 159, 64, 1)',
                        backgroundColor: 'rgba(255, 159, 64, 0.2)',
                        borderDash: [5, 5],
                        fill: false,
                        pointRadius: 5,
                        pointBackgroundColor: 'rgba(255, 159, 64, 1)',
                        spanGaps: true
                    },
                    {
                        label: 'Forecasted Sales ($)',
                        data: forecastSales,
                        borderColor: 'rgba(153, 102, 255, 1)',
                        backgroundColor: 'rgba(153, 102, 255, 0.2)',
                        borderDash: [5, 5],
                        fill: false,
                        pointRadius: 5,
                        pointBackgroundColor: 'rgba(153, 102, 255, 1)',
                        spanGaps: true
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        title: { display: true, text: getPeriodLabel(data.period_type), font: { size: 14 } },
                        grid: { display: false }
                    },
                    y: {
                        title: { display: true, text: 'Sales Amount ($)', font: { size: 14 } },
                        beginAtZero: true
                    }
                },
                plugins: {
                    legend: { display: true, position: 'top' },
                    tooltip: {
                        callbacks: {
                            label: function (tooltipItem) {
                                const datasetLabel = tooltipItem.dataset.label || '';
                                const value = tooltipItem.raw || 0;
                                return `${datasetLabel}: $${value.toFixed(2)}`;
                            }
                        }
                    }
                }
            }
        });
        window.chartInstances['salesTrendChart'] = salesChart;
        console.log('Sales Trend Chart created and stored in window.chartInstances');
    }

    function populateRegions() {
        fetch('/api/regions')
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                data.regions.forEach(region => {
                    const option = document.createElement('option');
                    option.value = region;
                    option.textContent = region;
                    regionSelect.appendChild(option);
                });
            })
            .catch(error => {
                console.error('Error fetching regions:', error);
                alert('Failed to load regions. Please try again.');
            });
    }

    function loadRegionChartData() {
    const chartId = 'salesRegionChart';
    const region = document.querySelector('#region-select')?.value || 'all';
    const selectedDate = chartFilters[chartId]?.selectedDate || '2025-05-01';
    const endpoint = `/api/sales-by-region${region !== 'all' ? `?region_label=${encodeURIComponent(region)}` : ''}${selectedDate ? `${region !== 'all' ? '&' : '?'}selected_date=${selectedDate}` : ''}`;

    console.log(`Fetching region data from: ${endpoint}`);

    fetch(endpoint)
        .then(response => {
            if (!response.ok) {
                return response.json().then(data => {
                    console.error(`HTTP error! Status: ${response.status}, Error: ${data.error || 'Unknown error'}`);
                    throw new Error(data.error || 'Failed to fetch sales by region data');
                });
            }
            return response.json();
        })
        .then(data => {
            console.log('Sales by Region data:', data);
            updateRegionChart(data);
        })
        .catch(error => {
            console.error('Error fetching region data:', error);
            alert(`Failed to load Sales by Region data: ${error.message}`);
        });
}

    function updateRegionChart(data) {
    const chartId = 'salesRegionChart';
    const config = {
        type: 'bar',
        data: {
            labels: data.regions,
            datasets: [{
                label: 'Sales ($)',
                data: data.sales,
                backgroundColor: 'rgba(153, 102, 255, 0.6)',
                borderColor: 'rgba(153, 102, 255, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    title: { display: true, text: 'Region' },
                    ticks: { autoSkip: true, maxRotation: 45, minRotation: 45 },
                    grid: { display: false }
                },
                y: {
                    title: { display: true, text: 'Sales Amount ($)' },
                    beginAtZero: true
                }
            },
            plugins: {
                legend: { display: true, position: 'top' },
                tooltip: {
                    callbacks: {
                        label: (tooltipItem) => `${tooltipItem.dataset.label}: $${tooltipItem.raw.toFixed(2)}`
                    }
                }
            }
        }
    };

    // Destroy existing chart if it exists
    if (window.chartInstances[chartId]) {
        window.chartInstances[chartId].destroy();
        console.log(`Destroyed existing chart for ${chartId}`);
    }

    const canvas = document.getElementById(chartId);
    if (!canvas) {
        console.error(`Canvas element with ID ${chartId} not found`);
        return;
    }

    window.chartInstances[chartId] = new Chart(canvas, config);
}
        
        // Add an event listener for fullscreen toggle to properly resize the chart
        document.addEventListener('fullscreenchange', function() {
            if (window.chartInstances['salesRegionChart']) {
                window.chartInstances['salesRegionChart'].resize();
            }
        });

    function loadFunnelChartData() {
        funnelLoadingElement.style.display = 'flex';

        let apiUrl = '/api/sales-funnel';
        const params = [];
        const chartSelectedDate = chartFilters['salesFunnelChart'].selectedDate;
        if (chartSelectedDate) {
            params.push(`selected_date=${chartSelectedDate}`);
        }
        if (params.length > 0) {
            apiUrl += `?${params.join('&')}`;
        }

        fetch(apiUrl)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                updateFunnelChart(data);
                funnelLoadingElement.style.display = 'none';
                if (window.chartInstances['salesFunnelChart']) {
                    document.querySelector(`button[data-chart-id="salesFunnelChart"]`).classList.remove('disabled');
                }
            })
            .catch(error => {
                console.error('Error fetching funnel data:', error);
                alert('Failed to load Sales Funnel data. Please try again.');
                funnelLoadingElement.style.display = 'none';
                document.querySelector(`button[data-chart-id="salesFunnelChart"]`).classList.add('disabled');
            });
    }

    function updateFunnelChart(data) {
        if (window.chartInstances['salesFunnelChart']) {
            window.chartInstances['salesFunnelChart'].destroy();
            delete window.chartInstances['salesFunnelChart'];
        }
        if (funnelChart) {
            funnelChart.destroy();
        }

        const ctx = funnelChartContainer.getContext('2d');
        if (typeof Chart.FunnelChart === 'undefined') {
            console.warn('Funnel chart type not registered, using bar chart instead.');
            funnelChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: ['Leads', 'Quotes', 'Orders', 'Invoices'],
                    datasets: [{
                        label: 'Count',
                        data: [data.leads, data.quotes, data.orders, data.invoices],
                        backgroundColor: [
                            'rgba(255, 99, 132, 0.6)',
                            'rgba(54, 162, 235, 0.6)',
                            'rgba(75, 192, 192, 0.6)',
                            'rgba(255, 206, 86, 0.6)'
                        ],
                        borderColor: [
                            'rgba(255, 99, 132, 1)',
                            'rgba(54, 162, 235, 1)',
                            'rgba(75, 192, 192, 1)',
                            'rgba(255, 206, 86, 1)'
                        ],
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    indexAxis: 'y',
                    scales: {
                        x: { title: { display: true, text: 'Count', font: { size: 14 } }, beginAtZero: true, reverse: true },
                        y: { title: { display: true, text: 'Stage', font: { size: 14 } }, grid: { display: false } }
                    },
                    plugins: {
                        legend: { display: true, position: 'top' },
                        tooltip: {
                            callbacks: {
                                label: function (tooltipItem) {
                                    const datasetLabel = tooltipItem.dataset.label || '';
                                    const value = tooltipItem.raw || 0;
                                    return `${datasetLabel}: ${value}`;
                                }
                            }
                        }
                    }
                }
            });
        } else {
            funnelChart = new Chart(ctx, {
                type: 'funnel',
                data: {
                    labels: ['Leads', 'Quotes', 'Orders', 'Invoices'],
                    datasets: [{
                        label: 'Count',
                        data: [data.leads, data.quotes, data.orders, data.invoices],
                        backgroundColor: [
                            'rgba(255, 99, 132, 0.6)',
                            'rgba(54, 162, 235, 0.6)',
                            'rgba(75, 192, 192, 0.6)',
                            'rgba(255, 206, 86, 0.6)'
                        ],
                        borderColor: [
                            'rgba(255, 99, 132, 1)',
                            'rgba(54, 162, 235, 1)',
                            'rgba(75, 192, 192, 1)',
                            'rgba(255, 206, 86, 1)'
                        ],
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: true, position: 'top' },
                        tooltip: {
                            callbacks: {
                                label: function (tooltipItem) {
                                    const datasetLabel = tooltipItem.dataset.label || '';
                                    const value = tooltipItem.raw || 0;
                                    return `${datasetLabel}: ${value}`;
                                }
                            }
                        }
                    },
                    scales: { x: { display: false }, y: { display: false } }
                }
            });
        }
        window.chartInstances['salesFunnelChart'] = funnelChart;
        console.log('Sales Funnel Chart created and stored in window.chartInstances');
    }

    function loadCustomerChartData() {
        customerLoadingElement.style.display = 'flex';

        let apiUrl = '/api/sales-by-customer';
        const params = [];
        const chartSelectedDate = chartFilters['salesCustomerChart'].selectedDate;
        if (chartSelectedDate) {
            params.push(`selected_date=${chartSelectedDate}`);
        }
        if (params.length > 0) {
            apiUrl += `?${params.join('&')}`;
        }

        fetch(apiUrl)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                updateCustomerChart(data);
                customerLoadingElement.style.display = 'none';
                if (window.chartInstances['salesCustomerChart']) {
                    document.querySelector(`button[data-chart-id="salesCustomerChart"]`).classList.remove('disabled');
                }
            })
            .catch(error => {
                console.error('Error fetching customer data:', error);
                alert('Failed to load Sales by Customer data. Please try again.');
                customerLoadingElement.style.display = 'none';
                document.querySelector(`button[data-chart-id="salesCustomerChart"]`).classList.add('disabled');
            });
    }

    function updateCustomerChart(data) {
        if (window.chartInstances['salesCustomerChart']) {
            window.chartInstances['salesCustomerChart'].destroy();
            delete window.chartInstances['salesCustomerChart'];
        }
        if (customerChart) {
            customerChart.destroy();
        }

        const ctx = customerChartContainer.getContext('2d');
        customerChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.customers.slice(0, 10),
                datasets: [
                    {
                        label: 'Revenue ($)',
                        data: data.revenues.slice(0, 10),
                        backgroundColor: 'rgba(75, 192, 192, 0.6)',
                        borderColor: 'rgba(75, 192, 192, 1)',
                        borderWidth: 1,
                        yAxisID: 'y'
                    },
                    {
                        label: 'Cumulative %',
                        data: data.cumulative_percentages.slice(0, 10),
                        type: 'line',
                        borderColor: 'rgba(255, 99, 132, 1)',
                        backgroundColor: 'rgba(255, 99, 132, 0.2)',
                        fill: false,
                        yAxisID: 'y1',
                        pointRadius: 5
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: { title: { display: true, text: 'Customer', font: { size: 14 } }, grid: { display: false } },
                    y: { title: { display: true, text: 'Revenue ($)', font: { size: 14 } }, beginAtZero: true, position: 'left' },
                    y1: { title: { display: true, text: 'Cumulative %', font: { size: 14 } }, beginAtZero: true, position: 'right', max: 100, ticks: { callback: function(value) { return value + '%'; } } }
                },
                plugins: {
                    legend: { display: true, position: 'top' },
                    tooltip: {
                        callbacks: {
                            label: function (tooltipItem) {
                                const datasetLabel = tooltipItem.dataset.label || '';
                                const value = tooltipItem.raw || 0;
                                return datasetLabel === 'Cumulative %' ? `${datasetLabel}: ${value.toFixed(2)}%` : `${datasetLabel}: $${value.toFixed(2)}`;
                            }
                        }
                    }
                }
            }
        });
        window.chartInstances['salesCustomerChart'] = customerChart;
        console.log('Sales by Customer Chart created and stored in window.chartInstances');
    }

    function loadSalespersonChartData() {
        salespersonLoadingElement.style.display = 'flex';

        let apiUrl = '/api/sales-by-salesperson';
        const params = [];
        const chartSelectedDate = chartFilters['salesSalespersonChart'].selectedDate;
        if (chartSelectedDate) {
            params.push(`selected_date=${chartSelectedDate}`);
        }
        if (params.length > 0) {
            apiUrl += `?${params.join('&')}`;
        }

        fetch(apiUrl)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                updateSalespersonChart(data);
                salespersonLoadingElement.style.display = 'none';
                if (window.chartInstances['salesSalespersonChart']) {
                    document.querySelector(`button[data-chart-id="salesSalespersonChart"]`).classList.remove('disabled');
                }
            })
            .catch(error => {
                console.error('Error fetching salesperson data:', error);
                alert('Failed to load Sales by Salesperson data. Please try again.');
                salespersonLoadingElement.style.display = 'none';
                document.querySelector(`button[data-chart-id="salesSalespersonChart"]`).classList.add('disabled');
            });
    }

    function updateSalespersonChart(data) {
        if (window.chartInstances['salesSalespersonChart']) {
            window.chartInstances['salesSalespersonChart'].destroy();
            delete window.chartInstances['salesSalespersonChart'];
        }
        if (salespersonChart) {
            salespersonChart.destroy();
        }
    
        // Store the full dataset for reuse
        window.salespersonChartData = data;
        
        const ctx = salespersonChartContainer.getContext('2d');
        salespersonChart = new Chart(ctx, {
            type: 'bar',
            data: {
                // Always include all data points in the chart configuration
                // The responsive nature of the chart will handle showing fewer items in normal view
                labels: data.salespersons,
                datasets: [{
                    label: 'Sales ($)',
                    data: data.sales,
                    backgroundColor: 'rgba(54, 162, 235, 0.6)',
                    borderColor: 'rgba(54, 162, 235, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: { 
                        title: { display: true, text: 'Salesperson', font: { size: 14 } }, 
                        ticks: { 
                            autoSkip: true,  // Enable auto skipping
                            maxRotation: 45, 
                            minRotation: 45
                        }, 
                        grid: { display: false } 
                    },
                    y: { 
                        title: { display: true, text: 'Sales Amount ($)', font: { size: 14 } }, 
                        beginAtZero: true 
                    }
                },
                plugins: {
                    legend: { display: true, position: 'top' },
                    tooltip: {
                        callbacks: {
                            label: function (tooltipItem) {
                                const datasetLabel = tooltipItem.dataset.label || '';
                                const value = tooltipItem.raw || 0;
                                return `${datasetLabel}: $${value.toFixed(2)}`;
                            }
                        }
                    }
                }
            }
        });
        
        window.chartInstances['salesSalespersonChart'] = salespersonChart;
        console.log('Sales by Salesperson Chart created and stored in window.chartInstances');
        
        // Add an event listener for fullscreen toggle to properly resize the chart
        document.addEventListener('fullscreenchange', function() {
            if (window.chartInstances['salesSalespersonChart']) {
                window.chartInstances['salesSalespersonChart'].resize();
            }
        });
    }

    function loadTargetAchievementChartData() {
        targetAchievementLoadingElement.style.display = 'flex';

        let apiUrl = '/api/sales-target-vs-achievement';
        const params = [];
        const chartSelectedDate = chartFilters['salesTargetAchievementChart'].selectedDate;
        if (chartSelectedDate) {
            params.push(`selected_date=${chartSelectedDate}`);
        }
        if (params.length > 0) {
            apiUrl += `?${params.join('&')}`;
        }

        fetch(apiUrl)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                updateTargetAchievementChart(data);
                targetAchievementLoadingElement.style.display = 'none';
                if (window.chartInstances['salesTargetAchievementChart']) {
                    document.querySelector(`button[data-chart-id="salesTargetAchievementChart"]`).classList.remove('disabled');
                }
            })
            .catch(error => {
                console.error('Error fetching target vs achievement data:', error);
                alert('Failed to load Sales Target vs Achievement data. Please try again.');
                targetAchievementLoadingElement.style.display = 'none';
                document.querySelector(`button[data-chart-id="salesTargetAchievementChart"]`).classList.add('disabled');
            });
    }

    function updateTargetAchievementChart(data) {
        if (window.chartInstances['salesTargetAchievementChart']) {
            window.chartInstances['salesTargetAchievementChart'].destroy();
            delete window.chartInstances['salesTargetAchievementChart'];
        }
        if (targetAchievementChart) {
            targetAchievementChart.destroy();
        }
    
        // Store the full dataset for reuse
        window.targetAchievementChartData = data;
        
        const ctx = targetAchievementChartContainer.getContext('2d');
        targetAchievementChart = new Chart(ctx, {
            type: 'bar',
            data: {
                // Include all data points in the chart configuration
                // The responsive nature of the chart will handle showing fewer items in normal view
                labels: data.labels,
                datasets: [
                    {
                        label: 'Target (₹)',
                        data: data.targets,
                        backgroundColor: 'rgba(255, 99, 132, 0.6)',
                        borderColor: 'rgba(255, 99, 132, 1)',
                        borderWidth: 1
                    },
                    {
                        label: 'Achieved (₹)',
                        data: data.achieved,
                        backgroundColor: 'rgba(75, 192, 192, 0.6)',
                        borderColor: 'rgba(75, 192, 192, 1)',
                        borderWidth: 1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: { 
                        title: { display: true, text: 'Salesperson - Period', font: { size: 14 } }, 
                        ticks: { 
                            autoSkip: true,  // Enable auto skipping for responsive behavior
                            maxRotation: 45, 
                            minRotation: 45 
                        }, 
                        grid: { display: false } 
                    },
                    y: { 
                        title: { display: true, text: 'Amount (₹)', font: { size: 14 } }, 
                        beginAtZero: false, 
                        min: 1000000, 
                        ticks: { 
                            callback: function(value) { 
                                return '₹' + (value / 100000).toFixed(0) + 'L'; 
                            } 
                        } 
                    }
                },
                plugins: {
                    legend: { display: true, position: 'top' },
                    tooltip: {
                        callbacks: {
                            label: function (tooltipItem) {
                                const datasetLabel = tooltipItem.dataset.label || '';
                                const value = tooltipItem.raw || 0;
                                const index = tooltipItem.dataIndex;
                                const percentage = data.percentages[index];
                                return `${datasetLabel}: ₹${(value / 100000).toFixed(2)}L` + (datasetLabel === 'Achieved' ? ` (${percentage.toFixed(2)}% of Target)` : '');
                            }
                        }
                    }
                }
            }
        });
        
        window.chartInstances['salesTargetAchievementChart'] = targetAchievementChart;
        console.log('Sales Target vs Achievement Chart created and stored in window.chartInstances');
        
        // Add an event listener for fullscreen toggle to properly resize the chart
        document.addEventListener('fullscreenchange', function() {
            if (window.chartInstances['salesTargetAchievementChart']) {
                window.chartInstances['salesTargetAchievementChart'].resize();
            }
        });
    }

    function loadCategoryChartData() {
    categoryLoadingElement.style.display = 'flex';
    const errorElement = document.getElementById('category-error'); // Add in HTML

    const periodType = periodTypeSelect.value;
    const chartSelectedDate = chartFilters['salesByCategoryChart'].selectedDate;

    let apiUrl = `/api/sales-by-category?period_type=${periodType}`;
    if (chartSelectedDate) {
        const selected = new Date(chartSelectedDate);
        const currentDate = new Date('2025-06-04');
        if (selected > currentDate) {
            if (errorElement) {
                errorElement.textContent = 'Selected date is in the future. Please choose an earlier date.';
                errorElement.style.display = 'block';
                errorElement.style.color = 'red';
            }
            categoryLoadingElement.style.display = 'none';
            document.querySelector(`button[data-chart-id="salesByCategoryChart"]`).classList.add('disabled');
            return;
        }
        apiUrl += `&selected_date=${chartSelectedDate}`;
    } else {
        const startDate = startDateInput.value || '2024-01-01';
        let endDate = endDateInput.value || '2025-06-04';
        const currentDate = new Date('2025-06-04');
        if (new Date(endDate) > currentDate) {
            endDate = '2025-06-04';
        }
        if (startDate) apiUrl += `&start_date=${startDate}`;
        if (endDate) apiUrl += `&end_date=${endDate}`;
    }

    console.log(`Fetching category data from: ${apiUrl}`);

    fetch(apiUrl)
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => {
                    throw new Error(`HTTP ${response.status}: ${err.error || 'Bad request'}`);
                });
            }
            return response.json();
        })
        .then(data => {
            if (data.error) {
                throw new Error(data.error);
            }
            if (data.categories.length === 0 || data.sales.length === 0) {
                if (errorElement) {
                    errorElement.textContent = 'No sales category data available for the selected period';
                    errorElement.style.display = 'block';
                    errorElement.style.color = 'red';
                }
                categoryLoadingElement.style.display = 'none';
                document.querySelector(`button[data-chart-id="salesByCategoryChart"]`).classList.add('disabled');
                return;
            }
            updateCategoryChart(data);
            categoryLoadingElement.style.display = 'none';
            if (window.chartInstances['salesByCategoryChart']) {
                document.querySelector(`button[data-chart-id="salesByCategoryChart"]`).classList.remove('disabled');
            }
            if (errorElement) {
                errorElement.textContent = '';
                errorElement.style.display = 'none';
            }
        })
        .catch(error => {
            console.error('Error fetching category data:', error);
            if (errorElement) {
                errorElement.textContent = `Failed to load Sales by Category data: ${error.message}`;
                errorElement.style.display = 'block';
                errorElement.style.color = 'red';
            } else {
                alert('Failed to load Sales by Category data: ' + error.message);
            }
            categoryLoadingElement.style.display = 'none';
            document.querySelector(`button[data-chart-id="salesByCategoryChart"]`).classList.add('disabled');
        });
}

    function updateCategoryChart(data) {
        if (window.chartInstances['salesByCategoryChart']) {
            window.chartInstances['salesByCategoryChart'].destroy();
            delete window.chartInstances['salesByCategoryChart'];
        }
        if (categoryChart) {
            categoryChart.destroy();
        }

        const ctx = categoryChartContainer.getContext('2d');
        categoryChart = new Chart(ctx, {
            type: 'pie',
            data: {
                labels: data.categories,
                datasets: [{
                    label: 'Sales Distribution (%)',
                    data: data.sales,
                    backgroundColor: [
                        'rgba(255, 99, 132, 0.6)',
                        'rgba(54, 162, 235, 0.6)',
                        'rgba(75, 192, 192, 0.6)',
                        'rgba(255, 206, 86, 0.6)',
                        'rgba(153, 102, 255, 0.6)'
                    ],
                    borderColor: [
                        'rgba(255, 99, 132, 1)',
                        'rgba(54, 162, 235, 1)',
                        'rgba(75, 192, 192, 1)',
                        'rgba(255, 206, 86, 1)',
                        'rgba(153, 102, 255, 1)'
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: true, position: 'top' },
                    tooltip: {
                        callbacks: {
                            label: function (tooltipItem) {
                                const label = tooltipItem.label || '';
                                const value = tooltipItem.raw || 0;
                                return `${label}: ${value}%`;
                            }
                        }
                    }
                }
            }
        });
        window.chartInstances['salesByCategoryChart'] = categoryChart;
        console.log('Sales by Category Chart created and stored in window.chartInstances');
    }
    function populateDateDropdowns() {
    const startDate = new Date(startDateInput.value || '2024-01-01');
    const endDate = new Date(endDateInput.value || '2025-12-31');
    const months = [];
    const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

    // Generate months between startDate and endDate
    let current = new Date(startDate);
    while (current <= endDate) {
        const year = current.getFullYear();
        const month = current.getMonth();
        const formatted = `${monthNames[month]} ${year}`;
        const value = `${year}-${String(month + 1).padStart(2, '0')}-01`;
        months.push({ formatted, value });
        current.setMonth(current.getMonth() + 1);
    }
    months.reverse(); // Most recent first

    // Populate each dropdown
    document.querySelectorAll('.chart-date-select').forEach(select => {
        select.innerHTML = '<option value="">Select Date</option>'; // Reset options
        months.forEach(month => {
            const option = document.createElement('option');
            option.value = month.value;
            option.textContent = month.formatted;
            select.appendChild(option);
        });
        // Set default to the most recent month
        select.value = months[0]?.value || '';
        const chartId = select.closest('.options-dropdown').getAttribute('data-chart-id');
        chartFilters[chartId].selectedDate = months[0]?.value || null;
    });
}
    
    function loadGrowthRateChartData() {
    growthRateLoadingElement.style.display = 'flex';
    const errorElement = document.getElementById('growth-rate-error'); // Ensure this exists in HTML

    const chartSelectedDate = chartFilters['salesGrowthRateChart'].selectedDate;
    let apiUrl = '/api/sales-growth-rate?period_type=MS';

    if (chartSelectedDate && chartSelectedDate !== 'all') {
        // Parse selected date (e.g., '2025-05-01')
        const selected = new Date(chartSelectedDate);
        const year = selected.getFullYear();
        const month = selected.getMonth(); // 0-based

        // Calculate start and end dates for selected month and previous month
        const selectedMonthStart = `${year}-${String(month + 1).padStart(2, '0')}-01`;
        // Use MonthEnd to get the correct last day of the month
        const selectedMonthEnd = new Date(year, month + 1, 0).toISOString().split('T')[0]; // e.g., '2025-05-31'
        const prevMonthStart = new Date(year, month - 1, 1).toISOString().split('T')[0]; // e.g., '2025-04-01'

        // Ensure end_date is not in the future
        const currentDate = new Date('2025-06-04'); // Current date
        if (new Date(selectedMonthEnd) > currentDate) {
            if (errorElement) {
                errorElement.textContent = 'Selected date is in the future. Please choose an earlier date.';
                errorElement.style.display = 'block';
                errorElement.style.color = 'red';
            }
            growthRateLoadingElement.style.display = 'none';
            document.querySelector(`button[data-chart-id="salesGrowthRateChart"]`).classList.add('disabled');
            return;
        }

        apiUrl += `&start_date=${prevMonthStart}&end_date=${selectedMonthEnd}`;
    } else {
        // Use global date range, capped at current date
        const startDate = startDateInput.value || '2024-01-01';
        let endDate = endDateInput.value || '2025-06-04';
        const currentDate = new Date('2025-06-04');
        if (new Date(endDate) > currentDate) {
            endDate = '2025-06-04'; // Cap at current date
        }
        if (startDate) apiUrl += `&start_date=${startDate}`;
        if (endDate) apiUrl += `&end_date=${endDate}`;
    }

    console.log(`Fetching growth rate data from: ${apiUrl}`); // Debug log

    fetch(apiUrl)
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => {
                    throw new Error(`HTTP ${response.status}: ${err.error || 'Bad request'}`);
                });
            }
            return response.json();
        })
        .then(data => {
            if (data.error) {
                throw new Error(data.error);
            }
            if (data.periods.length === 0 || data.growth_rates.length === 0) {
                if (errorElement) {
                    errorElement.textContent = 'No sales growth data available for the selected period';
                    errorElement.style.display = 'block';
                    errorElement.style.color = 'red';
                }
                growthRateLoadingElement.style.display = 'none';
                document.querySelector(`button[data-chart-id="salesGrowthRateChart"]`).classList.add('disabled');
                return;
            }
            updateGrowthRateChart(data);
            growthRateLoadingElement.style.display = 'none';
            if (window.chartInstances['salesGrowthRateChart']) {
                document.querySelector(`button[data-chart-id="salesGrowthRateChart"]`).classList.remove('disabled');
            }
            if (errorElement) {
                errorElement.textContent = '';
                errorElement.style.display = 'none';
            }
        })
        .catch(error => {
            console.error('Error fetching growth rate data:', error);
            if (errorElement) {
                errorElement.textContent = `Failed to load Sales Growth Rate data: ${error.message}`;
                errorElement.style.display = 'block';
                errorElement.style.color = 'red';
            } else {
                alert('Failed to load Sales Growth Rate data: ' + error.message);
            }
            growthRateLoadingElement.style.display = 'none';
            document.querySelector(`button[data-chart-id="salesGrowthRateChart"]`).classList.add('disabled');
        });
}
    
    function updateGrowthRateChart(data) {
        if (window.chartInstances['salesGrowthRateChart']) {
            window.chartInstances['salesGrowthRateChart'].destroy();
            delete window.chartInstances['salesGrowthRateChart'];
        }
        if (growthRateChart) {
            growthRateChart.destroy();
        }
    
        const ctx = growthRateChartContainer.getContext('2d');
        const labels = formatChartLabels(data.periods, data.period_type);
        const isAllMonths = chartFilters['salesGrowthRateChart'].selectedDate === 'all';
    
        // Use line chart for multiple data points or All Months, bar chart for single point
        const chartType = isAllMonths || data.growth_rates.length > 1 ? 'line' : 'bar';
    
        // Annotation only for specific month selection
        const selectedIndex = data.periods.length - 1;
        const selectedDateLabel = labels.length > 0 ? labels[selectedIndex] : null;
        const annotationConfig = (!isAllMonths && selectedDateLabel && data.growth_rates[selectedIndex]) ? {
            annotations: {
                selectedPoint: {
                    type: chartType === 'bar' ? 'box' : 'point',
                    xMin: selectedDateLabel,
                    xMax: selectedDateLabel,
                    yMin: chartType === 'bar' ? 0 : data.growth_rates[selectedIndex],
                    yMax: data.growth_rates[selectedIndex],
                    backgroundColor: chartType === 'bar' ? 'rgba(255, 99, 132, 0.2)' : undefined,
                    radius: chartType === 'line' ? 8 : undefined,
                    borderColor: 'rgba(255, 99, 132, 1)',
                    borderWidth: chartType === 'bar' ? 2 : undefined,
                    label: {
                        display: true,
                        content: `Growth: ${data.growth_rates[selectedIndex].toFixed(2)}%`,
                        backgroundColor: 'rgba(255, 99, 132, 0.8)',
                        color: '#fff',
                        font: { weight: 'bold', size: 12 },
                        position: 'center',
                        yAdjust: chartType === 'bar' ? -20 : -20
                    }
                }
            }
        } : {};
    
        growthRateChart = new Chart(ctx, {
            type: chartType,
            data: {
                labels: labels,
                datasets: [{
                    label: 'Growth Rate (%)',
                    data: data.growth_rates,
                    borderColor: 'rgba(255, 99, 132, 1)',
                    backgroundColor: chartType === 'bar' ? 'rgba(255, 99, 132, 0.6)' : 'rgba(255, 99, 132, 0.2)',
                    fill: chartType === 'line' ? false : true,
                    pointRadius: chartType === 'line' ? 5 : 0,
                    pointBackgroundColor: 'rgba(255, 99, 132, 1)',
                    spanGaps: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: 'Month',
                            font: { size: 14 }
                        },
                        grid: { display: false },
                        ticks: {
                            autoSkip: isAllMonths, // Auto-skip for many labels
                            maxRotation: isAllMonths ? 45 : 0,
                            minRotation: isAllMonths ? 45 : 0
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Growth Rate (%)',
                            font: { size: 14 }
                        },
                        beginAtZero: false,
                        ticks: {
                            callback: function(value) {
                                return value + '%';
                            }
                        }
                    }
                },
                plugins: {
                    legend: { display: true, position: 'top' },
                    tooltip: {
                        callbacks: {
                            label: function(tooltipItem) {
                                const datasetLabel = tooltipItem.dataset.label || '';
                                const value = tooltipItem.raw || 0;
                                return `${datasetLabel}: ${value.toFixed(2)}%`;
                            }
                        }
                    },
                    annotation: annotationConfig
                }
            }
        });
    
        window.chartInstances['salesGrowthRateChart'] = growthRateChart;
        console.log('Sales Growth Rate Chart created with ' + (isAllMonths ? 'full history' : 'selected month'));
    }

function loadRepeatVsNewChartData() {
    repeatVsNewLoadingElement.style.display = 'flex';
    const errorElement = document.getElementById('repeat-vs-new-error'); // Add in HTML

    const periodType = periodTypeSelect.value;
    const chartSelectedDate = chartFilters['repeatVsNewSalesChart'].selectedDate;

    let apiUrl = `/api/repeat-vs-new-sales?period_type=${periodType}`;
    if (chartSelectedDate) {
        const selected = new Date(chartSelectedDate);
        const currentDate = new Date('2025-06-04');
        if (selected > currentDate) {
            if (errorElement) {
                errorElement.textContent = 'Selected date is in the future. Please choose an earlier date.';
                errorElement.style.display = 'block';
                errorElement.style.color = 'red';
            }
            repeatVsNewLoadingElement.style.display = 'none';
            document.querySelector(`button[data-chart-id="repeatVsNewSalesChart"]`).classList.add('disabled');
            return;
        }
        apiUrl += `&selected_date=${chartSelectedDate}`;
    } else {
        const startDate = startDateInput.value || '2024-01-01';
        let endDate = endDateInput.value || '2025-06-04';
        const currentDate = new Date('2025-06-04');
        if (new Date(endDate) > currentDate) {
            endDate = '2025-06-04';
        }
        if (startDate) apiUrl += `&start_date=${startDate}`;
        if (endDate) apiUrl += `&end_date=${endDate}`;
    }

    console.log(`Fetching repeat vs new data from: ${apiUrl}`);

    fetch(apiUrl)
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => {
                    throw new Error(`HTTP ${response.status}: ${err.error || 'Bad request'}`);
                });
            }
            return response.json();
        })
        .then(data => {
            if (data.error) {
                throw new Error(data.error);
            }
            if (!data || typeof data !== 'object') {
                throw new Error('Invalid API response: Data is not an object');
            }
            const requiredProps = ['period_type', 'periods', 'repeat_sales', 'new_sales'];
            const missingProps = requiredProps.filter(prop => !(prop in data));
            if (missingProps.length > 0) {
                throw new Error(`API response is missing required properties: ${missingProps.join(', ')}`);
            }
            if (data.periods.length === 0) {
                if (errorElement) {
                    errorElement.textContent = 'No repeat vs new sales data available for the selected period';
                    errorElement.style.display = 'block';
                    errorElement.style.color = 'red';
                }
                repeatVsNewLoadingElement.style.display = 'none';
                document.querySelector(`button[data-chart-id="repeatVsNewSalesChart"]`).classList.add('disabled');
                return;
            }
            updateRepeatVsNewChart(data);
            repeatVsNewLoadingElement.style.display = 'none';
            if (window.chartInstances['repeatVsNewSalesChart']) {
                document.querySelector(`button[data-chart-id="repeatVsNewSalesChart"]`).classList.remove('disabled');
            }
            if (errorElement) {
                errorElement.textContent = '';
                errorElement.style.display = 'none';
            }
        })
        .catch(error => {
            console.error('Error fetching repeat vs new customer sales data:', error);
            if (errorElement) {
                errorElement.textContent = `Failed to load Repeat vs New Customer Sales data: ${error.message}`;
                errorElement.style.display = 'block';
                errorElement.style.color = 'red';
            } else {
                alert('Failed to load Repeat vs New Customer Sales data: ' + error.message);
            }
            repeatVsNewLoadingElement.style.display = 'none';
            document.querySelector(`button[data-chart-id="repeatVsNewSalesChart"]`).classList.add('disabled');
        });
}

    function updateRepeatVsNewChart(data) {
        if (window.chartInstances['repeatVsNewSalesChart']) {
            window.chartInstances['repeatVsNewSalesChart'].destroy();
            delete window.chartInstances['repeatVsNewSalesChart'];
        }
        if (repeatVsNewChart) {
            repeatVsNewChart.destroy();
        }

        // Validate the data structure more thoroughly
        if (!data || typeof data !== 'object') {
            console.error('updateRepeatVsNewChart: Data is not an object:', data);
            alert('Invalid data received for Repeat vs New Customer Sales chart: Data is not an object.');
            return;
        }

        const { period_type, periods, repeat_sales, new_sales } = data;

        // Check individual properties
        if (typeof period_type !== 'string') {
            console.error('updateRepeatVsNewChart: period_type is not a string:', period_type);
            alert('Invalid data received for Repeat vs New Customer Sales chart: period_type is invalid.');
            return;
        }

        if (!Array.isArray(periods)) {
            console.error('updateRepeatVsNewChart: periods is not an array:', periods);
            alert('Invalid data received for Repeat vs New Customer Sales chart: periods is not an array.');
            return;
        }

        if (!Array.isArray(repeat_sales)) {
            console.error('updateRepeatVsNewChart: repeat_sales is not an array:', repeat_sales);
            alert('Invalid data received for Repeat vs New Customer Sales chart: repeat_sales is not an array.');
            return;
        }

        if (!Array.isArray(new_sales)) {
            console.error('updateRepeatVsNewChart: new_sales is not an array:', new_sales);
            alert('Invalid data received for Repeat vs New Customer Sales chart: new_sales is not an array.');
            return;
        }

        const ctx = repeatVsNewChartContainer.getContext('2d');
        repeatVsNewChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: formatChartLabels(periods, period_type),
                datasets: [
                    {
                        label: 'Repeat Customer Sales ($)',
                        data: repeat_sales,
                        backgroundColor: 'rgba(54, 162, 235, 0.6)',
                        borderColor: 'rgba(54, 162, 235, 1)',
                        borderWidth: 1
                    },
                    {
                        label: 'New Customer Sales ($)',
                        data: new_sales,
                        backgroundColor: 'rgba(255, 99, 132, 0.6)',
                        borderColor: 'rgba(255, 99, 132, 1)',
                        borderWidth: 1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        title: { display: true, text: getPeriodLabel(period_type), font: { size: 14 } },
                        grid: { display: false }
                    },
                    y: {
                        title: { display: true, text: 'Sales Amount ($)', font: { size: 14 } },
                        beginAtZero: true
                    }
                },
                plugins: {
                    legend: { display: true, position: 'top' },
                    tooltip: {
                        callbacks: {
                            label: function (tooltipItem) {
                                const datasetLabel = tooltipItem.dataset.label || '';
                                const value = tooltipItem.raw || 0;
                                return `${datasetLabel}: $${value.toFixed(2)}`;
                            }
                        }
                    }
                }
            }
        });
        window.chartInstances['repeatVsNewSalesChart'] = repeatVsNewChart;
        console.log('Repeat vs New Customer Sales Chart created and stored in window.chartInstances');

    }
    fetch('http://192.168.1.34:5001/api/sales-by-salesperson')
  .then(response => response.json())
  .then(data => {
    const labels = data.map(item => item.salesperson);
    const values = data.map(item => item.sales);

    const ctx = document.getElementById('myChart').getContext('2d');
    new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: 'Sales by Salesperson',
          data: values,
          backgroundColor: 'blue'
        }]
      }
    });
  });

});



