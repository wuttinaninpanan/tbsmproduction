(() => {
	const init = () => {
		const chartsEl = document.getElementById('dashboard-charts');
		const charts = chartsEl ? JSON.parse(chartsEl.textContent) : null;
		if (!charts || typeof Chart === 'undefined') return;

		const pickColor = (className) => {
			const el = document.createElement('span');
			el.className = className;
			el.style.display = 'none';
			document.body.appendChild(el);
			const color = getComputedStyle(el).color;
			document.body.removeChild(el);
			return color;
		};

		const cPrimary = pickColor('text-red-600');
		const cNeutral = pickColor('text-slate-700');
		const cGrid = pickColor('text-slate-200');

		const dailyCanvas = document.getElementById('chartDaily');
		if (dailyCanvas && charts.daily && Array.isArray(charts.daily.labels)) {
			new Chart(dailyCanvas, {
				type: 'line',
				data: {
					labels: charts.daily.labels,
					datasets: [{
						label: 'Records',
						data: charts.daily.data || [],
						borderColor: cPrimary,
						backgroundColor: cPrimary,
						tension: 0.3,
						fill: false,
						pointRadius: 2,
						pointHoverRadius: 4,
					}]
				},
				options: {
					responsive: true,
					maintainAspectRatio: false,
					plugins: { legend: { display: false } },
					scales: {
						x: {
							ticks: { color: cNeutral },
							grid: { display: false },
						},
						y: {
							beginAtZero: true,
							ticks: { color: cNeutral, precision: 0 },
							grid: { color: cGrid },
						},
					},
				}
			});
		}

		const defectCanvas = document.getElementById('chartTopDefect');
		if (defectCanvas && charts.top_defect && Array.isArray(charts.top_defect.labels)) {
			const palette = [
				'#ef4444', '#f97316', '#eab308', '#22c55e', '#3b82f6',
			];
			new Chart(defectCanvas, {
				type: 'doughnut',
				data: {
					labels: charts.top_defect.labels,
					datasets: [{
						data: charts.top_defect.data || [],
						backgroundColor: palette,
						borderWidth: 2,
						borderColor: '#ffffff',
						hoverOffset: 8,
					}]
				},
				options: {
					responsive: true,
					maintainAspectRatio: false,
					cutout: '62%',
					plugins: {
						legend: {
							display: true,
							position: 'bottom',
							labels: {
								color: cNeutral,
								boxWidth: 12,
								padding: 12,
								font: { size: 12 },
							},
						},
						tooltip: {
							callbacks: {
								label: (ctx) => ` ${ctx.label}: ${ctx.parsed} qty`,
							},
						},
					},
				}
			});
		}

		const topCanvas = document.getElementById('chartTopLines');
		if (topCanvas && charts.top_lines && Array.isArray(charts.top_lines.labels)) {
			new Chart(topCanvas, {
				type: 'bar',
				data: {
					labels: charts.top_lines.labels,
					datasets: [{
						label: 'Qty',
						data: charts.top_lines.data || [],
						backgroundColor: cPrimary,
					}]
				},
				options: {
					responsive: true,
					maintainAspectRatio: false,
					plugins: { legend: { display: false } },
					scales: {
						x: {
							ticks: { color: cNeutral },
							grid: { display: false },
						},
						y: {
							beginAtZero: true,
							ticks: { color: cNeutral, precision: 0 },
							grid: { color: cGrid },
						},
					},
				}
			});
		}
	};

	if (document.readyState === 'loading') {
		document.addEventListener('DOMContentLoaded', init);
	} else {
		init();
	}
})();
