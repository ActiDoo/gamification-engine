jQuery().ready(function($) {
    var defaultcall = "progress";
    
    var fields=["userid","variable","value","key","achievementid","level",
                "lat","lon","friends","groups","timezone","country","region","city",
                "email","password","device_id","push_id","device_os","app_version",
                "offset","message_id","additional_public_data","language"];
    
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
            "fields":["userid","lat","lon","friends","groups","timezone","country","region","city","additional_public_data","language"],
            "url":"/add_or_update_user/{userid}",
            "method":"POST",
            "postparams":["lat","lon","friends","groups","timezone","country","region","city","additional_public_data","language"]
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
        },
        "auth_login" : {
            "fields":["email","password"],
            "url":"/auth/login",
            "method":"POST",
            "jsonparams":["email","password"]
        },
        "register_device" : {
            "fields":["userid","device_id","push_id","device_os","app_version"],
            "url":"/register_device/{userid}",
            "method":"POST",
            "jsonparams":["device_id","push_id","device_os","app_version"]
        },
        "get_messages" : {
            "fields":["userid","offset"],
            "url":"/messages/{userid}",
            "method":"GET",
            "getparams":["offset"]
        },
        "set_messages_read" : {
            "fields":["userid","message_id"],
            "url":"/read_messages/{userid}",
            "method":"POST",
            "jsonparams":["message_id"]
        }
    };
    
    setupAPIForm($,defaultcall,fields,api_funcs);
    
});