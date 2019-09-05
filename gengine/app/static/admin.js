jQuery().ready(function($) {
    var defaultcall = "progress";
    
    var fields=["subjectid","variable","value","key","achievementid","level",
                "lat","lon","friends","groups","timezone","country","region","city",
                "email","password","device_id","push_id","device_os","app_version",
                "offset","message_id","additional_public_data","language"];
    
    var api_funcs = {
        "progress" : {
            "fields":["subjectid"],
            "url":"/progress/{subjectid}",
            "method":"GET"
        },
        "increase_value" : {
            "fields":["variable","subjectid","value","key"],
            "url":"/increase_value/{variable}/{subjectid}{/key}",
            "method":"POST",
            "postparams":["value"]
        },
        "add_or_update_subject" : {
            "fields":["subjectid","lat","lon","friends","groups","timezone","country","region","city","additional_public_data","language"],
            "url":"/add_or_update_subject/{subjectid}",
            "method":"POST",
            "postparams":["lat","lon","friends","groups","timezone","country","region","city","additional_public_data","language"]
        },
        "delete_subject" : {
            "fields":["subjectid"],
            "url":"/delete_subject/{subjectid}",
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
            "fields":["subjectid","device_id","push_id","device_os","app_version"],
            "url":"/register_device/{subjectid}",
            "method":"POST",
            "jsonparams":["device_id","push_id","device_os","app_version"]
        },
        "get_messages" : {
            "fields":["subjectid","offset"],
            "url":"/messages/{subjectid}",
            "method":"GET",
            "getparams":["offset"]
        },
        "set_messages_read" : {
            "fields":["subjectid","message_id"],
            "url":"/read_messages/{subjectid}",
            "method":"POST",
            "jsonparams":["message_id"]
        }
    };
    
    setupAPIForm($,defaultcall,fields,api_funcs);
    
});