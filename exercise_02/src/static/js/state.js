// Shared application state and helpers for coordinated views

const AppState = {
    csvData: null,
    pcaData: null,
    indicators: [],

    // Lookup maps built during initState
    codeToName: new Map(),      // ISO3 -> CSV country name
    topoNameToCSV: new Map(),   // TopoJSON admin name -> CSV country name

    // Current UI state
    selectedIndicator: null,
    selectedYear: 2020,

    // Selection state
    hoveredCountry: null,           // CSV country name or null
    brushedCountries: new Set(),    // Set of CSV country names (from scatter brush)
    clickedCountries: new Set(),    // Set of CSV country names (for time series)

    // Callbacks registered by each view
    onHoverChange: null,
    onBrushChange: null,
    onClickChange: null,
    onYearChange: null,
    onIndicatorChange: null,
};


function initState(csvData, pcaData, indicatorList) {
    AppState.csvData = csvData;
    AppState.pcaData = pcaData;
    AppState.indicators = indicatorList;
    AppState.selectedIndicator = indicatorList[0];
    AppState.selectedYear = 2020;

    for (const [name, info] of Object.entries(csvData)) {
        AppState.codeToName.set(info.code, name);
        AppState.topoNameToCSV.set(info.topoName, name);
    }
}


// --- Data accessors ---

function getIndicatorIndex(indicatorName) {
    return AppState.indicators.indexOf(indicatorName);
}

function getValue(csvName, year, indicatorName) {
    const info = AppState.csvData[csvName];
    if (!info) return null;
    const vals = info.years[String(year)];
    if (!vals) return null;
    const idx = getIndicatorIndex(indicatorName);
    if (idx === -1) return null;
    return vals[idx];
}

function getYearRecord(csvName, year) {
    const info = AppState.csvData[csvName];
    if (!info) return {};
    const vals = info.years[String(year)];
    if (!vals) return {};
    const record = {};
    AppState.indicators.forEach((ind, i) => {
        record[ind] = vals[i];
    });
    return record;
}

function getTimeSeries(csvName, indicatorName) {
    const info = AppState.csvData[csvName];
    if (!info) return [];
    const idx = getIndicatorIndex(indicatorName);
    if (idx === -1) return [];
    const result = [];
    for (const [yr, vals] of Object.entries(info.years)) {
        const val = vals[idx];
        if (val !== null) {
            result.push({ year: parseInt(yr), value: val });
        }
    }
    return result.sort((a, b) => a.year - b.year);
}


// --- Color helpers ---

function buildChoroplethScale(indicatorName, year) {
    const values = Object.keys(AppState.csvData)
        .map(name => getValue(name, year, indicatorName))
        .filter(v => v !== null);
    return d3.scaleSequential()
        .domain(d3.extent(values))
        .interpolator(d3.interpolateBlues);
}

function getChoroplethColor(csvName, scale) {
    const val = getValue(csvName, AppState.selectedYear, AppState.selectedIndicator);
    if (val === null) return '#ccc';
    return scale(val);
}

function getCountryColor(csvName, defaultColor) {
    if (AppState.hoveredCountry === csvName) return 'red';
    if (AppState.brushedCountries.has(csvName)) return 'orange';
    return defaultColor;
}


// --- Event dispatchers ---

function combineCallbacks(existing, newCb) {
    if (!existing) return newCb;
    return function(arg) { existing(arg); newCb(arg); };
}

function setHoveredCountry(csvName) {
    AppState.hoveredCountry = csvName;
    if (AppState.onHoverChange) AppState.onHoverChange(csvName);
}

function setBrushedCountries(nameSet) {
    AppState.brushedCountries = nameSet;
    if (AppState.onBrushChange) AppState.onBrushChange(nameSet);
}

function setClickedCountry(csvName) {
    if (AppState.clickedCountries.has(csvName)) {
        AppState.clickedCountries.delete(csvName);
    } else {
        AppState.clickedCountries.add(csvName);
    }
    if (AppState.onClickChange) AppState.onClickChange(AppState.clickedCountries);
}

function setYear(year) {
    AppState.selectedYear = year;
    if (AppState.onYearChange) AppState.onYearChange(year);
}

function setIndicator(indicatorName) {
    AppState.selectedIndicator = indicatorName;
    if (AppState.onIndicatorChange) AppState.onIndicatorChange(indicatorName);
}
