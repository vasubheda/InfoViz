let mapWidth = 800;
let mapHeight = 500;
let map = null;
let mapData = null;

const countryNameMap = {
    "Russia": "Russian Federation",
    "Syria": "Syrian Arab Republic",
};

function highlightCountryOnMap(country_name) {
    const id = "#map-" + country_name.replace(/\s+/g, '-');
    console.log("Highlighting country:", country_name, "with id:", id);
    d3.select(id)
        .transition().duration(200)
        .attr("fill", "orange")
        .attr("stroke-width", 2);
}

function unhighlightCountryOnMap(country_name) {
    const id = "#map-" + country_name.replace(/\s+/g, '-');
    d3.select(id)
        .transition().duration(200)
        .attr("fill", "white")
        .attr("stroke-width", 0.5);
}

function getNormalizedName(topoName) {
    return countryNameMap[topoName] || topoName;
}

function initMap() {

    // loads the world map as topojson
    d3.json("../static/data/world-topo.json").then(function (countries) {

        // defines the map projection method and scales the map within the SVG
        let projection = d3.geoEqualEarth()
            .scale(180)
            .translate([mapWidth / 2, mapHeight / 2]);

        // generates the path coordinates from topojson
        let path = d3.geoPath()
            .projection(projection);

        // configures the SVG element
        let svg = d3.select("#svg_map")
            .attr("width", mapWidth)
            .attr("height", mapHeight);

        // map geometry
        mapData = topojson.feature(countries, countries.objects.countries).features;

        const tooltip = d3.select("#tooltip");

        // generates and styles the SVG path
        map = svg.append("g")
            .selectAll('path')
            .data(mapData)
            .enter().append('path')
            .attr('d', path)
            .attr('id', d => {
                //console.log(d);
                const csvName = getNormalizedName(d.properties.admin.replace(/\s+/g, '-'));
                return "map-" + csvName;
            })
            .attr('class', 'country')
            .attr('stroke', 'black')
            .attr('stroke-width', 0.5)
            .attr('fill', 'white')
            .on("mouseover", function(event, d) {
                d3.select(this).attr("stroke-width", 2).attr("stroke", "red");
                const csvName = getNormalizedName(d.properties.admin.replace(/\s+/g, '-'));
                tooltip.style("visibility", "visible")
                    .html(`<strong>Country:</strong> ${csvName}`);
                highlightDotInScatterplot(csvName);
            })
            .on("mousemove", function(event) {
                tooltip.style("top", (event.pageY - 10) + "px")
                    .style("left", (event.pageX + 10) + "px");
            })
            .on("mouseout", function(event, d) {
                d3.select(this).attr("stroke-width", 0.5).attr("stroke", "black");
                tooltip.style("visibility", "hidden");
                const csvName = getNormalizedName(d.properties.admin.replace(/\s+/g, '-'));
                unhighlightDotInScatterplot(csvName);
            });
    });


}

