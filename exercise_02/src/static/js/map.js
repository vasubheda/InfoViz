// Choropleth world map with hover, click, and brush-response interactions

let mapWidth = 800;
let mapHeight = 500;
let mapSvg, mapG, mapPath;
let choroplethScale = null;
let tooltipDiv;


function initMap() {
    tooltipDiv = d3.select('#tooltip');

    d3.json("/static/data/world-topo.json").then(function(world) {
        let projection = d3.geoEqualEarth()
            .scale(180)
            .translate([mapWidth / 2, mapHeight / 2]);

        mapPath = d3.geoPath().projection(projection);

        mapSvg = d3.select("#svg_map")
            .attr("width", mapWidth)
            .attr("height", mapHeight);

        const mapData = topojson.feature(world, world.objects.countries).features;

        mapG = mapSvg.append("g");

        // Enter once — paths are never re-appended
        mapG.selectAll('path.country')
            .data(mapData, d => d.properties.id)
            .enter()
            .append('path')
            .attr('class', 'country')
            .attr('d', mapPath)
            .attr('stroke', 'black')
            .attr('stroke-width', 0.5)
            .attr('fill', '#eee')
            .on('mouseover', onMapMouseover)
            .on('mousemove', onMapMousemove)
            .on('mouseout', onMapMouseout)
            .on('click', onMapClick);

        updateChoropleth();

        // Register state callbacks
        AppState.onHoverChange = combineCallbacks(AppState.onHoverChange, updateMapHighlight);
        AppState.onBrushChange = combineCallbacks(AppState.onBrushChange, updateMapHighlight);
        AppState.onYearChange = combineCallbacks(AppState.onYearChange, function() { 
            updateChoropleth(); 
            updateMapHighlight(); 
        });
        AppState.onIndicatorChange = combineCallbacks(AppState.onIndicatorChange, function() { 
            updateChoropleth(); 
            updateMapHighlight(); 
        });
    });
}


function updateChoropleth() {
    choroplethScale = buildChoroplethScale(AppState.selectedIndicator, AppState.selectedYear);

    mapG.selectAll('path.country')
        .transition().duration(300)
        .attr('fill', function(d) {
            const csvName = AppState.topoNameToCSV.get(d.properties.admin);
            if (!csvName) return '#eee';
            const val = getValue(csvName, AppState.selectedYear, AppState.selectedIndicator);
            if (val === null) return '#ccc';
            return choroplethScale(val);
        });
}


function updateMapHighlight() {
    if (!choroplethScale) return;
    mapG.selectAll('path.country')
        .attr('fill', function(d) {
            const csvName = AppState.topoNameToCSV.get(d.properties.admin);
            if (!csvName) return '#eee';
            if (AppState.hoveredCountry === csvName) return 'red';
            if (AppState.brushedCountries.has(csvName)) return 'orange';
            const val = getValue(csvName, AppState.selectedYear, AppState.selectedIndicator);
            if (val === null) return '#ccc';
            return choroplethScale(val);
        })
        .attr('stroke-width', function(d) {
            const csvName = AppState.topoNameToCSV.get(d.properties.admin);
            return (AppState.hoveredCountry === csvName) ? 1.5 : 0.5;
        });
}


function onMapMouseover(event, d) {
    const csvName = AppState.topoNameToCSV.get(d.properties.admin);
    //console.log("Map hovered:", d.properties.admin, "-> Extracted CSV Name:", csvName);
    if (!csvName) return;
    setHoveredCountry(csvName);
    showTooltip(event, csvName);
}

function onMapMousemove(event, d) {
    const csvName = AppState.topoNameToCSV.get(d.properties.admin);
    if (!csvName) return;
    tooltipDiv
        .style('left', (event.pageX + 14) + 'px')
        .style('top', (event.pageY - 30) + 'px');
}

function onMapMouseout(event, d) {
    setHoveredCountry(null);
    tooltipDiv.style('opacity', 0);
}

function onMapClick(event, d) {
    const csvName = AppState.topoNameToCSV.get(d.properties.admin);
    if (!csvName) return;
    setClickedCountry(csvName);
}


function showTooltip(event, csvName) {
    const record = getYearRecord(csvName, AppState.selectedYear);
    let html = `<strong>${csvName}</strong> <em>(${AppState.selectedYear})</em><br>`;
    let count = 0;
    for (const [indName, val] of Object.entries(record)) {
        if (val !== null && count < 8) {
            const label = indName.length > 42 ? indName.substring(0, 39) + '...' : indName;
            html += `<span style="font-size:11px">${label}: <b>${val.toFixed(2)}</b></span><br>`;
            count++;
        }
    }
    tooltipDiv
        .style('opacity', 1)
        .style('left', (event.pageX + 14) + 'px')
        .style('top', (event.pageY - 30) + 'px')
        .html(html);
}
