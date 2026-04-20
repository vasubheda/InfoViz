// Multi-line time series chart with enter/update/exit pattern

const lineW = 800;
const lineH = 380;
const lineMargin = { top: 30, right: 130, bottom: 60, left: 80 };
const lineInnerW = lineW - lineMargin.left - lineMargin.right;
const lineInnerH = lineH - lineMargin.top - lineMargin.bottom;

let lineSvg, lineG, linesContainer;
let xLineScale, yLineScale;
let lineColorScale;


function initLineChart() {
    lineSvg = d3.select('#svg_line_plot')
        .append('svg')
        .attr('width', lineW)
        .attr('height', lineH);

    lineG = lineSvg.append('g')
        .attr('transform', `translate(${lineMargin.left},${lineMargin.top})`);

    // X axis — static, covers 1960–2020
    xLineScale = d3.scaleLinear()
        .domain([1960, 2020])
        .range([0, lineInnerW]);

    lineG.append('g')
        .attr('class', 'x-axis-line')
        .attr('transform', `translate(0,${lineInnerH})`)
        .call(d3.axisBottom(xLineScale).tickFormat(d3.format('d')).ticks(10));

    // Y axis group — updated when data changes
    lineG.append('g').attr('class', 'y-axis-line');

    // X axis label
    lineG.append('text')
        .attr('class', 'axis-label')
        .attr('x', lineInnerW / 2)
        .attr('y', lineInnerH + 48)
        .attr('text-anchor', 'middle')
        .attr('font-size', '12px')
        .text('Year');

    // Y axis label — updated on indicator change
    lineG.append('text')
        .attr('class', 'y-axis-label')
        .attr('transform', 'rotate(-90)')
        .attr('x', -lineInnerH / 2)
        .attr('y', -65)
        .attr('text-anchor', 'middle')
        .attr('font-size', '11px');

    // Chart title
    lineG.append('text')
        .attr('class', 'line-chart-title')
        .attr('x', lineInnerW / 2)
        .attr('y', -12)
        .attr('text-anchor', 'middle')
        .attr('font-size', '12px')
        .attr('font-weight', 'bold');

    // Container for all line paths
    linesContainer = lineG.append('g').attr('class', 'lines-container');

    // Year marker (vertical dashed line)
    lineG.append('line')
        .attr('class', 'year-marker')
        .attr('stroke', 'steelblue')
        .attr('stroke-dasharray', '4,3')
        .attr('stroke-width', 1.5)
        .attr('opacity', 0);

    // Color scale for distinguishing countries
    lineColorScale = d3.scaleOrdinal(d3.schemeTableau10);

    // Register state callbacks
    AppState.onClickChange = updateLineChart;
    AppState.onYearChange = combineCallbacks(AppState.onYearChange, function(yr) {
        updateYearMarker(yr);
    });
    AppState.onIndicatorChange = combineCallbacks(AppState.onIndicatorChange, function() {
        updateLineChart(AppState.clickedCountries);
    });
}


function updateLineChart(countriesSet) {
    if (!countriesSet || countriesSet.size === 0) {
        d3.select('#svg_line_plot').transition().duration(200).style('opacity', 0);
        return;
    }

    d3.select('#svg_line_plot').transition().duration(300).style('opacity', 1);

    const ind = AppState.selectedIndicator;
    const indLabel = ind.length > 60 ? ind.substring(0, 57) + '...' : ind;

    // Build time series data for each country
    const lineData = Array.from(countriesSet).map(name => ({
        name,
        values: getTimeSeries(name, ind),
    })).filter(d => d.values.length > 0);

    if (lineData.length === 0) return;

    // Recompute y scale from all visible values
    const allValues = lineData.flatMap(d => d.values.map(v => v.value));
    yLineScale = d3.scaleLinear()
        .domain(d3.extent(allValues)).nice()
        .range([lineInnerH, 0]);

    // Update y axis
    lineG.select('.y-axis-line')
        .transition().duration(300)
        .call(d3.axisLeft(yLineScale).ticks(6));

    // Update y axis label
    lineG.select('.y-axis-label').text(indLabel);

    // Update chart title
    lineG.select('.line-chart-title').text(indLabel);

    // Line generator
    const lineGen = d3.line()
        .x(d => xLineScale(d.year))
        .y(d => yLineScale(d.value))
        .defined(d => d.value !== null);

    // --- enter/update/exit on paths ---
    const paths = linesContainer.selectAll('path.country-line')
        .data(lineData, d => d.name);

    // EXIT
    paths.exit()
        .transition().duration(200)
        .attr('opacity', 0)
        .remove();

    // ENTER
    const pathsEnter = paths.enter()
        .append('path')
        .attr('class', 'country-line')
        .attr('fill', 'none')
        .attr('stroke-width', 2)
        .attr('opacity', 0);

    // ENTER + UPDATE
    paths.merge(pathsEnter)
        .transition().duration(400)
        .attr('stroke', d => lineColorScale(d.name))
        .attr('d', d => lineGen(d.values))
        .attr('opacity', 1);

    // --- enter/update/exit on end-of-line labels ---
    const labels = linesContainer.selectAll('text.line-label')
        .data(lineData, d => d.name);

    labels.exit().remove();

    labels.enter()
        .append('text')
        .attr('class', 'line-label')
        .merge(labels)
        .attr('x', function(d) {
            const last = d.values[d.values.length - 1];
            return last ? xLineScale(last.year) + 4 : 0;
        })
        .attr('y', function(d) {
            const last = d.values[d.values.length - 1];
            return last ? yLineScale(last.value) + 4 : 0;
        })
        .attr('fill', d => lineColorScale(d.name))
        .attr('font-size', '10px')
        .text(d => d.name);

    updateYearMarker(AppState.selectedYear);
}


function updateYearMarker(year) {
    if (!yLineScale) return;
    lineG.select('line.year-marker')
        .attr('x1', xLineScale(year))
        .attr('x2', xLineScale(year))
        .attr('y1', 0)
        .attr('y2', lineInnerH)
        .attr('opacity', 1);
}
