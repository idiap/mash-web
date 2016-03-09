/*******************************************************************************
* This file is an adaptation of the one originally written by Xiao Liu
*******************************************************************************/

var nodeList = new Array;
var data = new Array;
var previousPoint = null;
var plot = null;
var display = null;
var pan_range_x = null;
var pan_range_y = null;


plotNodes = function() {
	plot = $.plot(display, data, {
		series: {
			points:{
				show: true,
				radius: 6,
				fill: true,
				lineWidth: 3,
			},
			shadowSize: 5
		},
		grid: {
			backgroundColor: { colors: ["#fff", "#eee"] },
			hoverable: true, 
		},
		legend: {
		    show: false,
			backgroundOpacity: 0,
			container: null,
			},
		zoom: {
		    interactive: true,
		},
		pan: {
			interactive: true
		},
		xaxis: {
		    show: false,
            panRange: pan_range_x,
		},
		yaxis: {
		    show: false,
		    panRange: pan_range_y,
		},
	});
	
    plot.zoom();
	
	updateLabels();
}


updateLabels = function() {
	var o;
	$(".nodeLabel").remove();
	
	if ($('#clustering_display_names')[0].checked)
	{
    	$.each(data, function(key, val) {
		
    		var axes = plot.getAxes();
    		var xaxis = axes['xaxis'];
    		var yaxis = axes['yaxis'];
    		var x = val.data[0][0];
    		var y = val.data[0][1];
		
    		if ((x >= xaxis.min) && (x <= xaxis.max) && (y >= yaxis.min) && (y <= yaxis.max))
    		{
    		    o = plot.pointOffset({x: x, y: y});
		
        		$(display).append('<div class="nodeLabel" style="position:absolute; left:' + 
                            		(o.left + val.radius + 4) + 'px; top:' + 
                            		(o.top - 7) + 'px; color:#666; font-size:smaller">'+
                            		val.name + '</div>');
    		}
    	});
	}
}


filterData = function()
{
    var display_closest = false;
    if ($('#clustering_display_closest_heuristics').length > 0)
        display_closest = $('#clustering_display_closest_heuristics')[0].checked;
    
    if ($('#clustering_display_public_heuristics').length > 0)
    {
        var display_public = $('#clustering_display_public_heuristics')[0].checked;
        var display_user_public = $('#clustering_display_user_public_heuristics')[0].checked;
        var display_user_private = $('#clustering_display_user_private_heuristics')[0].checked;

        if (display_public && display_user_public && display_user_private)
        {
            data = nodeList;
        }
        else
        {
            data = Array();
            for (var i = 0; i < nodeList.length; i += 1)
            {
                var node = nodeList[i];
            
                if (node.public && !node.user && !display_public)
                    continue;

                if (node.public && node.user && !display_user_public)
                    continue;
            
                if (node.user && !node.public && !display_user_private)
                    continue;
            
                data.push(node);
            }
        }
    }
    else
    {
        data = nodeList;
    }

    if (($('#clustering_display_closest_heuristics').length > 0) &&
        $('#clustering_display_closest_heuristics')[0].checked)
    {
        data.sort(function(a, b) {
            return a.dist - b.dist;
        });
        
        data = data.slice(0, 11);
    }

    if (plot)
    {
        plot.setData(data);
        plot.draw();
        updateLabels();
    }
}


drawGraph = function()
{
	//---------------------------------------------draw points---------------------------------------------
	plotNodes();
	
	//---------------------------------------------react with data point function---------------------------------------------
	function showTooltip(x, y, contents) {
		$('<div id="tooltip">' + contents + '</div>').css( {
			position: 'absolute',
			display: 'none',
			top: y + 5,
			left: x + 5,
			border: '1px solid #fdd',
			padding: '2px',
			'background-color': '#fee',
			opacity: 0.80
		}).appendTo("body").fadeIn(200);
	}

	$(display).bind("plothover", function (event, pos, item) {
		if (item) {
			if (previousPoint != item.datapoint) {
				previousPoint = item.datapoint;
			
				$("#tooltip").remove();
				var x = item.datapoint[0].toFixed(2),
					y = item.datapoint[1].toFixed(2);
				
				var content = item.series.name;
				
				if (item.series.public)
				    content += " (public)";
				else
				    content += " (private)"
				
				showTooltip(item.pageX, item.pageY, content);
			}
		}
		else {
			$("#tooltip").remove();
			previousPoint = null;
		}
	});
	
	//---------------------------------------------zoom function---------------------------------------------
	display.bind('plotpan', function (event, plot) {
		updateLabels();
	});

	display.bind('plotzoom', function (event, plot) {
        $("#clustering_current_zoom").html("Zoom: " + plot.currentZoom + "x");
		updateLabels();
	});

	$('#clustering_zoom_out').click(function (e) {
		e.preventDefault();
		plot.zoomOut();
	});

	$('#clustering_zoom_in').click(function (e) {
		e.preventDefault();
		plot.zoom();
	});

	$('#clustering_view_all').click(function (e) {
		e.preventDefault();
		plotNodes();
	});

	$('#clustering_move_up').click(function (e) {
		e.preventDefault();
		plot.pan({ top: -100 });
	});

	$('#clustering_move_down').click(function (e) {
		e.preventDefault();
		plot.pan({ top: 100 });
	});

	$('#clustering_move_left').click(function (e) {
		e.preventDefault();
		plot.pan({ left: -100 });
	});

	$('#clustering_move_right').click(function (e) {
		e.preventDefault();
		plot.pan({ left: 100 });
	});

	$('#clustering_display_names').change(function (e) {
		updateLabels();
	});

	$('#clustering_display_closest_heuristics').change(function (e) {
        filterData();
	});

	$('#clustering_display_public_heuristics').change(function (e) {
        filterData();
	});

	$('#clustering_display_user_public_heuristics').change(function (e) {
        filterData();
	});

	$('#clustering_display_user_private_heuristics').change(function (e) {
        filterData();
	});
}


function process_gexf(dataPath) {
	$.ajax({
		type: "GET",
		url: dataPath,
		async: false,
		error: function(xml){
			alert('Error loading XML document ' + xml);
		},
		success: function(xml) {
			$(xml).find('node').each(function(i){
				var x, y, r, g, b;
				
				x = Number($(this).find('viz\\:position').attr('x'));
				y = Number($(this).find('viz\\:position').attr('y'));
				r = Number($(this).find('viz\\:color').attr('r'));
				g = Number($(this).find('viz\\:color').attr('g'));
				b = Number($(this).find('viz\\:color').attr('b'));
				
				nodeList[i] = {
					label:     $(this).attr('id'), 
					name:      $(this).attr('label'), 
					data:      [[x, y]], 
					color:     "rgb(" + r + "," + g + "," + b + ")",
					fillColor: "#FFFFFF",
					radius:    6,
					public:    true,
					user:      false,
				};
				
				if ($(this).attr('user'))
				{
				    nodeList[i]['color']     = "#A0A0A0";
				    nodeList[i]['fillColor'] = "rgb(" + r + "," + g + "," + b + ")";
				    nodeList[i]['user']      = true;
                }
                
				if (!$(this).attr('public'))
				{
				    nodeList[i]['radius'] = 10;
				    nodeList[i]['public'] = false;
				}

				if ($(this).attr('dist'))
			        nodeList[i]['dist'] = parseFloat($(this).attr('dist'));
				
				if (pan_range_x !== null)
				{
                    if (pan_range_x[0] > x)
                        pan_range_x[0] = x;

                    if (pan_range_x[1] < x)
                        pan_range_x[1] = x;
				}
				else
				{
                    pan_range_x = [x, x];
				}

				if (pan_range_y !== null)
				{
                    if (pan_range_y[0] > y)
                        pan_range_y[0] = y;

                    if (pan_range_y[1] < y)
                        pan_range_y[1] = y;
				}
				else
				{
                    pan_range_y = [y, y];
				}
			});

            c = (pan_range_x[1] - pan_range_x[0]) * 0.5;
            pan_range_x = [pan_range_x[0] - c, pan_range_x[1] + c];

            c = (pan_range_y[1] - pan_range_y[0]) * 0.5;
            pan_range_y = [pan_range_y[0] - c, pan_range_y[1] + c];
        
            filterData();
		}
	});

	display = $('#clustering_display');
	drawGraph();
}
