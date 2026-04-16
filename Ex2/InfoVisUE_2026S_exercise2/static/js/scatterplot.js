function highlightDotInScatterplot(country_name) {
    const id = "#dot-" + country_name.replace(/\s+/g, '-');
    
    const dot = d3.select(id);

    console.log("Highlighting dot for country:", country_name, "with id:", id);
    console.log(dot)
    
    if (!dot.empty()) {
        dot.transition()
           .duration(200)
           .attr("r", 10)
           .style("fill", "red")
           .style("stroke", "red")
           .style("stroke-width", 2);
           
        dot.raise(); 
    }
}

function unhighlightDotInScatterplot(country_name) {
    const id = "#dot-" + country_name.replace(/\s+/g, '-');
    
    const dot = d3.select(id);
    
    if (!dot.empty()) {
        dot.transition()
           .duration(200)
           .attr("r", 5)
           .style("fill", "black")
           .style("stroke", "none");
    }
}

function initScatterplot(data) {
    const margin = {top: 20, right: 20, bottom: 30, left: 40};
    const width = 500 - margin.left - margin.right;
    const height = 400 - margin.top - margin.bottom;

    const svg = d3.select("#svg_plot")
        .attr("width", width + margin.left + margin.right)
        .attr("height", height + margin.top + margin.bottom)
      .append("g")
        .attr("transform", `translate(${margin.left},${margin.top})`);

    // Scales
    const x = d3.scaleLinear()
        .domain(d3.extent(data, d => d.x)).nice()
        .range([0, width]);

    const y = d3.scaleLinear()
        .domain(d3.extent(data, d => d.y)).nice()
        .range([height, 0]);

    const tooltip = d3.select("#tooltip");

    // Draw Dots
    svg.selectAll(".dot")
        .data(data)
        .enter()
        .append("circle")
        .attr("class", "dot")
        .attr("id", d => {
            console.log(d);
            return "dot-" + d.country_name.replace(/\s+/g, '-');
        }) 
        .attr("r", 5)
        .attr("cx", d => x(d.x))
        .attr("cy", d => y(d.y))
        .style("fill", "#000000")
        .on("mouseover", function(event, d) {
            d3.select(this).attr("r", 8).style("fill", "red");
            tooltip.style("visibility", "visible")
               .html(`<strong>Country:</strong> ${d.country_name.replace(/\s+/g, '-')}`);
            highlightCountryOnMap(d.country_name.replace(/\s+/g, '-'));
        })
        .on("mousemove", function(event) {
            tooltip.style("top", (event.pageY - 10) + "px")
                .style("left", (event.pageX + 10) + "px");
        })
        .on("mouseout", function(event, d) {
            d3.select(this).attr("r", 5).style("fill", "black");
            tooltip.style("visibility", "hidden");
            unhighlightCountryOnMap(d.country_name.replace(/\s+/g, '-'));
        });
}