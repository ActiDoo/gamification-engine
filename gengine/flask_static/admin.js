jQuery().ready(function($) {
    var defaultcall = "progress";
    
    var fields=["userid","variable","value","key","achievementid","level",
                "lat","lon","friends","groups","timezone","country","region","city"];
    
    var api_funcs = {
        "progress" : {
            "fields":["userid"],
            "url":"/progress/{userid}",
            "method":"GET"
        },
        "increase_value" : {
            "fields":["variable","userid","value","key"],
            "url":"/increase_value/{variable}/{userid}{/key}",
            "method":"POST",
            "postparams":["value"]
        },
        "add_or_update_user" : {
            "fields":["userid","lat","lon","friends","groups","timezone","country","region","city"],
            "url":"/add_or_update_user/{userid}",
            "method":"POST",
            "postparams":["lat","lon","friends","groups","timezone","country","region","city"]
        },
        "delete_user" : {
            "fields":["userid"],
            "url":"/delete_user/{userid}",
            "method":"DELETE"
        },
        "achievement_level" : {
            "fields":["achievementid","level"],
            "url":"/achievement/{achievementid}/level/{level}",
            "method":"GET"
        }
    };
    
    setupAPIForm($,defaultcall,fields,api_funcs);
    
});