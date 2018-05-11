import {getApiUrl} from '../service/ApiService';

export default {
    id: "api",
    url: getApiUrl("_swagger"), //http://127.0.0.1:6543/api/_swagger
    apis: {
        /*auth: {
            register: {
                responseReducer: ({state, data, requestParams, is_error}) => {
                    console.log("state.AUTH_REGISTER",state.AUTH_REGISTER)
                    let registrationState = state.authRegister || {};
                    registrationState[requestParams.requestID] = data;
                    return {
                        ...state,
                        authRegister: registrationState
                    };
                }
            }
        }*/
    },
    persist: [
    ]
}