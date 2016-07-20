var setupAPIForm = function($, defaultcall, fields, api_funcs) { 
	
	var container_fields = {};
	
	for(var i=0; i<fields.length; i++) {
		var f = fields[i];		
		container_fields[f] = $('#api_field_'+f);
	}
	
	var call_select = $('select[name=apicall]');
	var api_form = $('#api_form');
	var submit_button = $('#api_submit');
	var api_result = $('#api_result');
	
	call_select.change(function() {
		var selected_call = call_select.val();
		activationfuncs[selected_call]();
	});
	
	var setActiveFields = function(show_fields) {
		for(var i=0; i<fields.length; i++) {
			var f = fields[i];
			if($.inArray(f,show_fields)!=-1) {
				container_fields[f].show();
			} else {
				container_fields[f].hide();
			}
		}
	};
	
	var ajax_options = {
		"method" : "GET",
		"url" : "/",
		"data" : {
			
		},
	};
	$.ajaxSetup({headers: {"X-Auth-Token": $.cookie("X-Auth-Token")}});

	var api_settings_url;
	var api_settings_method;
	var api_settings_postparams;
	var api_settings_jsonparams;
	var api_settings_getparams;
	
	var setURL = function(url, method, postparams, jsonparams, getparams) {
		api_settings_url = API_BASE_URL ? API_BASE_URL+url : url;
		api_settings_method=method;
		api_settings_postparams = postparams;
		api_settings_jsonparams = jsonparams;
		api_settings_getparams = getparams;
	};
	
	var activationfuncs = {};
	$.each(api_funcs,function(k,f) {
	   activationfuncs[k] = function() {
	       setActiveFields(f["fields"]);
           setURL(f["url"],f["method"],f["postparams"],f["jsonparams"],f["getparams"]);
	   };
	});
	
	//from http://stackoverflow.com/questions/4810841/how-can-i-pretty-print-json-using-javascript
	var syntaxHighlight = function(json) {
	    if (typeof json != 'string') {
	         json = JSON.stringify(json, undefined, 2);
	    }
	    json = json.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
	    return json.replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, function (match) {
	        var cls = 'number';
	        if (/^"/.test(match)) {
	            if (/:$/.test(match)) {
	                cls = 'key';
	            } else {
	                cls = 'string';
	            }
	        } else if (/true|false/.test(match)) {
	            cls = 'boolean';
	        } else if (/null/.test(match)) {
	            cls = 'null';
	        }
	        return '<span class="' + cls + '">' + match + '</span>';
	    });
	};
	
	//register form submit
	api_form.submit(function() {
		var url = api_settings_url;
		var method = api_settings_method;
		var postparams = api_settings_postparams;
		var jsonparams = api_settings_jsonparams;
		var getparams = api_settings_getparams;
		var ajax_options={};
		
		ajax_options["data"] = {};
		jsondata = {};
		encoded_get_params = [];

		for(var i=0; i<fields.length; i++) {
			var f	= fields[i];
			var val = container_fields[f].find("input").val();
			//replace {field} with field-value
			url = url.replace("{"+f+"}",""+val);
			
			//replace {/field} with /field-value or "" if not set
			if(val!=undefined && val!="" && val!=0) {
				url = url.replace("{/"+f+"}","/"+val);
			} else {
				url = url.replace("{/"+f+"}","");
			}

			if(typeof(postparams)!=undefined && $.inArray(f,postparams)!=-1) {
				ajax_options["data"][f] = val;
			}

			if(typeof(jsonparams)!=undefined && $.inArray(f,jsonparams)!=-1) {
				jsondata[f] = val;
			}

			if(typeof(getparams)!=undefined && $.inArray(f,getparams)!=-1) {
				encoded_get_params.push(f+"="+encodeURIComponent(val));
			}
		}
		ajax_options["url"] = url + "?" + encoded_get_params.join("&");
		ajax_options["method"] = method;

		if(Object.keys(jsondata).length>0) {
		    ajax_options["data"] = JSON.stringify(jsondata)
		}
		
		var request = $.ajax(ajax_options);
		
		request.done(function( msg ) {
		    api_result.html("<pre>"+syntaxHighlight(msg)+"</pre>");
		});
		
		request.fail(function( jqXHR, textStatus ) {
			try {
				var json = JSON.parse(jqXHR.responseText);
				api_result.html("<pre>Error "+jqXHR.status+":\n"+syntaxHighlight(json)+"</pre>");
			} catch(e) {
				api_result.html("<pre>Error: "+jqXHR.status+"</pre>");
			}
		});
		
		return false;
	});
	
	//activate default api call
	call_select.val(defaultcall);
	activationfuncs[defaultcall]();
};