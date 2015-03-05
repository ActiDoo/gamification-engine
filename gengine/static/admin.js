jQuery().ready(function($) {
	
	var defaultcall = "progress";
	var fields=["userid","variable","value","key","achievementid","level",
	            "lat","lon","friends","timezone","country","region","city"];
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
			
		}
	};
	var api_settings_url;
	var api_settings_method;
	var api_settings_postparams; 
	
	var setURL = function(url,method,postparams) {
		api_settings_url = url;
		api_settings_method=method;
		api_settings_postparams = postparams;
	};
	
	var activationfuncs = {
		"progress" : function() {
			setActiveFields(["userid"]);
			setURL("/progress/{userid}","GET");
		},
		"increase_value" : function() {
			setActiveFields(["variable","userid","value","key"]);
			setURL("/increase_value/{variable}/{userid}{/key}","POST",["value"]);
		},
		"add_or_update_user" : function() {
			setActiveFields(["userid","lat","lon","friends","timezone","country","region","city"]);
			setURL("/add_or_update_user/{userid}",
					"POST",
					["lat","lon","friends","timezone","country","region","city"]);
		},
		"delete_user" : function() {
			setActiveFields(["userid"]);
			setURL("/delete_user/{userid}","DELETE",[]);
		},
		"achievement_level" : function() {
			setActiveFields(["achievementid","level"]);
			setURL("/achievement/{achievementid}/level/{level}","GET");
		},
	};
	
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
		var ajax_options={};
		
		ajax_options["data"] = {};
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
			
			if(postparams!=undefined && $.inArray(f,postparams)!=-1) {
				ajax_options["data"][f] = val;
			}
		}
		ajax_options["url"] = url;
		ajax_options["method"] = method;
		
		var request = $.ajax(ajax_options);
		
		request.done(function( msg ) {
		    api_result.html("<pre>"+syntaxHighlight(msg)+"</pre>");
		});
		
		request.fail(function( jqXHR, textStatus ) {
			api_result.html("<pre> Error: "+jqXHR.status+"</pre>");
		});
		
		return false;
	});
	
	//activate default api call
	call_select.val(defaultcall);
	activationfuncs[defaultcall]();
	
	
});