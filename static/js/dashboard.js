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
			const dd = charts.daily;
			const cBlue = pickColor('text-sky-600');
			// Optional second series (e.g. produced vs defective). When absent the
			// chart stays a single red line (used by the inspection scrap dashboard).
			const hasTwo = Array.isArray(dd.data2);
			const datasets = [{
				label: dd.label1 || 'Records',
				data: dd.data || [],
				borderColor: hasTwo ? cBlue : cPrimary,
				backgroundColor: hasTwo ? cBlue : cPrimary,
				tension: 0.3,
				fill: false,
				pointRadius: 2,
				pointHoverRadius: 4,
			}];
			if (hasTwo) {
				datasets.push({
					label: dd.label2 || 'ของเสีย',
					data: dd.data2 || [],
					borderColor: cPrimary,
					backgroundColor: cPrimary,
					tension: 0.3,
					fill: false,
					pointRadius: 2,
					pointHoverRadius: 4,
				});
			}
			new Chart(dailyCanvas, {
				type: 'line',
				data: { labels: dd.labels, datasets: datasets },
				options: {
					responsive: true,
					maintainAspectRatio: false,
					plugins: { legend: { display: hasTwo, position: 'bottom', labels: { color: cNeutral, boxWidth: 12, padding: 12 } } },
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
		const singleCanvas = document.getElementById('chartSinglePart');
		if (singleCanvas && charts.single_part && Array.isArray(charts.single_part.labels)) {
			const cRose = pickColor('text-rose-500');
			const names = charts.single_part.names || [];
			new Chart(singleCanvas, {
				type: 'bar',
				data: {
					labels: charts.single_part.labels,
					datasets: [{
						label: 'ทิ้ง (ชิ้น)',
						data: charts.single_part.data || [],
						backgroundColor: cRose,
					}]
				},
				options: {
					indexAxis: 'y', // horizontal — SD codes read better as row labels
					responsive: true,
					maintainAspectRatio: false,
					plugins: {
						legend: { display: false },
						tooltip: {
							callbacks: {
								title: (items) => {
									const nm = names[items[0].dataIndex];
									return nm ? `${items[0].label} — ${nm}` : items[0].label;
								},
								label: (ctx) => ` ${ctx.parsed.x} ชิ้น`,
							},
						},
					},
					scales: {
						x: { beginAtZero: true, ticks: { color: cNeutral, precision: 0 }, grid: { color: cGrid } },
						y: { ticks: { color: cNeutral }, grid: { display: false } },
					},
				}
			});
		}

		const scrapCanvas = document.getElementById('chartScrapDaily');
		if (scrapCanvas && charts.scrap_daily && Array.isArray(charts.scrap_daily.labels)) {
			const cAmber = pickColor('text-amber-500');
			new Chart(scrapCanvas, {
				type: 'bar',
				data: {
					labels: charts.scrap_daily.labels,
					datasets: [{
						label: 'Scrap (ชิ้น)',
						data: charts.scrap_daily.data || [],
						backgroundColor: cAmber,
					}]
				},
				options: {
					responsive: true,
					maintainAspectRatio: false,
					plugins: { legend: { display: false } },
					scales: {
						x: { ticks: { color: cNeutral }, grid: { display: false } },
						y: { beginAtZero: true, ticks: { color: cNeutral, precision: 0 }, grid: { color: cGrid } },
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
