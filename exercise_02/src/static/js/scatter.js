// PCA scatterplot with d3.brush and coordinated highlighting

const scatterW = 420;
const scatterH = 420;
const scatterMargin = { top: 40, right: 20, bottom: 65, left: 55 };
const scatterInnerW = scatterW - scatterMargin.left - scatterMargin.right;
const scatterInnerH = scatterH - scatterMargin.top - scatterMargin.bottom;

let scatterSvg, scatterG, brushG;
let xScatterScale, yScatterScale;


function initScatter() {
    const points = AppState.pcaData.points;
    const [ev1, ev2] = AppState.pcaData.explained_variance;

    scatterSvg = d3.select('#svg_plot')
        .attr('width', scatterW)
        .attr('height', scatterH);

    scatterG = scatterSvg.append('g')
        .attr('transform', `translate(${scatterMargin.left},${scatterMargin.top})`);

    xScatterScale = d3.scaleLinear()
        .domain(d3.extent(points, p => p.x)).nice()
        .range([0, scatterInnerW]);

    yScatterScale = d3.scaleLinear()
        .domain(d3.extent(points, p => p.y)).nice()
        .range([scatterInnerH, 0]);

    // Axes
    scatterG.append('g')
        .attr('class', 'x-axis')
        .attr('transform', `translate(0,${scatterInnerH})`)
        .call(d3.axisBottom(xScatterScale).ticks(5));

    scatterG.append('g')
        .attr('class', 'y-axis')
        .call(d3.axisLeft(yScatterScale).ticks(5));

    // Axis labels
    scatterG.append('text')
        .attr('class', 'axis-label')
        .attr('x', scatterInnerW / 2)
        .attr('y', scatterInnerH + 52)
        .attr('text-anchor', 'middle')
        .attr('font-size', '11px')
        .text(`PC1 (${(ev1 * 100).toFixed(1)}%)`);

    scatterG.append('text')
        .attr('class', 'axis-label')
        .attr('transform', 'rotate(-90)')
        .attr('x', -scatterInnerH / 2)
        .attr('y', -42)
        .attr('text-anchor', 'middle')
        .attr('font-size', '11px')
        .text(`PC2 (${(ev2 * 100).toFixed(1)}%)`);

    // d3.brush group — appended BEFORE dots so dots sit on top and receive hover events
    brushG = scatterG.append('g').attr('class', 'brush');
    const brush = d3.brush()
        .extent([[0, 0], [scatterInnerW, scatterInnerH]])
        .on('brush end', onBrush);
    brushG.call(brush);

    // Dots (on top of brush overlay so hover works in empty areas)
    scatterG.selectAll('circle.pca-dot')
        .data(points, d => d.code)
        .enter()
        .append('circle')
        .attr('class', 'pca-dot')
        .attr('cx', d => xScatterScale(d.x))
        .attr('cy', d => yScatterScale(d.y))
        .attr('r', 5)
        .attr('fill', 'steelblue')
        .attr('stroke', 'white')
        .attr('stroke-width', 0.8)
        .on('mouseover', onDotMouseover)
        .on('mouseout', onDotMouseout)
        .on('click', onDotClick);

    // Country code labels (pointer-events:none so they don't block brush/hover)
    scatterG.selectAll('text.dot-label')
        .data(points, d => d.code)
        .enter()
        .append('text')
        .attr('class', 'dot-label')
        .attr('x', d => xScatterScale(d.x) + 6)
        .attr('y', d => yScatterScale(d.y) + 4)
        .text(d => d.code);

    // Apply initial dot colors based on first indicator
    updateDotStyling();

    // Register state callbacks (combine with map.js callbacks already registered)
    AppState.onHoverChange = combineCallbacks(AppState.onHoverChange, updateScatterHighlight);
    AppState.onBrushChange = combineCallbacks(AppState.onBrushChange, updateScatterHighlight);
    AppState.onIndicatorChange = combineCallbacks(AppState.onIndicatorChange, updateDotStyling);
    AppState.onYearChange = combineCallbacks(AppState.onYearChange, updateDotStyling);
}


function updateScatterHighlight() {
    // Instant update for hover/brush state changes
    scatterG.selectAll('circle.pca-dot')
        .attr('fill', function(d) {
            if (AppState.hoveredCountry === d.name) return 'red';
            if (AppState.brushedCountries.has(d.name)) return 'orange';
            // Fall back to choropleth color
            const scale = buildChoroplethScale(AppState.selectedIndicator, AppState.selectedYear);
            const val = getValue(d.name, AppState.selectedYear, AppState.selectedIndicator);
            return val !== null ? scale(val) : '#ccc';
        })
        .attr('r', function(d) {
            if (AppState.hoveredCountry === d.name) return 8;
            if (AppState.brushedCountries.has(d.name)) return 7;
            return 5;
        })
        .attr('stroke', function(d) {
            if (AppState.hoveredCountry === d.name) return 'darkred';
            if (AppState.brushedCountries.has(d.name)) return 'darkorange';
            return 'white';
        });
}


function updateDotStyling() {
    // Transition update for indicator/year changes — colors dots by selected indicator
    const scale = buildChoroplethScale(AppState.selectedIndicator, AppState.selectedYear);
    scatterG.selectAll('circle.pca-dot')
        .transition().duration(300)
        .attr('fill', function(d) {
            if (AppState.hoveredCountry === d.name) return 'red';
            if (AppState.brushedCountries.has(d.name)) return 'orange';
            const val = getValue(d.name, AppState.selectedYear, AppState.selectedIndicator);
            return val !== null ? scale(val) : '#ccc';
        })
        .attr('r', function(d) {
            if (AppState.hoveredCountry === d.name) return 8;
            if (AppState.brushedCountries.has(d.name)) return 7;
            return 5;
        });
}


function onBrush(event) {
    if (!event.selection) {
        // Brush cleared — reset all selections
        setBrushedCountries(new Set());
        AppState.clickedCountries = new Set();
        if (AppState.onClickChange) AppState.onClickChange(AppState.clickedCountries);
        return;
    }

    const [[x0, y0], [x1, y1]] = event.selection;
    const brushed = new Set();

    AppState.pcaData.points.forEach(p => {
        const cx = xScatterScale(p.x);
        const cy = yScatterScale(p.y);
        if (cx >= x0 && cx <= x1 && cy >= y0 && cy <= y1) {
            brushed.add(p.name);
        }
    });

    setBrushedCountries(brushed);

    // Update time series with brushed countries
    if (brushed.size > 0) {
        AppState.clickedCountries = new Set(brushed);
        if (AppState.onClickChange) AppState.onClickChange(AppState.clickedCountries);
    }
}


function onDotMouseover(event, d) {
    setHoveredCountry(d.name);
}

function onDotMouseout(event, d) {
    setHoveredCountry(null);
}

function onDotClick(event, d) {
    setClickedCountry(d.name);
}
